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
    VendorPatch,
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
    vendor = Vendor.create(name=body.name, country=body.country, vendor_type=vendor_type, address=body.address, account_details=body.account_details, tax_id=body.tax_id)
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


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def patch_vendor(
    vendor_id: str,
    body: VendorPatch,
    repo: VendorRepoDep,
    _user: User = require_role(UserRole.ADMIN),
) -> VendorResponse:
    """Iter 110+113: partial update for vendor attributes (tax_id, default party FKs)."""
    from datetime import UTC, datetime
    from src.domain.vendor_party import VendorPartyRole
    from src.vendor_party_repository import VendorPartyRepository

    vendor = await repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if body.tax_id is not None:
        vendor.tax_id = body.tax_id
        vendor.updated_at = datetime.now(UTC)

    # Validate and set each default party FK.
    # party_repo shares the same connection as vendor_repo via the same DI function.
    async def _validate_and_set_default(
        field_value: str | None,
        expected_role: VendorPartyRole,
        setter_role: VendorPartyRole,
    ) -> str | None:
        if field_value is None:
            return None
        # We need party_repo; create it inline sharing the same conn.
        # The vendor repo's internal conn is accessed via the dependency override pattern.
        # Use a local import to avoid a circular dep at module level.
        from src.db import get_db as _get_db  # noqa: F401 — not actually used here
        # Reuse the connection from the vendor repo dependency (same DB session per request).
        party_row = await repo._conn.fetchrow(
            "SELECT vendor_id, role FROM vendor_parties WHERE id = $1", field_value
        )
        if party_row is None:
            raise HTTPException(
                status_code=422,
                detail=f"VendorParty {field_value!r} not found",
            )
        if party_row["vendor_id"] != vendor_id:
            raise HTTPException(
                status_code=422,
                detail=f"VendorParty {field_value!r} belongs to a different vendor",
            )
        if party_row["role"] != expected_role.value:
            raise HTTPException(
                status_code=422,
                detail=f"VendorParty {field_value!r} has role {party_row['role']!r}; expected {expected_role.value!r}",
            )
        return field_value

    if body.default_seller_party_id is not None:
        validated = await _validate_and_set_default(
            body.default_seller_party_id,
            VendorPartyRole.SELLER,
            VendorPartyRole.SELLER,
        )
        vendor.default_seller_party_id = validated
        vendor.updated_at = datetime.now(UTC)
    if body.default_shipper_party_id is not None:
        validated = await _validate_and_set_default(
            body.default_shipper_party_id,
            VendorPartyRole.SHIPPER,
            VendorPartyRole.SHIPPER,
        )
        vendor.default_shipper_party_id = validated
        vendor.updated_at = datetime.now(UTC)
    if body.default_remit_to_party_id is not None:
        validated = await _validate_and_set_default(
            body.default_remit_to_party_id,
            VendorPartyRole.REMIT_TO,
            VendorPartyRole.REMIT_TO,
        )
        vendor.default_remit_to_party_id = validated
        vendor.updated_at = datetime.now(UTC)

    await repo.save(vendor)
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
