from __future__ import annotations

from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import require_role
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.document import FileMetadata
from src.domain.packaging import PackagingSpec, PackagingSpecStatus
from src.domain.user import User, UserRole
from src.document_repository import DocumentRepository
from src.packaging_dto import (
    PackagingSpecCreate,
    PackagingSpecResponse,
    PackagingSpecUpdate,
    spec_to_response,
)
from src.packaging_repository import PackagingSpecRepository
from src.product_repository import ProductRepository
from src.services.file_storage import FileStorageService

router = APIRouter(prefix="/api/v1/packaging-specs", tags=["packaging-specs"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = ("application/pdf",)


async def get_packaging_repo() -> AsyncIterator[PackagingSpecRepository]:
    async with get_db() as conn:
        yield PackagingSpecRepository(conn)


async def get_product_repo_for_packaging() -> AsyncIterator[ProductRepository]:
    async with get_db() as conn:
        yield ProductRepository(conn)


async def get_document_repo_for_packaging() -> AsyncIterator[DocumentRepository]:
    async with get_db() as conn:
        yield DocumentRepository(conn)


def get_file_storage_for_packaging() -> FileStorageService:
    return FileStorageService(Path(__file__).resolve().parent.parent.parent / "uploads")


async def get_activity_repo_for_packaging() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


PackagingRepoDep = Annotated[PackagingSpecRepository, Depends(get_packaging_repo)]
ProductRepoDep = Annotated[ProductRepository, Depends(get_product_repo_for_packaging)]
DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repo_for_packaging)]
FileStorageDep = Annotated[FileStorageService, Depends(get_file_storage_for_packaging)]
ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo_for_packaging)]


@router.post("/", response_model=PackagingSpecResponse, status_code=201)
async def create_packaging_spec(
    body: PackagingSpecCreate,
    repo: PackagingRepoDep,
    product_repo: ProductRepoDep,
    _user: User = require_role(UserRole.SM),
) -> PackagingSpecResponse:
    product = await product_repo.get_by_id(body.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    existing = await repo.get_by_unique_key(body.product_id, body.marketplace, body.spec_name)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="PackagingSpec with this product_id, marketplace, and spec_name already exists",
        )

    try:
        spec = PackagingSpec.create(
            product_id=body.product_id,
            marketplace=body.marketplace,
            spec_name=body.spec_name,
            description=body.description,
            requirements_text=body.requirements_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        await repo.save(spec)
    except Exception as exc:
        if "UNIQUE constraint" in str(exc) or "unique" in str(exc).lower():
            raise HTTPException(
                status_code=409,
                detail="PackagingSpec with this product_id, marketplace, and spec_name already exists",
            ) from exc
        raise

    return spec_to_response(spec)


@router.get("/", response_model=list[PackagingSpecResponse])
async def list_packaging_specs(
    repo: PackagingRepoDep,
    product_id: str | None = None,
    marketplace: str | None = None,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR),
) -> list[PackagingSpecResponse]:
    if product_id is None:
        raise HTTPException(status_code=422, detail="product_id query parameter is required")

    if marketplace is not None:
        specs = await repo.list_by_product_and_marketplace(product_id, marketplace)
    else:
        specs = await repo.list_by_product(product_id)

    return [spec_to_response(s) for s in specs]


@router.get("/{spec_id}", response_model=PackagingSpecResponse)
async def get_packaging_spec(
    spec_id: str,
    repo: PackagingRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR),
) -> PackagingSpecResponse:
    spec = await repo.get(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="PackagingSpec not found")
    return spec_to_response(spec)


@router.patch("/{spec_id}", response_model=PackagingSpecResponse)
async def update_packaging_spec(
    spec_id: str,
    body: PackagingSpecUpdate,
    repo: PackagingRepoDep,
    _user: User = require_role(UserRole.SM),
) -> PackagingSpecResponse:
    spec = await repo.get(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="PackagingSpec not found")

    spec.update(
        spec_name=body.spec_name,
        description=body.description,
        requirements_text=body.requirements_text,
    )
    await repo.save(spec)
    return spec_to_response(spec)


@router.delete("/{spec_id}", status_code=204)
async def delete_packaging_spec(
    spec_id: str,
    repo: PackagingRepoDep,
    _user: User = require_role(UserRole.SM),
) -> None:
    spec = await repo.get(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="PackagingSpec not found")

    if spec.status is not PackagingSpecStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail="PackagingSpec can only be deleted when status is PENDING",
        )

    await repo.delete(spec_id)


@router.post("/{spec_id}/upload", response_model=PackagingSpecResponse)
async def upload_packaging_file(
    spec_id: str,
    file: UploadFile,
    repo: PackagingRepoDep,
    doc_repo: DocumentRepoDep,
    file_storage: FileStorageDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR),
) -> PackagingSpecResponse:
    spec = await repo.get(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="PackagingSpec not found")

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
        stored_path = await file_storage.save_file("PACKAGING", spec_id, original_name, content)
        metadata = FileMetadata.create(
            entity_type="PACKAGING",
            entity_id=spec_id,
            file_type="PACKAGING_FILE",
            original_name=original_name,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=len(content),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await doc_repo.save(metadata)
    spec.collect(metadata.id)
    await repo.save(spec)
    await activity_repo.append(
        entity_type=EntityType.PACKAGING,
        entity_id=spec_id,
        event=ActivityEvent.PACKAGING_COLLECTED,
    )

    return spec_to_response(spec)
