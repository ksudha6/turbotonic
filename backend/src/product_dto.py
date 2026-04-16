from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from src.domain.product import Product
from src.qualification_type_dto import QualificationTypeListItem


class ProductCreate(BaseModel):
    vendor_id: str
    part_number: str
    description: str = ""
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
    manufacturing_address: str | None = None


class ProductResponse(BaseModel):
    id: str
    vendor_id: str
    part_number: str
    description: str
    manufacturing_address: str
    qualifications: list[QualificationTypeListItem]
    created_at: datetime
    updated_at: datetime


class ProductListItem(BaseModel):
    id: str
    vendor_id: str
    part_number: str
    description: str
    manufacturing_address: str
    qualifications: list[QualificationTypeListItem]


def product_to_response(product: Product, qualifications: list[QualificationTypeListItem]) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        vendor_id=product.vendor_id,
        part_number=product.part_number,
        description=product.description,
        manufacturing_address=product.manufacturing_address,
        qualifications=qualifications,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def product_to_list_item(product: Product, qualifications: list[QualificationTypeListItem]) -> ProductListItem:
    return ProductListItem(
        id=product.id,
        vendor_id=product.vendor_id,
        part_number=product.part_number,
        description=product.description,
        manufacturing_address=product.manufacturing_address,
        qualifications=qualifications,
    )
