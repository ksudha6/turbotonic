from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

from src.domain.milestone import MilestoneUpdate, ProductionMilestone


def _iso(dt: datetime) -> str:
    # Store all datetimes as UTC ISO 8601 strings.
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    # datetime.fromisoformat handles the +00:00 suffix from isoformat().
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class MilestoneRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def save(self, po_id: str, update: MilestoneUpdate) -> None:
        await self._conn.execute(
            """
            INSERT INTO milestone_updates (id, po_id, milestone, posted_at)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid4()), po_id, update.milestone.value, _iso(update.posted_at)),
        )
        await self._conn.commit()

    async def list_by_po(self, po_id: str) -> list[MilestoneUpdate]:
        async with self._conn.execute(
            "SELECT milestone, posted_at FROM milestone_updates WHERE po_id = ? ORDER BY posted_at",
            (po_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            MilestoneUpdate(
                milestone=ProductionMilestone(row[0]),
                posted_at=_parse_dt(row[1]),
            )
            for row in rows
        ]

    async def latest_for_po(self, po_id: str) -> MilestoneUpdate | None:
        async with self._conn.execute(
            "SELECT milestone, posted_at FROM milestone_updates WHERE po_id = ? ORDER BY posted_at DESC LIMIT 1",
            (po_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        return MilestoneUpdate(
            milestone=ProductionMilestone(row[0]),
            posted_at=_parse_dt(row[1]),
        )
