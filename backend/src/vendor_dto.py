from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from src.domain.reference_data import VALID_COUNTRIES
from src.domain.vendor import Vendor


class VendorCreate(BaseModel):
    name: str
    country: str
    vendor_type: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be empty or whitespace-only")
        return v

    @field_validator("country")
    @classmethod
    def country_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("country must not be empty or whitespace-only")
        if v not in VALID_COUNTRIES:
            raise ValueError(f"country must be a valid country code; got {v!r}")
        return v

    @field_validator("vendor_type")
    @classmethod
    def vendor_type_valid(cls, v: str) -> str:
        upper = v.upper()
        if upper not in {"PROCUREMENT", "OPEX", "FREIGHT", "MISCELLANEOUS"}:
            raise ValueError("vendor_type must be one of: PROCUREMENT, OPEX, FREIGHT, MISCELLANEOUS")
        return upper


class VendorResponse(BaseModel):
    id: str
    name: str
    country: str
    status: str
    vendor_type: str
    created_at: datetime
    updated_at: datetime


class VendorListItem(BaseModel):
    id: str
    name: str
    country: str
    status: str
    vendor_type: str


def vendor_to_response(vendor: Vendor) -> VendorResponse:
    return VendorResponse(
        id=vendor.id,
        name=vendor.name,
        country=vendor.country,
        status=vendor.status.value,
        vendor_type=vendor.vendor_type.value,
        created_at=vendor.created_at,
        updated_at=vendor.updated_at,
    )


def vendor_to_list_item(vendor: Vendor) -> VendorListItem:
    return VendorListItem(
        id=vendor.id,
        name=vendor.name,
        country=vendor.country,
        status=vendor.status.value,
        vendor_type=vendor.vendor_type.value,
    )
