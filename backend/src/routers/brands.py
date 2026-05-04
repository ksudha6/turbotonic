from __future__ import annotations

import json
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import require_role
from src.brand_repository import BrandRepository
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.brand import Brand, BrandStatus
from src.domain.reference_data import VALID_COUNTRIES
from src.domain.user import User, UserRole
from src.vendor_repository import VendorRepository

router = APIRouter(prefix="/api/v1/brands", tags=["brands"])


# --- Dependency providers ---

async def get_brand_repo() -> AsyncIterator[BrandRepository]:
    async with get_db() as conn:
        yield BrandRepository(conn)


async def get_vendor_repo_for_brands() -> AsyncIterator[VendorRepository]:
    async with get_db() as conn:
        yield VendorRepository(conn)


async def get_activity_repo_for_brands() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


BrandRepoDep = Annotated[BrandRepository, Depends(get_brand_repo)]
VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo_for_brands)]
ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo_for_brands)]


# --- Pydantic models ---

class BrandCreate(BaseModel):
    name: str
    legal_name: str
    address: str
    country: str
    tax_id: str = ""

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be empty or whitespace-only")
        return v

    @field_validator("legal_name")
    @classmethod
    def legal_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("legal_name must not be empty or whitespace-only")
        return v

    @field_validator("address")
    @classmethod
    def address_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("address must not be empty or whitespace-only")
        return v

    @field_validator("country")
    @classmethod
    def country_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("country must not be empty or whitespace-only")
        if v not in VALID_COUNTRIES:
            raise ValueError(f"invalid country: {v!r}")
        return v


