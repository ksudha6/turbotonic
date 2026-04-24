from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from src.domain.shipment_document_requirement import (
    ReadinessResult,
    ShipmentDocumentRequirement,
)


class ShipmentDocumentRequirementResponse(BaseModel):
    id: str
    shipment_id: str
    document_type: str
    is_auto_generated: bool
    status: str
    document_id: str | None
    created_at: datetime
    updated_at: datetime


class ShipmentDocumentRequirementCreate(BaseModel):
    document_type: str


class ReadinessResultResponse(BaseModel):
    documents_ready: bool
    certificates_ready: bool
    packaging_ready: bool
    is_ready: bool
    missing_documents: list[str]
    missing_certificates: list[dict[str, str]]
    missing_packaging: list[dict[str, str]]


def requirement_to_response(
    req: ShipmentDocumentRequirement,
) -> ShipmentDocumentRequirementResponse:
    return ShipmentDocumentRequirementResponse(
        id=req.id,
        shipment_id=req.shipment_id,
        document_type=req.document_type,
        is_auto_generated=req.is_auto_generated,
        status=req.status.value,
        document_id=req.document_id,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


def readiness_result_to_response(result: ReadinessResult) -> ReadinessResultResponse:
    return ReadinessResultResponse(
        documents_ready=result.documents_ready,
        certificates_ready=result.certificates_ready,
        packaging_ready=result.packaging_ready,
        is_ready=result.is_ready,
        missing_documents=result.missing_documents,
        missing_certificates=result.missing_certificates,
        missing_packaging=result.missing_packaging,
    )
