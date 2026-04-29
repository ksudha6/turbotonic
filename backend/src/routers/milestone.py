from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import check_vendor_access, require_auth, require_role
from src.certificate_repository import CertificateRepository
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.milestone import (
    MilestoneUpdate,
    ProductionMilestone,
    compute_days_overdue,
    validate_next_milestone,
)
from src.domain.user import User, UserRole
from src.milestone_repository import MilestoneRepository
from src.product_repository import ProductRepository
from src.qualification_type_repository import QualificationTypeRepository
from src.repository import PurchaseOrderRepository
from src.services.quality_gate import check_po_qualifications

router = APIRouter(prefix="/api/v1/po", tags=["milestones"])


async def get_milestone_repo() -> AsyncIterator[MilestoneRepository]:
    async with get_db() as conn:
        yield MilestoneRepository(conn)


async def get_po_repo() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        yield PurchaseOrderRepository(conn)


MilestoneRepoDep = Annotated[MilestoneRepository, Depends(get_milestone_repo)]
PORepoDep = Annotated[PurchaseOrderRepository, Depends(get_po_repo)]


async def get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo)]


async def get_product_repo() -> AsyncIterator[ProductRepository]:
    async with get_db() as conn:
        yield ProductRepository(conn)


ProductRepoDep = Annotated[ProductRepository, Depends(get_product_repo)]


async def get_qualification_repo() -> AsyncIterator[QualificationTypeRepository]:
    async with get_db() as conn:
        yield QualificationTypeRepository(conn)


QualificationRepoDep = Annotated[QualificationTypeRepository, Depends(get_qualification_repo)]


async def get_cert_repo() -> AsyncIterator[CertificateRepository]:
    async with get_db() as conn:
        yield CertificateRepository(conn)


CertRepoDep = Annotated[CertificateRepository, Depends(get_cert_repo)]


class MilestonePostRequest(BaseModel):
    milestone: str


class MilestoneResponse(BaseModel):
    milestone: str
    posted_at: datetime
    # Iter 082: per-row overdue indicators. Only the latest posted milestone
    # may carry is_overdue=True; earlier rows have moved on so are always
    # is_overdue=False, days_overdue=None.
    is_overdue: bool = False
    days_overdue: int | None = None


@router.get("/{po_id}/milestones", response_model=list[MilestoneResponse])
async def list_milestones(
    po_id: str,
    milestone_repo: MilestoneRepoDep,
    po_repo: PORepoDep,
    user: User = require_auth,
) -> list[MilestoneResponse]:
    po = await po_repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)

    updates = await milestone_repo.list_by_po(po_id)
    if not updates:
        return []

    now_utc = datetime.now(UTC)
    # The latest update is the "stuck" stage; earlier rows are not overdue
    # because the PO has progressed past them.
    latest_index = len(updates) - 1
    response: list[MilestoneResponse] = []
    for i, u in enumerate(updates):
        is_overdue = False
        days_overdue: int | None = None
        if i == latest_index:
            days = compute_days_overdue(u.milestone, u.posted_at, now_utc)
            if days is not None and days > 0:
                is_overdue = True
                days_overdue = days
        response.append(
            MilestoneResponse(
                milestone=u.milestone.value,
                posted_at=u.posted_at,
                is_overdue=is_overdue,
                days_overdue=days_overdue,
            )
        )
    return response


@router.post("/{po_id}/milestones", response_model=MilestoneResponse, status_code=201)
async def post_milestone(
    po_id: str,
    body: MilestonePostRequest,
    milestone_repo: MilestoneRepoDep,
    po_repo: PORepoDep,
    activity_repo: ActivityRepoDep,
    product_repo: ProductRepoDep,
    qualification_repo: QualificationRepoDep,
    cert_repo: CertRepoDep,
    user: User = require_role(UserRole.VENDOR, UserRole.SM),
) -> MilestoneResponse:
    # Reject empty or whitespace-only milestone values before enum lookup.
    if not body.milestone or not body.milestone.strip():
        raise HTTPException(status_code=422, detail="milestone must not be empty or whitespace-only")

    try:
        proposed = ProductionMilestone(body.milestone.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"invalid milestone value: {body.milestone!r}",
        ) from exc

    po = await po_repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    check_vendor_access(user, po.vendor_id)

    if po.status.value != "ACCEPTED" or po.po_type.value != "PROCUREMENT":
        raise HTTPException(
            status_code=409,
            detail="milestone updates require an ACCEPTED PROCUREMENT purchase order",
        )

    existing = await milestone_repo.list_by_po(po_id)

    try:
        validate_next_milestone(existing, proposed)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    update = MilestoneUpdate(milestone=proposed, posted_at=datetime.now(UTC))
    await milestone_repo.save(po_id, update)
    await activity_repo.append(EntityType.PO, po_id, ActivityEvent.MILESTONE_POSTED, detail=update.milestone.value)

    # On QC_PASSED: emit CERT_REQUESTED for each product line missing valid cert coverage.
    if proposed is ProductionMilestone.QC_PASSED:
        warnings = await check_po_qualifications(po, product_repo, qualification_repo, cert_repo)
        for warning in warnings:
            detail = f"Product {warning.part_number} requires {warning.qualification_name}"
            if po.marketplace:
                detail = f"{detail} for market {po.marketplace}"
            await activity_repo.append(
                EntityType.CERTIFICATE,
                warning.product_id,
                ActivityEvent.CERT_REQUESTED,
                detail=detail,
            )

    # A freshly posted milestone is current, not overdue yet.
    return MilestoneResponse(
        milestone=update.milestone.value,
        posted_at=update.posted_at,
        is_overdue=False,
        days_overdue=None,
    )
