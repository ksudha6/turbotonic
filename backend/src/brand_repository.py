from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import asyncpg

from src.domain.brand import Brand, BrandStatus
from src.domain.purchase_order import POStatus


# Non-terminal PO statuses used by the deactivate guard
_ACTIVE_PO_STATUSES: tuple[str, ...] = (
    POStatus.DRAFT.value,
    POStatus.PENDING.value,
    POStatus.MODIFIED.value,
    POStatus.REVISED.value,
    POStatus.ACCEPTED.value,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class BrandRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, brand: Brand) -> None:
        # Check if brand exists by id
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM brands WHERE id = $1", brand.id
        )
        exists = (count or 0) > 0

        if not exists:
            try:
                await self._conn.execute(
                    """
                    INSERT INTO brands (id, name, legal_name, address, country, tax_id, status, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    brand.id, brand.name, brand.legal_name, brand.address,
                    brand.country, brand.tax_id, brand.status.value,
                    _iso(brand.created_at), _iso(brand.updated_at),
                )
            except asyncpg.UniqueViolationError as e:
                raise ValueError(f"brand name {brand.name!r} already exists") from e
        else:
            await self._conn.execute(
                """
                UPDATE brands SET name = $1, legal_name = $2, address = $3, country = $4,
                    tax_id = $5, status = $6, updated_at = $7
                WHERE id = $8
                """,
                brand.name, brand.legal_name, brand.address, brand.country,
                brand.tax_id, brand.status.value, _iso(brand.updated_at), brand.id,
            )

    async def get(self, brand_id: str) -> Brand | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM brands WHERE id = $1", brand_id
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def list(self, status: BrandStatus | None = None) -> list[Brand]:
        if status is not None:
            rows = await self._conn.fetch(
                "SELECT * FROM brands WHERE status = $1 ORDER BY name", status.value
            )
        else:
            rows = await self._conn.fetch("SELECT * FROM brands ORDER BY name")
        return [_reconstruct(row) for row in rows]

    async def delete(self, brand_id: str) -> None:
        await self._conn.execute("DELETE FROM brands WHERE id = $1", brand_id)

    async def assign_vendor(self, brand_id: str, vendor_id: str) -> None:
        # Idempotent: ON CONFLICT DO NOTHING means double-assign is safe
        await self._conn.execute(
            """
            INSERT INTO brand_vendors (brand_id, vendor_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            brand_id, vendor_id,
        )

    async def unassign_vendor(self, brand_id: str, vendor_id: str) -> None:
        await self._conn.execute(
            "DELETE FROM brand_vendors WHERE brand_id = $1 AND vendor_id = $2",
            brand_id, vendor_id,
        )

    async def list_vendor_ids(self, brand_id: str) -> list[str]:
        rows = await self._conn.fetch(
            "SELECT vendor_id FROM brand_vendors WHERE brand_id = $1 ORDER BY vendor_id",
            brand_id,
        )
        return [row["vendor_id"] for row in rows]

    async def list_brand_ids_for_vendor(self, vendor_id: str) -> list[str]:
        rows = await self._conn.fetch(
            "SELECT brand_id FROM brand_vendors WHERE vendor_id = $1 ORDER BY brand_id",
            vendor_id,
        )
        return [row["brand_id"] for row in rows]

    async def count_active_pos(self, brand_id: str) -> int:
        # Counts POs in non-terminal statuses (Draft, Pending, Modified, Revised, Accepted)
        placeholders = ", ".join(f"${i}" for i in range(2, 2 + len(_ACTIVE_PO_STATUSES)))
        sql = f"SELECT COUNT(*) FROM purchase_orders WHERE brand_id = $1 AND status IN ({placeholders})"
        val = await self._conn.fetchval(sql, brand_id, *_ACTIVE_PO_STATUSES)
        return val or 0

    async def is_vendor_assigned_to_brand(self, brand_id: str, vendor_id: str) -> bool:
        row = await self._conn.fetchrow(
            "SELECT 1 FROM brand_vendors WHERE brand_id = $1 AND vendor_id = $2",
            brand_id, vendor_id,
        )
        return row is not None

    async def count_active_pos_for_brand_vendor(self, brand_id: str, vendor_id: str) -> int:
        # Counts non-terminal POs that use this specific brand+vendor pair
        placeholders = ", ".join(f"${i}" for i in range(3, 3 + len(_ACTIVE_PO_STATUSES)))
        sql = (
            f"SELECT COUNT(*) FROM purchase_orders "
            f"WHERE brand_id = $1 AND vendor_id = $2 AND status IN ({placeholders})"
        )
        val = await self._conn.fetchval(sql, brand_id, vendor_id, *_ACTIVE_PO_STATUSES)
        return val or 0


def _reconstruct(row: asyncpg.Record) -> Brand:
    return Brand(
        id=row["id"],
        name=row["name"],
        legal_name=row["legal_name"],
        address=row["address"] or "",
        country=row["country"],
        tax_id=row["tax_id"] or "",
        status=BrandStatus(row["status"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )
