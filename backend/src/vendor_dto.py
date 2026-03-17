from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from src.domain.vendor import Vendor


class VendorCreate(BaseModel):
    name: str
    country: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be empty or whitespace-only")
        return v

    @field_validator("country")
    @classmethod
    def country_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("country must not be empty or whitespace-only")
        return v


class VendorResponse(BaseModel):
    id: str
    name: str
    country: str
    status: str
    created_at: datetime
    updated_at: datetime


class VendorListItem(BaseModel):
    id: str
    name: str
    country: str
    status: str


def vendor_to_response(vendor: Vendor) -> VendorResponse:
    return VendorResponse(
        id=vendor.id,
        name=vendor.name,
        country=vendor.country,
        status=vendor.status.value,
        created_at=vendor.created_at,
        updated_at=vendor.updated_at,
    )


def vendor_to_list_item(vendor: Vendor) -> VendorListItem:
    return VendorListItem(
        id=vendor.id,
        name=vendor.name,
        country=vendor.country,
        status=vendor.status.value,
    )
