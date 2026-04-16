from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from src.domain.product import Product


class ProductCreate(BaseModel):
    vendor_id: str
    part_number: str
    description: str = ""
    requires_certification: bool = False
    manufacturing_address: str = ""

    @field_validator("vendor_id")
    @classmethod
    def vendor_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("vendor_id must not be empty or whitespace-only")
        return v

    @field_validator("part_number")
    @classmethod
    def part_number_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("part_number must not be empty or whitespace-only")
        return v


class ProductUpdate(BaseModel):
    description: str | None = None
    requires_certification: bool | None = None
    manufacturing_address: str | None = None


class ProductResponse(BaseModel):
    id: str
    vendor_id: str
    part_number: str
    description: str
    requires_certification: bool
    manufacturing_address: str
    created_at: datetime
    updated_at: datetime


class ProductListItem(BaseModel):
    id: str
    vendor_id: str
    part_number: str
    description: str
    requires_certification: bool
    manufacturing_address: str


def product_to_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        vendor_id=product.vendor_id,
        part_number=product.part_number,
        description=product.description,
        requires_certification=product.requires_certification,
        manufacturing_address=product.manufacturing_address,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def product_to_list_item(product: Product) -> ProductListItem:
    return ProductListItem(
        id=product.id,
        vendor_id=product.vendor_id,
        part_number=product.part_number,
        description=product.description,
        requires_certification=product.requires_certification,
        manufacturing_address=product.manufacturing_address,
    )
