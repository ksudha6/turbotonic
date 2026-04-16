from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from src.domain.packaging import PackagingSpec, PackagingSpecStatus


class PackagingSpecCreate(BaseModel):
    product_id: str
    marketplace: str
    spec_name: str
    description: str = ""
    requirements_text: str = ""

    @field_validator("product_id")
    @classmethod
    def product_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("product_id must not be empty or whitespace-only")
        return v

    @field_validator("marketplace")
    @classmethod
    def marketplace_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("marketplace must not be empty or whitespace-only")
        return v

    @field_validator("spec_name")
    @classmethod
    def spec_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("spec_name must not be empty or whitespace-only")
        return v


class PackagingSpecUpdate(BaseModel):
    spec_name: str | None = None
    description: str | None = None
    requirements_text: str | None = None


class PackagingSpecResponse(BaseModel):
    id: str
    product_id: str
    marketplace: str
    spec_name: str
    description: str
    requirements_text: str
    status: PackagingSpecStatus
    document_id: str | None = None
    created_at: datetime
    updated_at: datetime


def spec_to_response(spec: PackagingSpec) -> PackagingSpecResponse:
    return PackagingSpecResponse(
        id=spec.id,
        product_id=spec.product_id,
        marketplace=spec.marketplace,
        spec_name=spec.spec_name,
        description=spec.description,
        requirements_text=spec.requirements_text,
        status=spec.status,
        document_id=spec.document_id,
        created_at=spec.created_at,
        updated_at=spec.updated_at,
    )
