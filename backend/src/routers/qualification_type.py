from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import require_role
from src.db import get_db
from src.domain.qualification_type import QualificationType
from src.domain.user import User, UserRole
from src.qualification_type_dto import (
    QualificationTypeCreate,
    QualificationTypeListItem,
    QualificationTypeResponse,
    QualificationTypeUpdate,
    qualification_type_to_list_item,
    qualification_type_to_response,
)
from src.qualification_type_repository import QualificationTypeRepository

router = APIRouter(tags=["qualification_types"])


async def get_qt_repo() -> AsyncIterator[QualificationTypeRepository]:
    async with get_db() as conn:
        yield QualificationTypeRepository(conn)


QtRepoDep = Annotated[QualificationTypeRepository, Depends(get_qt_repo)]


# ---------------------------------------------------------------------------
# QualificationType CRUD
# ---------------------------------------------------------------------------

@router.post("/api/v1/qualification-types", response_model=QualificationTypeResponse, status_code=201)
async def create_qualification_type(
    body: QualificationTypeCreate,
    repo: QtRepoDep,
    _user: User = require_role(UserRole.SM),
) -> QualificationTypeResponse:
    existing = await repo.get_by_name(body.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail="QualificationType with this name already exists")
    qt = QualificationType.create(
        name=body.name,
        description=body.description,
        target_market=body.target_market,
        applies_to_category=body.applies_to_category,
    )
    try:
        await repo.save(qt)
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise HTTPException(
                status_code=409, detail="QualificationType with this name already exists"
            ) from exc
        raise
    return qualification_type_to_response(qt)


@router.get("/api/v1/qualification-types", response_model=list[QualificationTypeListItem])
async def list_qualification_types(
    repo: QtRepoDep,
    _user: User = require_role(UserRole.SM),
) -> list[QualificationTypeListItem]:
    qts = await repo.list_all()
    return [qualification_type_to_list_item(qt) for qt in qts]


@router.get("/api/v1/qualification-types/{qt_id}", response_model=QualificationTypeResponse)
async def get_qualification_type(
    qt_id: str,
    repo: QtRepoDep,
    _user: User = require_role(UserRole.SM),
) -> QualificationTypeResponse:
    qt = await repo.get_by_id(qt_id)
    if qt is None:
        raise HTTPException(status_code=404, detail="QualificationType not found")
    return qualification_type_to_response(qt)


@router.patch("/api/v1/qualification-types/{qt_id}", response_model=QualificationTypeResponse)
async def update_qualification_type(
    qt_id: str,
    body: QualificationTypeUpdate,
    repo: QtRepoDep,
    _user: User = require_role(UserRole.SM),
) -> QualificationTypeResponse:
    qt = await repo.get_by_id(qt_id)
    if qt is None:
        raise HTTPException(status_code=404, detail="QualificationType not found")
    qt.update(
        name=body.name,
        description=body.description,
        target_market=body.target_market,
        applies_to_category=body.applies_to_category,
    )
    await repo.save(qt)
    return qualification_type_to_response(qt)


@router.delete("/api/v1/qualification-types/{qt_id}", status_code=204)
async def delete_qualification_type(
    qt_id: str,
    repo: QtRepoDep,
    _user: User = require_role(UserRole.SM),
) -> None:
    qt = await repo.get_by_id(qt_id)
    if qt is None:
        raise HTTPException(status_code=404, detail="QualificationType not found")
    try:
        await repo.delete(qt_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Product qualifications sub-resource
# ---------------------------------------------------------------------------

@router.post("/api/v1/products/{product_id}/qualifications", status_code=201)
async def assign_qualification_to_product(
    product_id: str,
    body: dict,
    repo: QtRepoDep,
    _user: User = require_role(UserRole.SM),
) -> dict[str, str]:
    qt_id: str = body.get("qualification_type_id", "")
    if not qt_id:
        raise HTTPException(status_code=422, detail="qualification_type_id is required")
    qt = await repo.get_by_id(qt_id)
    if qt is None:
        raise HTTPException(status_code=404, detail="QualificationType not found")
    await repo.assign_to_product(product_id, qt_id)
    return {"product_id": product_id, "qualification_type_id": qt_id}


@router.delete("/api/v1/products/{product_id}/qualifications/{qt_id}", status_code=204)
async def remove_qualification_from_product(
    product_id: str,
    qt_id: str,
    repo: QtRepoDep,
    _user: User = require_role(UserRole.SM),
) -> None:
    await repo.remove_from_product(product_id, qt_id)


@router.get("/api/v1/products/{product_id}/qualifications", response_model=list[QualificationTypeListItem])
async def list_product_qualifications(
    product_id: str,
    repo: QtRepoDep,
    _user: User = require_role(UserRole.SM, UserRole.QUALITY_LAB),
) -> list[QualificationTypeListItem]:
    qts = await repo.list_by_product(product_id)
    return [qualification_type_to_list_item(qt) for qt in qts]
