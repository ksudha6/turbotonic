from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException

from src.db import get_db
from src.domain.vendor import Vendor, VendorStatus
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
        await conn.execute("PRAGMA foreign_keys = ON")
        yield VendorRepository(conn)


VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo)]


@router.post("/", response_model=VendorResponse, status_code=201)
async def create_vendor(body: VendorCreate, repo: VendorRepoDep) -> VendorResponse:
    vendor = Vendor.create(name=body.name, country=body.country)
    await repo.save(vendor)
    return vendor_to_response(vendor)


@router.get("/", response_model=list[VendorListItem])
async def list_vendors(
    repo: VendorRepoDep,
    status: str | None = None,
) -> list[VendorListItem]:
    vendor_status: VendorStatus | None = None
    if status is not None:
        try:
            vendor_status = VendorStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status value: {status!r}")
    vendors = await repo.list_vendors(vendor_status)
    return [vendor_to_list_item(v) for v in vendors]


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(vendor_id: str, repo: VendorRepoDep) -> VendorResponse:
    vendor = await repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor_to_response(vendor)


@router.post("/{vendor_id}/deactivate", response_model=VendorResponse)
async def deactivate_vendor(vendor_id: str, repo: VendorRepoDep) -> VendorResponse:
    vendor = await repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    try:
        vendor.deactivate()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(vendor)
    return vendor_to_response(vendor)
