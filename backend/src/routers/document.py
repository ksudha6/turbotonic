from __future__ import annotations

from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.auth.dependencies import require_auth
from src.db import get_db
from src.domain.document import FileMetadata
from src.document_dto import FileListItem, FileUploadResponse, file_metadata_to_list_item, file_metadata_to_response
from src.document_repository import DocumentRepository
from src.services.file_storage import FileStorageService

router = APIRouter(prefix="/api/v1/files", tags=["files"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = ("application/pdf",)


async def get_document_repo() -> AsyncIterator[DocumentRepository]:
    async with get_db() as conn:
        yield DocumentRepository(conn)


def get_file_storage() -> FileStorageService:
    return FileStorageService(Path(__file__).resolve().parent.parent.parent / "uploads")


DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repo)]
FileStorageDep = Annotated[FileStorageService, Depends(get_file_storage)]


@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    file: UploadFile,
    entity_type: Annotated[str, Form()],
    entity_id: Annotated[str, Form()],
    file_type: Annotated[str, Form()] = "",
    repo: DocumentRepoDep = ...,  # type: ignore[assignment]
    file_storage: FileStorageDep = ...,  # type: ignore[assignment]
    _user=require_auth,
) -> FileUploadResponse:
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Content type '{content_type}' not allowed. Allowed: {ALLOWED_CONTENT_TYPES}")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File must not be empty")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds maximum size of 10 MB")

    raw_name = file.filename or "upload"
    original_name = raw_name.replace("/", "_").replace("\\", "_")
    try:
        stored_path = await file_storage.save_file(entity_type, entity_id, original_name, content)

        metadata = FileMetadata.create(
            entity_type=entity_type,
            entity_id=entity_id,
            file_type=file_type,
            original_name=original_name,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=len(content),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await repo.save(metadata)
    return file_metadata_to_response(metadata)


@router.get("/", response_model=list[FileListItem])
async def list_files(
    entity_type: str,
    entity_id: str,
    repo: DocumentRepoDep = ...,  # type: ignore[assignment]
    _user=require_auth,
) -> list[FileListItem]:
    files = await repo.list_by_entity(entity_type, entity_id)
    return [file_metadata_to_list_item(f) for f in files]


@router.get("/{file_id}")
async def download_file(
    file_id: str,
    repo: DocumentRepoDep = ...,  # type: ignore[assignment]
    file_storage: FileStorageDep = ...,  # type: ignore[assignment]
    _user=require_auth,
) -> FileResponse:
    metadata = await repo.get_by_id(file_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_path = file_storage.read_file(metadata.stored_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found on disk") from exc

    # Sanitize filename for Content-Disposition header
    safe_filename = metadata.original_name.replace('"', "").replace("\n", "").replace("\r", "")
    return FileResponse(
        path=file_path,
        media_type=metadata.content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    repo: DocumentRepoDep = ...,  # type: ignore[assignment]
    file_storage: FileStorageDep = ...,  # type: ignore[assignment]
    _user=require_auth,
) -> None:
    metadata = await repo.get_by_id(file_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="File not found")

    deleted = await repo.delete(file_id)
    if deleted:
        file_storage.delete_file(metadata.stored_path)
