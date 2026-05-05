from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import asyncpg

from src.domain.vendor import Vendor, VendorStatus, VendorType


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class VendorRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, vendor: Vendor) -> None:
        # Check if vendor exists
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM vendors WHERE id = $1", vendor.id
        )
        exists = (count or 0) > 0

        if not exists:
            await self._conn.execute(
                """
                INSERT INTO vendors (id, name, country, status, vendor_type, address, account_details, tax_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                vendor.id, vendor.name, vendor.country, vendor.status.value,
                vendor.vendor_type.value, vendor.address, vendor.account_details,
                vendor.tax_id,
                _iso(vendor.created_at), _iso(vendor.updated_at),
            )
        else:
            await self._conn.execute(
                """
                UPDATE vendors SET name = $1, country = $2, status = $3, vendor_type = $4,
                    address = $5, account_details = $6, tax_id = $7, updated_at = $8
                WHERE id = $9
                """,
                vendor.name, vendor.country, vendor.status.value,
                vendor.vendor_type.value, vendor.address, vendor.account_details,
                vendor.tax_id,
                _iso(vendor.updated_at), vendor.id,
            )

    async def get_by_id(self, vendor_id: str) -> Vendor | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM vendors WHERE id = $1", vendor_id
        )
        if row is None:
            return None
        return _reconstruct(row)

    async def list_vendors(self, status: VendorStatus | None = None, *, vendor_type: VendorType | None = None) -> list[Vendor]:
        where_clauses: list[str] = []
        params: list[str] = []
        counter = 1
        if status is not None:
            where_clauses.append(f"status = ${counter}")
            params.append(status.value)
            counter += 1
        if vendor_type is not None:
            where_clauses.append(f"vendor_type = ${counter}")
            params.append(vendor_type.value)
            counter += 1
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        query = f"SELECT * FROM vendors {where_sql}"
        rows = await self._conn.fetch(query, *params)
        return [_reconstruct(row) for row in rows]

    async def vendor_count_by_status(self) -> dict[str, int]:
        rows = await self._conn.fetch(
            "SELECT status, COUNT(*) as cnt FROM vendors GROUP BY status"
        )
        return {row["status"]: row["cnt"] for row in rows}


def _reconstruct(row: asyncpg.Record) -> Vendor:
    keys = row.keys()
    return Vendor(
        id=row["id"],
        name=row["name"],
        country=row["country"],
        status=VendorStatus(row["status"]),
        vendor_type=VendorType(row["vendor_type"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
        address=row["address"] or "",
        account_details=row["account_details"] or "",
        tax_id=row["tax_id"] if "tax_id" in keys else "",
    )
