from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import asyncpg

from src.domain.activity import (
    ActivityEvent,
    ActivityLogEntry,
    EntityType,
    EVENT_METADATA,
    NotificationCategory,
    TargetRole,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class ActivityLogRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def append(
        self,
        entity_type: EntityType,
        entity_id: str,
        event: ActivityEvent,
        detail: str | None = None,
    ) -> None:
        category, target_role = EVENT_METADATA[event]
        now = datetime.now(UTC)
        await self._conn.execute(
            """
            INSERT INTO activity_log
                (id, entity_type, entity_id, event, category, target_role, actor_id, detail, read_at, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NULL, $7, NULL, $8)
            """,
            str(uuid4()),
            entity_type.value,
            entity_id,
            event.value,
            category.value,
            target_role.value if target_role is not None else None,
            detail,
            _iso(now),
        )

    async def list_recent(self, limit: int = 20) -> list[ActivityLogEntry]:
        rows = await self._conn.fetch(
            "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT $1",
            limit,
        )
        return [_row_to_entry(row) for row in rows]

    async def list_for_entity(
        self, entity_type: EntityType, entity_id: str
    ) -> list[ActivityLogEntry]:
        rows = await self._conn.fetch(
            """
            SELECT * FROM activity_log
            WHERE entity_type = $1 AND entity_id = $2
            ORDER BY created_at ASC
            """,
            entity_type.value, entity_id,
        )
        return [_row_to_entry(row) for row in rows]

    async def unread_count(self) -> int:
        val = await self._conn.fetchval(
            "SELECT COUNT(*) FROM activity_log WHERE read_at IS NULL"
        )
        return val or 0

    async def mark_read(
        self, event_ids: list[str] | None = None, all: bool = False
    ) -> int:
        now_iso = _iso(datetime.now(UTC))
        if all:
            result = await self._conn.execute(
                "UPDATE activity_log SET read_at = $1 WHERE read_at IS NULL",
                now_iso,
            )
            count = int(result.split()[-1])
        elif event_ids:
            placeholders = ",".join(f"${i}" for i in range(2, 2 + len(event_ids)))
            sql = f"UPDATE activity_log SET read_at = $1 WHERE id IN ({placeholders}) AND read_at IS NULL"
            result = await self._conn.execute(sql, now_iso, *event_ids)
            count = int(result.split()[-1])
        else:
            return 0
        return count

    async def has_delayed_entry(self, entity_id: str, detail: str) -> bool:
        row = await self._conn.fetchrow(
            """
            SELECT 1 FROM activity_log
            WHERE entity_id = $1 AND event = $2 AND detail LIKE $3
            LIMIT 1
            """,
            entity_id, ActivityEvent.MILESTONE_OVERDUE.value, f"{detail}%",
        )
        return row is not None


def _row_to_entry(row: asyncpg.Record) -> ActivityLogEntry:
    raw_read_at = row["read_at"]
    raw_target_role = row["target_role"]
    return ActivityLogEntry(
        id=row["id"],
        entity_type=EntityType(row["entity_type"]),
        entity_id=row["entity_id"],
        event=ActivityEvent(row["event"]),
        category=NotificationCategory(row["category"]),
        target_role=TargetRole(raw_target_role) if raw_target_role is not None else None,
        actor_id=row["actor_id"],
        detail=row["detail"],
        read_at=_parse_dt(raw_read_at) if raw_read_at is not None else None,
        created_at=_parse_dt(row["created_at"]),
    )
