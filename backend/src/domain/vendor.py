from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from src.domain.reference_data import VALID_COUNTRIES


# Imported here for callers that set defaults via Vendor.set_default_party
def _vendor_party_role_type() -> type:
    from src.domain.vendor_party import VendorPartyRole
    return VendorPartyRole


class VendorStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class VendorType(Enum):
    PROCUREMENT = "PROCUREMENT"
    OPEX = "OPEX"
    FREIGHT = "FREIGHT"
    MISCELLANEOUS = "MISCELLANEOUS"


class Vendor:
    # id owns the aggregate identity; name owns the business reference
    def __init__(
        self,
        *,
        id: str,
        name: str,
        country: str,
        status: VendorStatus,
        vendor_type: VendorType,
        created_at: datetime,
        updated_at: datetime,
        address: str = "",
        account_details: str = "",
        tax_id: str = "",
        # Iter 113: party FK defaults — nullable, set after VendorParty creation
        default_seller_party_id: str | None = None,
        default_shipper_party_id: str | None = None,
        default_remit_to_party_id: str | None = None,
    ) -> None:
        self._id = id
        self.name = name
        self.country = country
        self.status = status
        self.vendor_type = vendor_type
        self.address = address
        self.account_details = account_details
        self.tax_id = tax_id
        self.default_seller_party_id = default_seller_party_id
        self.default_shipper_party_id = default_shipper_party_id
        self.default_remit_to_party_id = default_remit_to_party_id
        self._created_at = created_at
        self.updated_at = updated_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def create(cls, *, name: str, country: str, vendor_type: VendorType, address: str = "", account_details: str = "", tax_id: str = "") -> Vendor:
        if not name or not name.strip():
            raise ValueError("name must not be empty or whitespace-only")
        if not country or not country.strip():
            raise ValueError("country must not be empty or whitespace-only")
        if country not in VALID_COUNTRIES:
            raise ValueError(f"invalid country: {country!r}")
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            name=name,
            country=country,
            status=VendorStatus.ACTIVE,
            vendor_type=vendor_type,
            created_at=now,
            updated_at=now,
            address=address,
            account_details=account_details,
            tax_id=tax_id,
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

    def set_default_party(self, role: object, party_id: str | None) -> None:
        # role is VendorPartyRole; typed as object to avoid circular import at module load.
        # Each role maps to the corresponding default_*_party_id field.
        role_str = str(role)
        if role_str == "SELLER":
            self.default_seller_party_id = party_id
        elif role_str == "SHIPPER":
            self.default_shipper_party_id = party_id
        elif role_str == "REMIT_TO":
            self.default_remit_to_party_id = party_id
        else:
            raise ValueError(f"unsupported role for vendor default: {role_str!r}")
        self.updated_at = datetime.now(UTC)
