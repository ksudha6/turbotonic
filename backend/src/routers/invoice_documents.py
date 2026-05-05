from __future__ import annotations

from pathlib import Path
from typing import Annotated, AsyncIterator

import asyncpg

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import (
    can_manage_invoice_attachments,
    can_view_invoice_attachments,
    check_vendor_access,
    require_auth,
)
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType, TargetRole
from src.domain.document import FileMetadata
from src.domain.invoice_attachment import validate_invoice_attachment_type
from src.domain.user import User
from src.document_repository import DocumentRepository
from src.invoice_document_dto import InvoiceFileListItem, InvoiceFileUploadResponse
from src.invoice_repository import InvoiceRepository
from src.repository import PurchaseOrderRepository
from src.services.file_storage import FileStorageService

router = APIRouter(prefix="/api/v1/invoices", tags=["invoice-documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = ("application/pdf",)


async def get_invoice_repo() -> AsyncIterator[InvoiceRepository]:
    async with get_db() as conn:
        yield InvoiceRepository(conn)


async def get_po_repo() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        yield PurchaseOrderRepository(conn)


async def get_document_repo() -> AsyncIterator[DocumentRepository]:
    async with get_db() as conn:
        yield DocumentRepository(conn)


async def get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


def get_file_storage() -> FileStorageService:
    return FileStorageService(Path(__file__).resolve().parent.parent.parent / "uploads")


InvoiceRepoDep = Annotated[InvoiceRepository, Depends(get_invoice_repo)]
PORepoDep = Annotated[PurchaseOrderRepository, Depends(get_po_repo)]
DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repo)]
ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo)]
FileStorageDep = Annotated[FileStorageService, Depends(get_file_storage)]


async def _batch_usernames(conn: asyncpg.Connection, user_ids: set[str]) -> dict[str, str]:
    """Fetch username for each user_id in one query. Returns a mapping id -> username."""
    if not user_ids:
        return {}
    rows = await conn.fetch(
        "SELECT id, username FROM users WHERE id = ANY($1::text[])",
        list(user_ids),
    )
    return {row["id"]: row["username"] for row in rows}


