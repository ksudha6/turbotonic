from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.activity_repository import ActivityLogRepository
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.milestone import (
    MilestoneUpdate,
    ProductionMilestone,
    validate_next_milestone,
)
from src.milestone_repository import MilestoneRepository
from src.repository import PurchaseOrderRepository

router = APIRouter(prefix="/api/v1/po", tags=["milestones"])


async def get_milestone_repo() -> AsyncIterator[MilestoneRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield MilestoneRepository(conn)


async def get_po_repo() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield PurchaseOrderRepository(conn)


MilestoneRepoDep = Annotated[MilestoneRepository, Depends(get_milestone_repo)]
PORepoDep = Annotated[PurchaseOrderRepository, Depends(get_po_repo)]


async def get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield ActivityLogRepository(conn)


ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo)]


class MilestonePostRequest(BaseModel):
    milestone: str


class MilestoneResponse(BaseModel):
    milestone: str
    posted_at: datetime


@router.get("/{po_id}/milestones", response_model=list[MilestoneResponse])
async def list_milestones(
    po_id: str,
    milestone_repo: MilestoneRepoDep,
    po_repo: PORepoDep,
) -> list[MilestoneResponse]:
    po = await po_repo.get(po_id)
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    updates = await milestone_repo.list_by_po(po_id)
    return [
        MilestoneResponse(milestone=u.milestone.value, posted_at=u.posted_at)
        for u in updates
    ]


@router.post("/{po_id}/milestones", response_model=MilestoneResponse, status_code=201)
async def post_milestone(
    po_id: str,
    body: MilestonePostRequest,
    milestone_repo: MilestoneRepoDep,
    po_repo: PORepoDep,
    activity_repo: ActivityRepoDep,
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

    return MilestoneResponse(milestone=update.milestone.value, posted_at=update.posted_at)
