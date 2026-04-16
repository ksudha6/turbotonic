from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class PackagingSpecStatus(str, Enum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"


class PackagingSpec:
    # id and created_at are immutable; document_id and status are mutable via collect()/uncollect()
    def __init__(
        self,
        *,
        id: str,
        product_id: str,
        marketplace: str,
        spec_name: str,
        description: str,
        requirements_text: str,
        status: PackagingSpecStatus,
        document_id: str | None = None,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self.product_id = product_id
        self.marketplace = marketplace
        self.spec_name = spec_name
        self.description = description
        self.requirements_text = requirements_text
        self.status = status
        self.document_id = document_id
        self._created_at = created_at
        self.updated_at = updated_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def create(
        cls,
        *,
        product_id: str,
        marketplace: str,
        spec_name: str,
        description: str = "",
        requirements_text: str = "",
    ) -> PackagingSpec:
        if not product_id or not product_id.strip():
            raise ValueError("product_id must not be empty or whitespace-only")
        if not marketplace or not marketplace.strip():
            raise ValueError("marketplace must not be empty or whitespace-only")
        if not spec_name or not spec_name.strip():
            raise ValueError("spec_name must not be empty or whitespace-only")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            product_id=product_id,
            marketplace=marketplace,
            spec_name=spec_name,
            description=description,
            requirements_text=requirements_text,
            status=PackagingSpecStatus.PENDING,
            document_id=None,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        spec_name: str | None = None,
        description: str | None = None,
        requirements_text: str | None = None,
    ) -> None:
        if spec_name is not None:
            self.spec_name = spec_name
        if description is not None:
            self.description = description
        if requirements_text is not None:
            self.requirements_text = requirements_text
        self.updated_at = datetime.now(UTC)

    def collect(self, document_id: str) -> None:
        # document_id identifies the stored file; status transitions to COLLECTED
        if not document_id or not document_id.strip():
            raise ValueError("document_id must not be empty or whitespace-only")
        self.document_id = document_id
        self.status = PackagingSpecStatus.COLLECTED
        self.updated_at = datetime.now(UTC)

    def uncollect(self) -> None:
        # Reverts a COLLECTED spec back to PENDING, clearing the associated document
        if self.status is not PackagingSpecStatus.COLLECTED:
            raise ValueError("Can only uncollect a spec that is currently COLLECTED")
        self.document_id = None
        self.status = PackagingSpecStatus.PENDING
        self.updated_at = datetime.now(UTC)
