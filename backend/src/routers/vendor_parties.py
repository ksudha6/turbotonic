from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import require_role
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.reference_data import VALID_COUNTRIES
from src.domain.user import User, UserRole
from src.domain.vendor_party import VendorParty, VendorPartyInUseError, VendorPartyRole, VendorPartyValidationError
from src.vendor_party_repository import VendorPartyRepository
from src.vendor_repository import VendorRepository

router = APIRouter(prefix="/api/v1/vendors/{vendor_id}/parties", tags=["vendor-parties"], redirect_slashes=False)


async def get_vendor_party_repo() -> AsyncIterator[VendorPartyRepository]:
    async with get_db() as conn:
        yield VendorPartyRepository(conn)


async def get_vendor_repo_for_parties() -> AsyncIterator[VendorRepository]:
    async with get_db() as conn:
        yield VendorRepository(conn)


async def get_activity_repo_for_parties() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


VendorPartyRepoDep = Annotated[VendorPartyRepository, Depends(get_vendor_party_repo)]
VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo_for_parties)]
ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo_for_parties)]


class VendorPartyCreate(BaseModel):
    role: str
    legal_name: str
    address: str
    country: str
    tax_id: str = ""
    banking_details: str = ""

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        upper = v.upper()
        try:
            VendorPartyRole(upper)
        except ValueError:
            raise ValueError(f"role must be one of: {', '.join(r.value for r in VendorPartyRole)}")
        return upper

    @field_validator("country")
    @classmethod
    def country_valid(cls, v: str) -> str:
        if v not in VALID_COUNTRIES:
            raise ValueError(f"country must be a valid country code; got {v!r}")
        return v

    @field_validator("legal_name", "address")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace-only")
        return v


class VendorPartyUpdate(BaseModel):
    legal_name: str | None = None
    address: str | None = None
    country: str | None = None
    tax_id: str | None = None
    banking_details: str | None = None


class VendorPartyResponse(BaseModel):
    id: str
    vendor_id: str
    role: str
    legal_name: str
    address: str
    country: str
    tax_id: str
    banking_details: str
    created_at: datetime
    updated_at: datetime


def _to_response(party: VendorParty) -> VendorPartyResponse:
    return VendorPartyResponse(
        id=party.id,
        vendor_id=party.vendor_id,
        role=party.role.value,
        legal_name=party.legal_name,
        address=party.address,
        country=party.country,
        tax_id=party.tax_id,
        banking_details=party.banking_details,
        created_at=party.created_at,
        updated_at=party.updated_at,
    )


@router.get("", response_model=list[VendorPartyResponse])
async def list_vendor_parties(
    vendor_id: str,
    repo: VendorPartyRepoDep,
    vendor_repo: VendorRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.ADMIN),
) -> list[VendorPartyResponse]:
    vendor = await vendor_repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    parties = await repo.list_by_vendor(vendor_id)
    return [_to_response(p) for p in parties]


@router.get("/{party_id}", response_model=VendorPartyResponse)
async def get_vendor_party(
    vendor_id: str,
    party_id: str,
    repo: VendorPartyRepoDep,
    vendor_repo: VendorRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.ADMIN),
) -> VendorPartyResponse:
    vendor = await vendor_repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    party = await repo.get(party_id)
    if party is None or party.vendor_id != vendor_id:
        raise HTTPException(status_code=404, detail="VendorParty not found")
    return _to_response(party)


@router.post("", response_model=VendorPartyResponse, status_code=201)
async def create_vendor_party(
    vendor_id: str,
    body: VendorPartyCreate,
    repo: VendorPartyRepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.ADMIN),
) -> VendorPartyResponse:
    vendor = await vendor_repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    try:
        party = await repo.create(
            vendor_id=vendor_id,
            role=VendorPartyRole(body.role),
            legal_name=body.legal_name,
            address=body.address,
            country=body.country,
            tax_id=body.tax_id,
            banking_details=body.banking_details,
        )
    except VendorPartyValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await activity_repo.append(
        entity_type=EntityType.VENDOR_PARTY,
        entity_id=party.id,
        event=ActivityEvent.VENDOR_PARTY_ADDED,
        actor_id=user.id,
        detail=json.dumps({"vendor_id": vendor_id, "role": party.role.value}),
    )
    return _to_response(party)


@router.patch("/{party_id}", response_model=VendorPartyResponse)
async def patch_vendor_party(
    vendor_id: str,
    party_id: str,
    body: VendorPartyUpdate,
    repo: VendorPartyRepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.ADMIN),
) -> VendorPartyResponse:
    vendor = await vendor_repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    existing = await repo.get(party_id)
    if existing is None or existing.vendor_id != vendor_id:
        raise HTTPException(status_code=404, detail="VendorParty not found")
    update_kwargs = {
        k: v for k, v in body.model_dump().items() if v is not None
    }
    if update_kwargs:
        try:
            party = await repo.update(party_id, **update_kwargs)
        except VendorPartyValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        party = existing
    await activity_repo.append(
        entity_type=EntityType.VENDOR_PARTY,
        entity_id=party.id,
        event=ActivityEvent.VENDOR_PARTY_UPDATED,
        actor_id=user.id,
        detail=json.dumps({"vendor_id": vendor_id, "role": party.role.value}),
    )
    return _to_response(party)


@router.delete("/{party_id}", status_code=204)
async def delete_vendor_party(
    vendor_id: str,
    party_id: str,
    repo: VendorPartyRepoDep,
    vendor_repo: VendorRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_role(UserRole.ADMIN),
) -> None:
    vendor = await vendor_repo.get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    existing = await repo.get(party_id)
    if existing is None or existing.vendor_id != vendor_id:
        raise HTTPException(status_code=404, detail="VendorParty not found")
    try:
        await repo.delete(party_id)
    except VendorPartyInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await activity_repo.append(
        entity_type=EntityType.VENDOR_PARTY,
        entity_id=party_id,
        event=ActivityEvent.VENDOR_PARTY_REMOVED,
        actor_id=user.id,
        detail=json.dumps({"vendor_id": vendor_id, "role": existing.role.value}),
    )
