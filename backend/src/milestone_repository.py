from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import asyncpg

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
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, po_id: str, update: MilestoneUpdate) -> None:
        await self._conn.execute(
            """
            INSERT INTO milestone_updates (id, po_id, milestone, posted_at)
            VALUES ($1, $2, $3, $4)
            """,
            str(uuid4()), po_id, update.milestone.value, _iso(update.posted_at),
        )

    async def list_by_po(self, po_id: str) -> list[MilestoneUpdate]:
        rows = await self._conn.fetch(
            "SELECT milestone, posted_at FROM milestone_updates WHERE po_id = $1 ORDER BY posted_at",
            po_id,
        )

        return [
            MilestoneUpdate(
                milestone=ProductionMilestone(row[0]),
                posted_at=_parse_dt(row[1]),
            )
            for row in rows
        ]

    async def latest_for_po(self, po_id: str) -> MilestoneUpdate | None:
        row = await self._conn.fetchrow(
            "SELECT milestone, posted_at FROM milestone_updates WHERE po_id = $1 ORDER BY posted_at DESC LIMIT 1",
            po_id,
        )

        if row is None:
            return None

        return MilestoneUpdate(
            milestone=ProductionMilestone(row[0]),
            posted_at=_parse_dt(row[1]),
        )
