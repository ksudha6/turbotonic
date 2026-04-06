from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

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
    def __init__(self, conn: aiosqlite.Connection) -> None:
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
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?)
            """,
            (
                str(uuid4()),
                entity_type.value,
                entity_id,
                event.value,
                category.value,
                target_role.value if target_role is not None else None,
                detail,
                _iso(now),
            ),
        )
        await self._conn.commit()

    async def list_recent(self, limit: int = 20) -> list[ActivityLogEntry]:
        self._conn.row_factory = aiosqlite.Row
        async with self._conn.execute(
            "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_entry(row) for row in rows]

    async def list_for_entity(
        self, entity_type: EntityType, entity_id: str
    ) -> list[ActivityLogEntry]:
        self._conn.row_factory = aiosqlite.Row
        async with self._conn.execute(
            """
            SELECT * FROM activity_log
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY created_at ASC
            """,
            (entity_type.value, entity_id),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_entry(row) for row in rows]

    async def unread_count(self) -> int:
        async with self._conn.execute(
            "SELECT COUNT(*) FROM activity_log WHERE read_at IS NULL"
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def mark_read(
        self, event_ids: list[str] | None = None, all: bool = False
    ) -> int:
        now_iso = _iso(datetime.now(UTC))
        if all:
            async with self._conn.execute(
                "UPDATE activity_log SET read_at = ? WHERE read_at IS NULL",
                (now_iso,),
            ) as cursor:
                count = cursor.rowcount
        elif event_ids:
            placeholders = ",".join("?" * len(event_ids))
            async with self._conn.execute(
                f"UPDATE activity_log SET read_at = ? WHERE id IN ({placeholders}) AND read_at IS NULL",
                (now_iso, *event_ids),
            ) as cursor:
                count = cursor.rowcount
        else:
            return 0
        await self._conn.commit()
        return count

    async def has_delayed_entry(self, entity_id: str, detail: str) -> bool:
        async with self._conn.execute(
            """
            SELECT 1 FROM activity_log
            WHERE entity_id = ? AND event = ? AND detail LIKE ?
            LIMIT 1
            """,
            (entity_id, ActivityEvent.MILESTONE_OVERDUE.value, f"{detail}%"),
        ) as cursor:
            row = await cursor.fetchone()
        return row is not None


def _row_to_entry(row: aiosqlite.Row) -> ActivityLogEntry:
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
