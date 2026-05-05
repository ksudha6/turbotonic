from __future__ import annotations

from datetime import UTC, datetime

import asyncpg

from src.domain.product import Product


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class ProductRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, product: Product) -> None:
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM products WHERE id = $1", product.id
        )
        exists = (count or 0) > 0

        if not exists:
            await self._conn.execute(
                """
                INSERT INTO products (id, vendor_id, part_number, description,
                    manufacturing_address, manufacturer_name, manufacturer_address,
                    manufacturer_country, manufacturer_party_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                product.id,
                product.vendor_id,
                product.part_number,
                product.description,
                product.manufacturing_address,
                product.manufacturer_name,
                product.manufacturer_address,
                product.manufacturer_country,
                product.manufacturer_party_id,
                _iso(product.created_at),
                _iso(product.updated_at),
            )
        else:
            await self._conn.execute(
                """
                UPDATE products SET vendor_id = $1, part_number = $2, description = $3,
                    manufacturing_address = $4, manufacturer_name = $5,
                    manufacturer_address = $6, manufacturer_country = $7,
                    manufacturer_party_id = $8, updated_at = $9
                WHERE id = $10
                """,
                product.vendor_id,
                product.part_number,
                product.description,
                product.manufacturing_address,
                product.manufacturer_name,
                product.manufacturer_address,
                product.manufacturer_country,
                product.manufacturer_party_id,
                _iso(product.updated_at),
                product.id,
            )

    async def get_by_id(self, product_id: str) -> Product | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM products WHERE id = $1", product_id
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def list_products(self, vendor_id: str | None = None) -> list[Product]:
        where_clauses: list[str] = []
        params: list[str] = []
        counter = 1
        if vendor_id is not None:
            where_clauses.append(f"vendor_id = ${counter}")
            params.append(vendor_id)
            counter += 1
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        query = f"SELECT * FROM products {where_sql} ORDER BY part_number"
        rows = await self._conn.fetch(query, *params)
        return [_reconstruct(row) for row in rows]

    async def get_by_vendor_and_part_number(
        self, vendor_id: str, part_number: str
    ) -> Product | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM products WHERE vendor_id = $1 AND part_number = $2",
            vendor_id, part_number,
        )
        if row is None:
            return None
        return _reconstruct(row)


def _reconstruct(row: asyncpg.Record) -> Product:
    keys = row.keys()
    return Product(
        id=row["id"],
        vendor_id=row["vendor_id"],
        part_number=row["part_number"],
        description=row["description"],
        manufacturing_address=row["manufacturing_address"] or "",
        manufacturer_name=row["manufacturer_name"] if "manufacturer_name" in keys else "",
        manufacturer_address=row["manufacturer_address"] if "manufacturer_address" in keys else "",
        manufacturer_country=row["manufacturer_country"] if "manufacturer_country" in keys else "",
        manufacturer_party_id=row["manufacturer_party_id"] if "manufacturer_party_id" in keys else None,
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )
