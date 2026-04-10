from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite

from src.domain.product import Product


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class ProductRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def save(self, product: Product) -> None:
        async with self._conn.execute(
            "SELECT COUNT(*) FROM products WHERE id = ?", (product.id,)
        ) as cursor:
            row = await cursor.fetchone()
            exists = (row[0] if row else 0) > 0

        if not exists:
            await self._conn.execute(
                """
                INSERT INTO products (id, vendor_id, part_number, description,
                    requires_certification, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.id,
                    product.vendor_id,
                    product.part_number,
                    product.description,
                    1 if product.requires_certification else 0,
                    _iso(product.created_at),
                    _iso(product.updated_at),
                ),
            )
        else:
            await self._conn.execute(
                """
                UPDATE products SET vendor_id = ?, part_number = ?, description = ?,
                    requires_certification = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    product.vendor_id,
                    product.part_number,
                    product.description,
                    1 if product.requires_certification else 0,
                    _iso(product.updated_at),
                    product.id,
                ),
            )
        await self._conn.commit()

    async def get_by_id(self, product_id: str) -> Product | None:
        self._conn.row_factory = aiosqlite.Row
        async with self._conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _reconstruct(row)

    async def list_products(self, vendor_id: str | None = None) -> list[Product]:
        self._conn.row_factory = aiosqlite.Row
        where_clauses: list[str] = []
        params: list[str] = []
        if vendor_id is not None:
            where_clauses.append("vendor_id = ?")
            params.append(vendor_id)
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        query = f"SELECT * FROM products {where_sql} ORDER BY part_number"
        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
        return [_reconstruct(row) for row in rows]

    async def get_by_vendor_and_part_number(
        self, vendor_id: str, part_number: str
    ) -> Product | None:
        self._conn.row_factory = aiosqlite.Row
        async with self._conn.execute(
            "SELECT * FROM products WHERE vendor_id = ? AND part_number = ?",
            (vendor_id, part_number),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _reconstruct(row)


def _reconstruct(row: aiosqlite.Row) -> Product:
    return Product(
        id=row["id"],
        vendor_id=row["vendor_id"],
        part_number=row["part_number"],
        description=row["description"],
        requires_certification=bool(row["requires_certification"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )
