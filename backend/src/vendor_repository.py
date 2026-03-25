from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

from src.domain.vendor import Vendor, VendorStatus


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class VendorRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def save(self, vendor: Vendor) -> None:
        # Check if vendor exists
        async with self._conn.execute(
            "SELECT COUNT(*) FROM vendors WHERE id = ?", (vendor.id,)
        ) as cursor:
            row = await cursor.fetchone()
            exists = (row[0] if row else 0) > 0

        if not exists:
            await self._conn.execute(
                """
                INSERT INTO vendors (id, name, country, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (vendor.id, vendor.name, vendor.country, vendor.status.value,
                 _iso(vendor.created_at), _iso(vendor.updated_at)),
            )
        else:
            await self._conn.execute(
                """
                UPDATE vendors SET name = ?, country = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (vendor.name, vendor.country, vendor.status.value,
                 _iso(vendor.updated_at), vendor.id),
            )
        await self._conn.commit()

    async def get_by_id(self, vendor_id: str) -> Vendor | None:
        self._conn.row_factory = aiosqlite.Row
        async with self._conn.execute(
            "SELECT * FROM vendors WHERE id = ?", (vendor_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _reconstruct(row)

    async def list_vendors(self, status: VendorStatus | None = None) -> list[Vendor]:
        self._conn.row_factory = aiosqlite.Row
        if status is not None:
            async with self._conn.execute(
                "SELECT * FROM vendors WHERE status = ?", (status.value,)
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with self._conn.execute("SELECT * FROM vendors") as cursor:
                rows = await cursor.fetchall()
        return [_reconstruct(row) for row in rows]

    async def vendor_count_by_status(self) -> dict[str, int]:
        self._conn.row_factory = aiosqlite.Row
        async with self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM vendors GROUP BY status"
        ) as cursor:
            rows = await cursor.fetchall()
        return {row["status"]: row["cnt"] for row in rows}


def _reconstruct(row: aiosqlite.Row) -> Vendor:
    return Vendor(
        id=row["id"],
        name=row["name"],
        country=row["country"],
        status=VendorStatus(row["status"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )
