from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from src.domain.packaging import PackagingSpec, PackagingSpecStatus


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class PackagingSpecRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, spec: PackagingSpec) -> None:
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM packaging_specs WHERE id = $1", spec.id
        )
        exists = (count or 0) > 0

        if not exists:
            await self._conn.execute(
                """
                INSERT INTO packaging_specs (
                    id, product_id, marketplace, spec_name, description,
                    requirements_text, status, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                spec.id,
                spec.product_id,
                spec.marketplace,
                spec.spec_name,
                spec.description,
                spec.requirements_text,
                spec.status.value,
                _iso(spec.created_at),
                _iso(spec.updated_at),
            )
        else:
            await self._conn.execute(
                """
                UPDATE packaging_specs SET
                    marketplace = $1,
                    spec_name = $2,
                    description = $3,
                    requirements_text = $4,
                    status = $5,
                    updated_at = $6
                WHERE id = $7
                """,
                spec.marketplace,
                spec.spec_name,
                spec.description,
                spec.requirements_text,
                spec.status.value,
                _iso(spec.updated_at),
                spec.id,
            )

    async def get(self, spec_id: str) -> PackagingSpec | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM packaging_specs WHERE id = $1", spec_id
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def list_by_product(self, product_id: str) -> list[PackagingSpec]:
        rows = await self._conn.fetch(
            "SELECT * FROM packaging_specs WHERE product_id = $1 ORDER BY marketplace, spec_name",
            product_id,
        )
        return [_reconstruct(row) for row in rows]

    async def list_by_product_and_marketplace(
        self, product_id: str, marketplace: str
    ) -> list[PackagingSpec]:
        rows = await self._conn.fetch(
            "SELECT * FROM packaging_specs WHERE product_id = $1 AND marketplace = $2 ORDER BY spec_name",
            product_id,
            marketplace,
        )
        return [_reconstruct(row) for row in rows]

    async def get_by_unique_key(
        self, product_id: str, marketplace: str, spec_name: str
    ) -> PackagingSpec | None:
        row = await self._conn.fetchrow(
            """
            SELECT * FROM packaging_specs
            WHERE product_id = $1 AND marketplace = $2 AND spec_name = $3
            """,
            product_id,
            marketplace,
            spec_name,
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def delete(self, spec_id: str) -> None:
        await self._conn.execute(
            "DELETE FROM packaging_specs WHERE id = $1", spec_id
        )


def _reconstruct(row: asyncpg.Record) -> PackagingSpec:
    return PackagingSpec(
        id=row["id"],
        product_id=row["product_id"],
        marketplace=row["marketplace"],
        spec_name=row["spec_name"],
        description=row["description"] or "",
        requirements_text=row["requirements_text"] or "",
        status=PackagingSpecStatus(row["status"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )
