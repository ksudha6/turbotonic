from __future__ import annotations

from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import require_role
from src.certificate_dto import (
    CertificateCreate,
    CertificateListItem,
    CertificateResponse,
    CertificateUpdate,
    certificate_to_list_item,
    certificate_to_response,
)
from src.certificate_repository import CertificateRepository
from src.db import get_db
from src.document_repository import DocumentRepository
from src.domain.activity import ActivityEvent, EntityType, TargetRole
from src.domain.certificate import Certificate
from src.domain.document import FileMetadata
from src.domain.user import User, UserRole
from src.product_repository import ProductRepository
from src.qualification_type_repository import QualificationTypeRepository
from src.services.file_storage import FileStorageService

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = ("application/pdf",)


async def get_cert_repo() -> AsyncIterator[CertificateRepository]:
    async with get_db() as conn:
        yield CertificateRepository(conn)


async def get_product_repo_for_cert() -> AsyncIterator[ProductRepository]:
    async with get_db() as conn:
        yield ProductRepository(conn)


async def get_qt_repo_for_cert() -> AsyncIterator[QualificationTypeRepository]:
    async with get_db() as conn:
        yield QualificationTypeRepository(conn)


async def get_activity_repo_for_cert() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


async def get_document_repo_for_cert() -> AsyncIterator[DocumentRepository]:
    async with get_db() as conn:
        yield DocumentRepository(conn)


def get_file_storage_for_cert() -> FileStorageService:
    return FileStorageService(Path(__file__).resolve().parent.parent.parent / "uploads")


CertRepoDep = Annotated[CertificateRepository, Depends(get_cert_repo)]
ProductRepoDep = Annotated[ProductRepository, Depends(get_product_repo_for_cert)]
QtRepoDep = Annotated[QualificationTypeRepository, Depends(get_qt_repo_for_cert)]
ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo_for_cert)]
DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repo_for_cert)]
FileStorageDep = Annotated[FileStorageService, Depends(get_file_storage_for_cert)]


@router.post("/", response_model=CertificateResponse, status_code=201)
async def create_certificate(
    body: CertificateCreate,
    repo: CertRepoDep,
    product_repo: ProductRepoDep,
    qt_repo: QtRepoDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_role(UserRole.SM),
) -> CertificateResponse:
    product = await product_repo.get_by_id(body.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    qt = await qt_repo.get_by_id(body.qualification_type_id)
    if qt is None:
        raise HTTPException(status_code=404, detail="QualificationType not found")

    try:
        cert = Certificate.create(
            product_id=body.product_id,
            qualification_type_id=body.qualification_type_id,
            cert_number=body.cert_number,
            issuer=body.issuer,
            testing_lab=body.testing_lab,
            test_date=body.test_date,
            issue_date=body.issue_date,
            expiry_date=body.expiry_date,
            target_market=body.target_market,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await repo.save(cert)
    await activity_repo.append(
        EntityType.CERTIFICATE,
        cert.id,
        ActivityEvent.CERT_UPLOADED,
        detail=cert.cert_number,
    )
    return certificate_to_response(cert)


@router.get("/", response_model=list[CertificateListItem])
async def list_certificates(
    repo: CertRepoDep,
    product_id: str | None = None,
    target_market: str | None = None,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR),
) -> list[CertificateListItem]:
    if product_id is None:
        raise HTTPException(status_code=422, detail="product_id query parameter is required")

    if target_market is not None:
        certs = await repo.list_by_product_and_market(product_id, target_market)
    else:
        certs = await repo.list_by_product(product_id)

    return [certificate_to_list_item(c) for c in certs]


@router.get("/{cert_id}", response_model=CertificateResponse)
async def get_certificate(
    cert_id: str,
    repo: CertRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR),
) -> CertificateResponse:
    cert = await repo.get_by_id(cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return certificate_to_response(cert)


@router.patch("/{cert_id}", response_model=CertificateResponse)
async def update_certificate(
    cert_id: str,
    body: CertificateUpdate,
    repo: CertRepoDep,
    _user: User = require_role(UserRole.SM),
) -> CertificateResponse:
    cert = await repo.get_by_id(cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if body.status is not None and body.status == "VALID":
        try:
            cert.mark_valid()
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    cert.update(
        cert_number=body.cert_number,
        issuer=body.issuer,
        testing_lab=body.testing_lab,
        test_date=body.test_date,
        issue_date=body.issue_date,
        expiry_date=body.expiry_date,
        target_market=body.target_market,
    )
    await repo.save(cert)
    return certificate_to_response(cert)


@router.post("/{cert_id}/approve", response_model=CertificateResponse)
async def approve_certificate(
    cert_id: str,
    repo: CertRepoDep,
    activity_repo: ActivityRepoDep,
    current_user: User = require_role(UserRole.FREIGHT_MANAGER),
) -> CertificateResponse:
    cert = await repo.get_by_id(cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")

    try:
        cert.approve()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await repo.save(cert)
    await activity_repo.append(
        EntityType.CERTIFICATE,
        cert.id,
        ActivityEvent.CERT_APPROVED,
        detail=cert.cert_number,
        actor_id=current_user.id,
    )
    return certificate_to_response(cert)


@router.post("/{cert_id}/document", response_model=CertificateResponse)
async def upload_certificate_document(
    cert_id: str,
    file: UploadFile,
    repo: CertRepoDep,
    doc_repo: DocumentRepoDep,
    file_storage: FileStorageDep,
    _user: User = require_role(UserRole.SM, UserRole.VENDOR),
) -> CertificateResponse:
    cert = await repo.get_by_id(cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")

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
        stored_path = await file_storage.save_file("CERTIFICATE", cert_id, original_name, content)
        metadata = FileMetadata.create(
            entity_type="CERTIFICATE",
            entity_id=cert_id,
            file_type="certificate",
            original_name=original_name,
            stored_path=stored_path,
            content_type=content_type,
            size_bytes=len(content),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await doc_repo.save(metadata)
    cert.attach_document(metadata.id)
    await repo.save(cert)
    return certificate_to_response(cert)
