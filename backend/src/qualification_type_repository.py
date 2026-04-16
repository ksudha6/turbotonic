from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from src.domain.qualification_type import QualificationType


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class QualificationTypeRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, qt: QualificationType) -> None:
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM qualification_types WHERE id = $1", qt.id
        )
        exists = (count or 0) > 0

        if not exists:
            await self._conn.execute(
                """
                INSERT INTO qualification_types (id, name, description, target_market, applies_to_category, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                qt.id,
                qt.name,
                qt.description,
                qt.target_market,
                qt.applies_to_category,
                _iso(qt.created_at),
            )
        else:
            await self._conn.execute(
                """
                UPDATE qualification_types SET name = $1, description = $2,
                    target_market = $3, applies_to_category = $4
                WHERE id = $5
                """,
                qt.name,
                qt.description,
                qt.target_market,
                qt.applies_to_category,
                qt.id,
            )

    async def get_by_id(self, qt_id: str) -> QualificationType | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM qualification_types WHERE id = $1", qt_id
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def get_by_name(self, name: str) -> QualificationType | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM qualification_types WHERE name = $1", name
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def list_all(self) -> list[QualificationType]:
        rows = await self._conn.fetch(
            "SELECT * FROM qualification_types ORDER BY name"
        )
        return [_reconstruct(row) for row in rows]

    async def delete(self, qt_id: str) -> bool:
        # Check if in use
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM product_qualifications WHERE qualification_type_id = $1",
            qt_id,
        )
        if (count or 0) > 0:
            raise ValueError(f"QualificationType {qt_id} is assigned to products and cannot be deleted")

        result = await self._conn.execute(
            "DELETE FROM qualification_types WHERE id = $1", qt_id
        )
        # asyncpg returns "DELETE N" where N is the number of rows deleted
        deleted = int(result.split()[-1])
        return deleted > 0

    async def list_by_product(self, product_id: str) -> list[QualificationType]:
        rows = await self._conn.fetch(
            """
            SELECT qt.* FROM qualification_types qt
            JOIN product_qualifications pq ON qt.id = pq.qualification_type_id
            WHERE pq.product_id = $1
            ORDER BY qt.name
            """,
            product_id,
        )
        return [_reconstruct(row) for row in rows]

    async def list_by_products(self, product_ids: list[str]) -> dict[str, list[QualificationType]]:
        """Batch fetch qualifications for multiple products. Returns a dict keyed by product_id."""
        if not product_ids:
            return {}
        rows = await self._conn.fetch(
            """
            SELECT pq.product_id, qt.* FROM qualification_types qt
            JOIN product_qualifications pq ON qt.id = pq.qualification_type_id
            WHERE pq.product_id = ANY($1::text[])
            ORDER BY qt.name
            """,
            product_ids,
        )
        result: dict[str, list[QualificationType]] = {pid: [] for pid in product_ids}
        for row in rows:
            pid = row["product_id"]
            # Reconstruct from columns excluding product_id
            qt = QualificationType(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                target_market=row["target_market"],
                applies_to_category=row["applies_to_category"],
                created_at=_parse_dt(row["created_at"]),
            )
            result[pid].append(qt)
        return result

    async def assign_to_product(self, product_id: str, qualification_type_id: str) -> None:
        await self._conn.execute(
            """
            INSERT INTO product_qualifications (product_id, qualification_type_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            product_id,
            qualification_type_id,
        )

    async def remove_from_product(self, product_id: str, qualification_type_id: str) -> None:
        await self._conn.execute(
            """
            DELETE FROM product_qualifications
            WHERE product_id = $1 AND qualification_type_id = $2
            """,
            product_id,
            qualification_type_id,
        )


def _reconstruct(row: asyncpg.Record) -> QualificationType:
    return QualificationType(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        target_market=row["target_market"],
        applies_to_category=row["applies_to_category"],
        created_at=_parse_dt(row["created_at"]),
    )
