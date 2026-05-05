from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from src.domain.reference_data import VALID_COUNTRIES


class VendorPartyRole(StrEnum):
    MANUFACTURER = "MANUFACTURER"
    SELLER = "SELLER"
    SHIPPER = "SHIPPER"
    REMIT_TO = "REMIT_TO"


class VendorPartyValidationError(ValueError):
    """Domain-level validation failure for VendorParty fields."""


class VendorPartyInUseError(Exception):
    """Raised when a VendorParty is referenced by at least one FK and cannot be deleted."""


class VendorParty:
    # id owns identity; vendor_id + role form the business reference context
    def __init__(
        self,
        *,
        id: str,
        vendor_id: str,
        role: VendorPartyRole,
        legal_name: str,
        address: str,
        country: str,
        tax_id: str = "",
        banking_details: str = "",
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self.vendor_id = vendor_id
        self.role = role
        self.legal_name = legal_name
        self.address = address
        self.country = country
        self.tax_id = tax_id
        self.banking_details = banking_details
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
        vendor_id: str,
        role: VendorPartyRole,
        legal_name: str,
        address: str,
        country: str,
        tax_id: str = "",
        banking_details: str = "",
    ) -> VendorParty:
        if not legal_name or not legal_name.strip():
            raise VendorPartyValidationError(
                "legal_name must not be empty or whitespace-only"
            ) from None
        if not address or not address.strip():
            raise VendorPartyValidationError(
                "address must not be empty or whitespace-only"
            ) from None
        if not country or country not in VALID_COUNTRIES:
            raise VendorPartyValidationError(
                f"invalid country: {country!r}"
            ) from None
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            vendor_id=vendor_id,
            role=role,
            legal_name=legal_name.strip(),
            address=address.strip(),
            country=country,
            tax_id=tax_id,
            banking_details=banking_details,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        legal_name: str | None = None,
        address: str | None = None,
        country: str | None = None,
        tax_id: str | None = None,
        banking_details: str | None = None,
    ) -> None:
        if legal_name is not None:
            if not legal_name or not legal_name.strip():
                raise VendorPartyValidationError(
                    "legal_name must not be empty or whitespace-only"
                ) from None
            self.legal_name = legal_name.strip()
        if address is not None:
            if not address or not address.strip():
                raise VendorPartyValidationError(
                    "address must not be empty or whitespace-only"
                ) from None
            self.address = address.strip()
        if country is not None:
            if country not in VALID_COUNTRIES:
                raise VendorPartyValidationError(
                    f"invalid country: {country!r}"
                ) from None
            self.country = country
        if tax_id is not None:
            self.tax_id = tax_id
        if banking_details is not None:
            self.banking_details = banking_details
        self.updated_at = datetime.now(UTC)