class BrandUpdate(BaseModel):
    name: str | None = None
    legal_name: str | None = None
    address: str | None = None
    country: str | None = None
    tax_id: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError("name must not be empty or whitespace-only")
        return v

    @field_validator("legal_name")
    @classmethod
    def legal_name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError("legal_name must not be empty or whitespace-only")
        return v

    @field_validator("address")
    @classmethod
    def address_not_empty(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError("address must not be empty or whitespace-only")
        return v

    @field_validator("country")
    @classmethod
    def country_valid(cls, v: str | None) -> str | None:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("country must not be empty or whitespace-only")
            if v not in VALID_COUNTRIES:
                raise ValueError(f"invalid country: {v!r}")
        return v


class BrandVendorAssign(BaseModel):
    vendor_id: str


# --- Response helper ---

def _brand_to_dict(brand: Brand) -> dict:
    return {
        "id": brand.id,
        "name": brand.name,
        "legal_name": brand.legal_name,
        "address": brand.address,
        "country": brand.country,
        "tax_id": brand.tax_id,
        "status": brand.status.value,
        "created_at": brand.created_at.isoformat(),
        "updated_at": brand.updated_at.isoformat(),
    }


# --- Endpoints ---

@router.get("/")
async def list_brands(
    repo: BrandRepoDep,
    status: str | None = None,
    _user: User = require_role(UserRole.SM),
) -> list[dict]:
    brand_status: BrandStatus | None = None
    if status is not None:
        try:
            brand_status = BrandStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status value: {status!r}")
    brands = await repo.list(brand_status)
    return [_brand_to_dict(b) for b in brands]


@router.get("/{brand_id}")
async def get_brand(
    brand_id: str,
    repo: BrandRepoDep,
    _user: User = require_role(UserRole.SM),
) -> dict:
    brand = await repo.get(brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    return _brand_to_dict(brand)


@router.post("/", status_code=201)
async def create_brand(
    request: Request,
    body: BrandCreate,
    repo: BrandRepoDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_role(UserRole.ADMIN),
) -> dict:
    current_user = getattr(request.state, "current_user", None)
    brand = Brand.create(
        name=body.name,
        legal_name=body.legal_name,
        address=body.address,
        country=body.country,
        tax_id=body.tax_id,
    )
    try:
        await repo.save(brand)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await activity_repo.append(
        entity_type=EntityType.BRAND,
        entity_id=brand.id,
        event=ActivityEvent.BRAND_CREATED,
        detail=f"Brand {brand.name!r} created",
        actor_id=current_user.id if current_user else None,
    )
    return _brand_to_dict(brand)


@router.patch("/{brand_id}")
async def update_brand(
    brand_id: str,
    request: Request,
    body: BrandUpdate,
    repo: BrandRepoDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_role(UserRole.ADMIN),
) -> dict:
    current_user = getattr(request.state, "current_user", None)
    brand = await repo.get(brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    try:
        brand.update(
            name=body.name,
            legal_name=body.legal_name,
            address=body.address,
            country=body.country,
            tax_id=body.tax_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repo.save(brand)
    await activity_repo.append(
        entity_type=EntityType.BRAND,
        entity_id=brand.id,
        event=ActivityEvent.BRAND_UPDATED,
        detail=f"Brand {brand.name!r} updated",
        actor_id=current_user.id if current_user else None,
    )
    return _brand_to_dict(brand)


@router.post("/{brand_id}/deactivate")
async def deactivate_brand(
    brand_id: str,
    request: Request,
    repo: BrandRepoDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_role(UserRole.ADMIN),
) -> dict:
    current_user = getattr(request.state, "current_user", None)
    brand = await repo.get(brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    active_pos = await repo.count_active_pos(brand_id)
    if active_pos > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Brand has {active_pos} active POs; close them before deactivating",
        )
    try:
        brand.deactivate()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(brand)
    await activity_repo.append(
        entity_type=EntityType.BRAND,
        entity_id=brand.id,
        event=ActivityEvent.BRAND_DEACTIVATED,
        detail=f"Brand {brand.name!r} deactivated",
        actor_id=current_user.id if current_user else None,
    )
    return _brand_to_dict(brand)


@router.post("/{brand_id}/reactivate")
async def reactivate_brand(
    brand_id: str,
    request: Request,
    repo: BrandRepoDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_role(UserRole.ADMIN),
) -> dict:
    current_user = getattr(request.state, "current_user", None)
    brand = await repo.get(brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    try:
        brand.reactivate()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(brand)
    await activity_repo.append(
        entity_type=EntityType.BRAND,
        entity_id=brand.id,
        event=ActivityEvent.BRAND_REACTIVATED,
        detail=f"Brand {brand.name!r} reactivated",
        actor_id=current_user.id if current_user else None,
    )
    return _brand_to_dict(brand)


@router.get("/{brand_id}/vendors")
async def list_brand_vendors(
    brand_id: str,
    repo: BrandRepoDep,
    vendor_repo: VendorRepoDep,
    _user: User = require_role(UserRole.SM),
) -> list[dict]:
    brand = await repo.get(brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    vendor_ids = await repo.list_vendor_ids(brand_id)
    vendors = []
    for vid in vendor_ids:
        v = await vendor_repo.get_by_id(vid)
        if v is not None:
            vendors.append({
                "id": v.id,
                "name": v.name,
                "country": v.country,
                "status": v.status.value,
                "vendor_type": v.vendor_type.value,
                "address": v.address,
            })
    return vendors


@router.post("/{brand_id}/vendors")
async def assign_vendor_to_brand(
    brand_id: str,
    request: Request,
    body: BrandVendorAssign,
    repo: BrandRepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_role(UserRole.ADMIN),
) -> dict:
    current_user = getattr(request.state, "current_user", None)
    brand = await repo.get(brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    vendor = await vendor_repo.get_by_id(body.vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    await repo.assign_vendor(brand_id, body.vendor_id)
    await activity_repo.append(
        entity_type=EntityType.BRAND,
        entity_id=brand_id,
        event=ActivityEvent.BRAND_VENDOR_ASSIGNED,
        detail=json.dumps({"vendor_id": body.vendor_id}),
        actor_id=current_user.id if current_user else None,
    )
    return {"brand_id": brand_id, "vendor_id": body.vendor_id}


@router.delete("/{brand_id}/vendors/{vendor_id}")
async def unassign_vendor_from_brand(
    brand_id: str,
    vendor_id: str,
    request: Request,
    repo: BrandRepoDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_role(UserRole.ADMIN),
) -> dict:
    current_user = getattr(request.state, "current_user", None)
    brand = await repo.get(brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    active_pos = await repo.count_active_pos_for_brand_vendor(brand_id, vendor_id)
    if active_pos > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot unassign: {active_pos} active PO(s) use this brand+vendor pair",
        )
    await repo.unassign_vendor(brand_id, vendor_id)
    await activity_repo.append(
        entity_type=EntityType.BRAND,
        entity_id=brand_id,
        event=ActivityEvent.BRAND_VENDOR_UNASSIGNED,
        detail=json.dumps({"vendor_id": vendor_id}),
        actor_id=current_user.id if current_user else None,
    )
    return {"brand_id": brand_id, "vendor_id": vendor_id}
