from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class DocumentRequirementStatus(Enum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"


@dataclass
class ShipmentDocumentRequirement:
    id: str
    shipment_id: str
    document_type: str
    is_auto_generated: bool
    status: DocumentRequirementStatus
    document_id: str | None
    created_at: datetime
    updated_at: datetime

    def collect(self, document_id: str) -> None:
        # document_id identifies the stored file; non-empty and non-whitespace required
        if not document_id or not document_id.strip():
            raise ValueError("document_id must not be empty or whitespace-only")
        self.document_id = document_id
        self.status = DocumentRequirementStatus.COLLECTED
        self.updated_at = datetime.now(UTC)

    @classmethod
    def create(
        cls,
        *,
        shipment_id: str,
        document_type: str,
        is_auto_generated: bool,
    ) -> ShipmentDocumentRequirement:
        if not document_type or not document_type.strip():
            raise ValueError("document_type must not be empty or whitespace-only")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            shipment_id=shipment_id,
            document_type=document_type,
            is_auto_generated=is_auto_generated,
            status=DocumentRequirementStatus.PENDING,
            document_id=None,
            created_at=now,
            updated_at=now,
        )


@dataclass
class ReadinessResult:
    documents_ready: bool
    certificates_ready: bool
    packaging_ready: bool
    is_ready: bool
    missing_documents: list[str]
    missing_certificates: list[dict[str, str]]
    missing_packaging: list[dict[str, str]]
