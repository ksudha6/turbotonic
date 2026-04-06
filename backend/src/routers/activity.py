from __future__ import annotations

from datetime import datetime
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.activity_repository import ActivityLogRepository
from src.db import get_db
from src.domain.activity import EntityType

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])


async def get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield ActivityLogRepository(conn)


ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo)]


class ActivityLogResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    event: str
    category: str
    target_role: str | None
    detail: str | None
    read_at: datetime | None
    created_at: datetime


class MarkReadRequest(BaseModel):
    event_ids: list[str] | None = None
    all: bool = False


def _entry_to_response(entry) -> ActivityLogResponse:
    return ActivityLogResponse(
        id=entry.id,
        entity_type=entry.entity_type.value,
        entity_id=entry.entity_id,
        event=entry.event.value,
        category=entry.category.value,
        target_role=entry.target_role.value if entry.target_role is not None else None,
        detail=entry.detail,
        read_at=entry.read_at,
        created_at=entry.created_at,
    )


@router.get("/unread-count")
async def get_unread_count(activity_repo: ActivityRepoDep) -> dict[str, int]:
    count = await activity_repo.unread_count()
    return {"count": count}


@router.get("/", response_model=list[ActivityLogResponse])
async def list_activity(
    activity_repo: ActivityRepoDep,
    limit: int = 20,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> list[ActivityLogResponse]:
    if entity_type is not None and entity_id is not None:
        et = EntityType(entity_type.upper())
        entries = await activity_repo.list_for_entity(et, entity_id)
    else:
        entries = await activity_repo.list_recent(limit)
    return [_entry_to_response(e) for e in entries]


@router.post("/mark-read")
async def mark_read(body: MarkReadRequest, activity_repo: ActivityRepoDep) -> dict[str, int]:
    marked = await activity_repo.mark_read(event_ids=body.event_ids, all=body.all)
    return {"marked": marked}