async def _resolve_invoice_vendor_id(
    invoice_id: str,
    invoice_repo: InvoiceRepository,
    po_repo: PurchaseOrderRepository,
) -> tuple[str, str]:
    """Return (invoice.id, vendor_id) or raise 404.

    invoice_id owns the lookup; vendor_id is resolved via the linked PO.
    """
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    po = await po_repo.get(invoice.po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return invoice.id, po.vendor_id


@router.post("/{invoice_id}/documents", response_model=InvoiceFileUploadResponse, status_code=201)
async def upload_invoice_document(
    invoice_id: str,
    file: UploadFile,
    file_type: Annotated[str, Form()],
    invoice_repo: InvoiceRepoDep = ...,  # type: ignore[assignment]
    po_repo: PORepoDep = ...,  # type: ignore[assignment]
    document_repo: DocumentRepoDep = ...,  # type: ignore[assignment]
    activity_repo: ActivityRepoDep = ...,  # type: ignore[assignment]
    file_storage: FileStorageDep = ...,  # type: ignore[assignment]
    user: User = require_auth,
) -> InvoiceFileUploadResponse:
    resolved_id, vendor_id = await _resolve_invoice_vendor_id(invoice_id, invoice_repo, po_repo)

    check_vendor_access(user, vendor_id)

    if not can_manage_invoice_attachments(user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        parsed_enum = validate_invoice_attachment_type(file_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Content type '{content_type}' not allowed. Allowed: {ALLOWED_CONTENT_TYPES}",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File must not be empty")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds maximum size of 10 MB")

    raw_name = file.filename or "upload"
    original_name = raw_name.replace("/", "_").replace("\\", "_")

    try:
        stored_path = await file_storage.save_file("INVOICE", resolved_id, original_name, content)
        metadata = FileMetadata.create(
            entity_type="INVOICE",
            entity_id=resolved_id,
            file_type=parsed_enum.value,
            original_name=original_name,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=len(content),
            uploaded_by=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await document_repo.save(metadata)

    await activity_repo.append(
        EntityType.INVOICE,
        resolved_id,
        ActivityEvent.INVOICE_DOCUMENT_UPLOADED,
        detail=f"{parsed_enum.value} uploaded ({original_name})",
        target_role=TargetRole.SM,
    )

    return InvoiceFileUploadResponse(
        id=metadata.id,
        entity_type=metadata.entity_type,
        entity_id=metadata.entity_id,
        file_type=metadata.file_type,
        original_name=metadata.original_name,
        content_type=metadata.content_type,
        size_bytes=metadata.size_bytes,
        uploaded_at=metadata.uploaded_at,
        uploaded_by=metadata.uploaded_by,
        uploaded_by_username=user.username,
    )


@router.get("/{invoice_id}/documents", response_model=list[InvoiceFileListItem])
async def list_invoice_documents(
    invoice_id: str,
    invoice_repo: InvoiceRepoDep = ...,  # type: ignore[assignment]
    po_repo: PORepoDep = ...,  # type: ignore[assignment]
    document_repo: DocumentRepoDep = ...,  # type: ignore[assignment]
    user: User = require_auth,
) -> list[InvoiceFileListItem]:
    resolved_id, vendor_id = await _resolve_invoice_vendor_id(invoice_id, invoice_repo, po_repo)

    check_vendor_access(user, vendor_id)

    if not can_view_invoice_attachments(user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    files = await document_repo.list_by_entity("INVOICE", resolved_id, order="desc")

    # Batch-fetch uploader usernames — single query, no N+1.
    uploader_ids = {f.uploaded_by for f in files if f.uploaded_by is not None}
    async with get_db() as conn:
        username_map = await _batch_usernames(conn, uploader_ids)

    return [
        InvoiceFileListItem(
            id=f.id,
            entity_type=f.entity_type,
            entity_id=f.entity_id,
            file_type=f.file_type,
            original_name=f.original_name,
            content_type=f.content_type,
            size_bytes=f.size_bytes,
            uploaded_at=f.uploaded_at,
            uploaded_by=f.uploaded_by,
            uploaded_by_username=username_map.get(f.uploaded_by) if f.uploaded_by else None,
        )
        for f in files
    ]


@router.get("/{invoice_id}/documents/{file_id}")
async def download_invoice_document(
    invoice_id: str,
    file_id: str,
    invoice_repo: InvoiceRepoDep = ...,  # type: ignore[assignment]
    po_repo: PORepoDep = ...,  # type: ignore[assignment]
    document_repo: DocumentRepoDep = ...,  # type: ignore[assignment]
    file_storage: FileStorageDep = ...,  # type: ignore[assignment]
    user: User = require_auth,
) -> FileResponse:
    resolved_id, vendor_id = await _resolve_invoice_vendor_id(invoice_id, invoice_repo, po_repo)

    check_vendor_access(user, vendor_id)

    metadata = await document_repo.get_by_id(file_id)
    if metadata is None or metadata.entity_type != "INVOICE" or metadata.entity_id != resolved_id:
        raise HTTPException(status_code=404, detail="File not found")

    if not can_view_invoice_attachments(user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        file_path = file_storage.read_file(metadata.stored_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found on disk") from exc

    safe_filename = metadata.original_name.replace('"', "").replace("\n", "").replace("\r", "")
    return FileResponse(
        path=file_path,
        media_type=metadata.content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.delete("/{invoice_id}/documents/{file_id}", status_code=204)
async def delete_invoice_document(
    invoice_id: str,
    file_id: str,
    invoice_repo: InvoiceRepoDep = ...,  # type: ignore[assignment]
    po_repo: PORepoDep = ...,  # type: ignore[assignment]
    document_repo: DocumentRepoDep = ...,  # type: ignore[assignment]
    file_storage: FileStorageDep = ...,  # type: ignore[assignment]
    user: User = require_auth,
) -> None:
    resolved_id, vendor_id = await _resolve_invoice_vendor_id(invoice_id, invoice_repo, po_repo)

    check_vendor_access(user, vendor_id)

    metadata = await document_repo.get_by_id(file_id)
    if metadata is None or metadata.entity_type != "INVOICE" or metadata.entity_id != resolved_id:
        raise HTTPException(status_code=404, detail="File not found")

    if not can_manage_invoice_attachments(user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    await document_repo.delete(file_id)
    # Best-effort; silent if the file is already gone from disk.
    file_storage.delete_file(metadata.stored_path)
