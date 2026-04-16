from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import require_role
from src.db import get_db
from src.domain.user import User, UserRole
from src.domain.vendor import Vendor, VendorStatus, VendorType
from src.vendor_dto import (
    VendorCreate,
    VendorListItem,
    VendorResponse,
    vendor_to_list_item,
    vendor_to_response,
)
from src.vendor_repository import VendorRepository

router = APIRouter(prefix="/api/v1/vendors", tags=["vendors"])


async def get_vendor_repo() -> AsyncIterator[VendorRepository]:
    async with get_db() as conn:
        yield VendorRepository(conn)


VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo)]


@router.post("/", response_model=VendorResponse, status_code=201)
async def create_vendor(body: VendorCreate, repo: VendorRepoDep, _user: User = require_role(UserRole.SM)) -> VendorResponse:
    vendor_type = VendorType(body.vendor_type)
    vendor = Vendor.create(name=body.name, country=body.country, vendor_type=vendor_type, address=body.address, account_details=body.account_details)
    await repo.save(vendor)
    return vendor_to_response(vendor)


@router.get("/", response_model=list[VendorListItem])
async def list_vendors(
    repo: VendorRepoDep,
    status: str | None = None,
    vendor_type: str | None = None,
    _user: User = require_role(UserRole.SM),
) -> list[VendorListItem]:
    vendor_status: VendorStatus | None = None
    if status is not None:
        try:
            vendor_status = VendorStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status value: {status!r}")
    vtype: VendorType | None = None
    if vendor_type is not None:
        try:
            vtype = VendorType(vendor_type.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid vendor_type value: {vendor_type!r}")
    vendors = await repo.list_vendors(vendor_status, vendor_type=vtype)
    return [vendor_to_list_item(v) for v in vendors]


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(vendor_id: str, repo: VendorRepoDep, _user: User = require_role(UserRole.SM)) -> VendorResponse:
    vendor = await repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor_to_response(vendor)


@router.post("/{vendor_id}/deactivate", response_model=VendorResponse)
async def deactivate_vendor(vendor_id: str, repo: VendorRepoDep, _user: User = require_role(UserRole.SM)) -> VendorResponse:
    vendor = await repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    try:
        vendor.deactivate()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(vendor)
    return vendor_to_response(vendor)


@router.post("/{vendor_id}/reactivate", response_model=VendorResponse)
async def reactivate_vendor(vendor_id: str, repo: VendorRepoDep, _user: User = require_role(UserRole.SM)) -> VendorResponse:
    vendor = await repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    try:
        vendor.reactivate()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(vendor)
    return vendor_to_response(vendor)
