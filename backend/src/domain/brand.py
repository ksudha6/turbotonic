from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from src.domain.reference_data import VALID_COUNTRIES


class BrandStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Brand:
    # _id owns aggregate identity; name owns the business key
    def __init__(
        self,
        *,
        id: str,
        name: str,
        legal_name: str,
        address: str,
        country: str,
        tax_id: str,
        status: BrandStatus,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self.name = name
        self.legal_name = legal_name
        self.address = address
        self.country = country
        self.tax_id = tax_id
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
    def create(
        cls,
        *,
        name: str,
        legal_name: str,
        address: str,
        country: str,
        tax_id: str = "",
    ) -> Brand:
        if not name or not name.strip():
            raise ValueError("name must not be empty or whitespace-only")
        if not legal_name or not legal_name.strip():
            raise ValueError("legal_name must not be empty or whitespace-only")
        if not address or not address.strip():
            raise ValueError("address must not be empty or whitespace-only")
        if not country or not country.strip():
            raise ValueError("country must not be empty or whitespace-only")
        if country not in VALID_COUNTRIES:
            raise ValueError(f"invalid country: {country!r}")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            name=name,
            legal_name=legal_name,
            address=address,
            country=country,
            tax_id=tax_id,
            status=BrandStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    def deactivate(self) -> None:
        # ACTIVE -> INACTIVE; already-inactive is an error
        if self.status is BrandStatus.INACTIVE:
            raise ValueError("brand is already INACTIVE")
        self.status = BrandStatus.INACTIVE
        self.updated_at = datetime.now(UTC)

    def reactivate(self) -> None:
        # INACTIVE -> ACTIVE; only INACTIVE brands transition back
        if self.status is BrandStatus.ACTIVE:
            raise ValueError("brand is already ACTIVE")
        self.status = BrandStatus.ACTIVE
        self.updated_at = datetime.now(UTC)

    def update(
        self,
        *,
        name: str | None = None,
        legal_name: str | None = None,
        address: str | None = None,
        country: str | None = None,
        tax_id: str | None = None,
    ) -> None:
        # Apply provided fields after validation; advances updated_at
        if name is not None:
            if not name or not name.strip():
                raise ValueError("name must not be empty or whitespace-only")
            self.name = name
        if legal_name is not None:
            if not legal_name or not legal_name.strip():
                raise ValueError("legal_name must not be empty or whitespace-only")
            self.legal_name = legal_name
        if address is not None:
            if not address or not address.strip():
                raise ValueError("address must not be empty or whitespace-only")
            self.address = address
        if country is not None:
            if not country or not country.strip():
                raise ValueError("country must not be empty or whitespace-only")
            if country not in VALID_COUNTRIES:
                raise ValueError(f"invalid country: {country!r}")
            self.country = country
        if tax_id is not None:
            self.tax_id = tax_id
        self.updated_at = datetime.now(UTC)
