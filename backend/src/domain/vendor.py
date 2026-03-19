from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class VendorStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Vendor:
    # id owns the aggregate identity; name owns the business reference
    def __init__(
        self,
        *,
        id: str,
        name: str,
        country: str,
        status: VendorStatus,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self.name = name
        self.country = country
        self.status = status
        self._created_at = created_at
        self.updated_at = updated_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def create(cls, *, name: str, country: str) -> Vendor:
        if not name or not name.strip():
            raise ValueError("name must not be empty or whitespace-only")
        if not country or not country.strip():
            raise ValueError("country must not be empty or whitespace-only")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            name=name,
            country=country,
            status=VendorStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    def deactivate(self) -> None:
        # ACTIVE -> INACTIVE; already-inactive is an error
        if self.status is VendorStatus.INACTIVE:
            raise ValueError("vendor is already INACTIVE")
        self.status = VendorStatus.INACTIVE
        self.updated_at = datetime.now(UTC)

    def reactivate(self) -> None:
        # INACTIVE -> ACTIVE; only INACTIVE vendors transition back
        if self.status is VendorStatus.ACTIVE:
            raise ValueError("vendor is already ACTIVE")
        self.status = VendorStatus.ACTIVE
        self.updated_at = datetime.now(UTC)
