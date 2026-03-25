from __future__ import annotations

from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import aiosqlite

from src.domain.purchase_order import (
    LineItem,
    POStatus,
    PurchaseOrder,
    RejectionRecord,
)


def _iso(dt: datetime) -> str:
    # Store all datetimes as UTC ISO 8601 strings.
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    # datetime.fromisoformat handles the +00:00 suffix from isoformat().
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class PurchaseOrderRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def next_po_number(self) -> str:
        today = datetime.now(UTC).strftime("%Y%m%d")
        async with self._conn.execute(
            "SELECT COUNT(*) FROM purchase_orders WHERE po_number LIKE ?",
            (f"PO-{today}-%",),
        ) as cursor:
            row = await cursor.fetchone()
            count: int = row[0] if row else 0
        return f"PO-{today}-{count + 1:04d}"

    async def save(self, po: PurchaseOrder) -> None:
        # Determine whether the PO already exists in the database.
        async with self._conn.execute(
            "SELECT COUNT(*) FROM purchase_orders WHERE id = ?", (po.id,)
        ) as cursor:
            row = await cursor.fetchone()
            exists: bool = (row[0] if row else 0) > 0

        async with self._conn.execute("BEGIN"):
            pass

        try:
            if not exists:
                await self._conn.execute(
                    """
                    INSERT INTO purchase_orders (
                        id, po_number, status, vendor_id, buyer_name, buyer_country,
                        ship_to_address, payment_terms, currency,
                        issued_date, required_delivery_date,
                        terms_and_conditions, incoterm, port_of_loading,
                        port_of_discharge, country_of_origin, country_of_destination,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        po.id,
                        po.po_number,
                        po.status.value,
                        po.vendor_id,
                        po.buyer_name,
                        po.buyer_country,
                        po.ship_to_address,
                        po.payment_terms,
                        po.currency,
                        _iso(po.issued_date),
                        _iso(po.required_delivery_date),
                        po.terms_and_conditions,
                        po.incoterm,
                        po.port_of_loading,
                        po.port_of_discharge,
                        po.country_of_origin,
                        po.country_of_destination,
                        _iso(po.created_at),
                        _iso(po.updated_at),
                    ),
                )

                for sort_order, item in enumerate(po.line_items):
                    await self._conn.execute(
                        """
                        INSERT INTO line_items (
                            id, po_id, part_number, description, quantity,
                            uom, unit_price, hs_code, country_of_origin, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid4()),
                            po.id,
                            item.part_number,
                            item.description,
                            item.quantity,
                            item.uom,
                            str(item.unit_price),
                            item.hs_code,
                            item.country_of_origin,
                            sort_order,
                        ),
                    )

                for record in po.rejection_history:
                    await self._conn.execute(
                        """
                        INSERT INTO rejection_history (id, po_id, comment, rejected_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (str(uuid4()), po.id, record.comment, _iso(record.rejected_at)),
                    )

            else:
                await self._conn.execute(
                    """
                    UPDATE purchase_orders SET
                        po_number = ?, status = ?, vendor_id = ?,
                        buyer_name = ?, buyer_country = ?,
                        ship_to_address = ?, payment_terms = ?, currency = ?,
                        issued_date = ?, required_delivery_date = ?,
                        terms_and_conditions = ?, incoterm = ?,
                        port_of_loading = ?, port_of_discharge = ?,
                        country_of_origin = ?, country_of_destination = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        po.po_number,
                        po.status.value,
                        po.vendor_id,
                        po.buyer_name,
                        po.buyer_country,
                        po.ship_to_address,
                        po.payment_terms,
                        po.currency,
                        _iso(po.issued_date),
                        _iso(po.required_delivery_date),
                        po.terms_and_conditions,
                        po.incoterm,
                        po.port_of_loading,
                        po.port_of_discharge,
                        po.country_of_origin,
                        po.country_of_destination,
                        _iso(po.updated_at),
                        po.id,
                    ),
                )

                # Replace all line items; sort_order is authoritative.
                await self._conn.execute(
                    "DELETE FROM line_items WHERE po_id = ?", (po.id,)
                )
                for sort_order, item in enumerate(po.line_items):
                    await self._conn.execute(
                        """
                        INSERT INTO line_items (
                            id, po_id, part_number, description, quantity,
                            uom, unit_price, hs_code, country_of_origin, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid4()),
                            po.id,
                            item.part_number,
                            item.description,
                            item.quantity,
                            item.uom,
                            str(item.unit_price),
                            item.hs_code,
                            item.country_of_origin,
                            sort_order,
                        ),
                    )

                # Append only new rejection records by comparing persisted count to
                # current list length; rejection_history is append-only by domain rule.
                async with self._conn.execute(
                    "SELECT COUNT(*) FROM rejection_history WHERE po_id = ?", (po.id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    persisted_count: int = row[0] if row else 0

                for record in po.rejection_history[persisted_count:]:
                    await self._conn.execute(
                        """
                        INSERT INTO rejection_history (id, po_id, comment, rejected_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (str(uuid4()), po.id, record.comment, _iso(record.rejected_at)),
                    )

            await self._conn.commit()

        except Exception:
            await self._conn.rollback()
            raise

    async def get(self, po_id: str) -> PurchaseOrder | None:
        self._conn.row_factory = aiosqlite.Row

        async with self._conn.execute(
            "SELECT * FROM purchase_orders WHERE id = ?", (po_id,)
        ) as cursor:
            po_row = await cursor.fetchone()

        if po_row is None:
            return None

        async with self._conn.execute(
            "SELECT * FROM line_items WHERE po_id = ? ORDER BY sort_order",
            (po_id,),
        ) as cursor:
            item_rows = await cursor.fetchall()

        async with self._conn.execute(
            "SELECT * FROM rejection_history WHERE po_id = ? ORDER BY rejected_at",
            (po_id,),
        ) as cursor:
            rejection_rows = await cursor.fetchall()

        return _reconstruct(po_row, item_rows, rejection_rows)

    _SORT_ALLOWLIST: dict[str, str] = {
        "po_number": "p.po_number",
        "issued_date": "p.issued_date",
        "required_delivery_date": "p.required_delivery_date",
        "total_value": "total_value",
        "created_at": "p.created_at",
    }

    async def list_pos_paginated(
        self,
        *,
        status: POStatus | None = None,
        vendor_id: str | None = None,
        currency: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        if sort_by not in self._SORT_ALLOWLIST:
            raise ValueError(f"Invalid sort_by value: {sort_by!r}")
        if sort_dir not in ("asc", "desc"):
            raise ValueError(f"Invalid sort_dir value: {sort_dir!r}")

        sort_col = self._SORT_ALLOWLIST[sort_by]

        where_clauses: list[str] = []
        params: list[Any] = []

        if status is not None:
            where_clauses.append("p.status = ?")
            params.append(status.value)
        if vendor_id is not None:
            where_clauses.append("p.vendor_id = ?")
            params.append(vendor_id)
        if currency is not None:
            where_clauses.append("p.currency = ?")
            params.append(currency)
        if search is not None:
            term = f"%{search}%"
            where_clauses.append(
                "(LOWER(p.po_number) LIKE LOWER(?) OR LOWER(v.name) LIKE LOWER(?) OR LOWER(p.buyer_name) LIKE LOWER(?))"
            )
            params.extend([term, term, term])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        base_query = f"""
            SELECT
                p.id,
                p.po_number,
                p.status,
                p.vendor_id,
                p.buyer_name,
                p.buyer_country,
                v.name AS vendor_name,
                v.country AS vendor_country,
                p.issued_date,
                p.required_delivery_date,
                p.currency,
                (SELECT COALESCE(SUM(quantity * CAST(unit_price AS REAL)), 0)
                 FROM line_items WHERE po_id = p.id) AS total_value
            FROM purchase_orders p
            LEFT JOIN vendors v ON v.id = p.vendor_id
            {where_sql}
        """

        count_query = f"""
            SELECT COUNT(*) FROM purchase_orders p
            LEFT JOIN vendors v ON v.id = p.vendor_id
            {where_sql}
        """

        self._conn.row_factory = aiosqlite.Row

        async with self._conn.execute(count_query, params) as cursor:
            count_row = await cursor.fetchone()
            total: int = count_row[0] if count_row else 0

        offset = (page - 1) * page_size
        data_query = f"{base_query} ORDER BY {sort_col} {sort_dir.upper()} LIMIT ? OFFSET ?"
        data_params = params + [page_size, offset]

        async with self._conn.execute(data_query, data_params) as cursor:
            rows = await cursor.fetchall()

        return [dict(row) for row in rows], total

    async def list_pos(self, status: POStatus | None = None) -> list[PurchaseOrder]:
        self._conn.row_factory = aiosqlite.Row

        if status is not None:
            async with self._conn.execute(
                "SELECT * FROM purchase_orders WHERE status = ?", (status.value,)
            ) as cursor:
                po_rows = await cursor.fetchall()
        else:
            async with self._conn.execute("SELECT * FROM purchase_orders") as cursor:
                po_rows = await cursor.fetchall()

        result: list[PurchaseOrder] = []
        for po_row in po_rows:
            po_id = po_row["id"]

            async with self._conn.execute(
                "SELECT * FROM line_items WHERE po_id = ? ORDER BY sort_order",
                (po_id,),
            ) as cursor:
                item_rows = await cursor.fetchall()

            async with self._conn.execute(
                "SELECT * FROM rejection_history WHERE po_id = ? ORDER BY rejected_at",
                (po_id,),
            ) as cursor:
                rejection_rows = await cursor.fetchall()

            result.append(_reconstruct(po_row, item_rows, rejection_rows))

        return result

    async def po_summary_by_status(self) -> list[dict[str, Any]]:
        self._conn.row_factory = aiosqlite.Row
        async with self._conn.execute(
            """
            SELECT p.status, p.currency, COUNT(DISTINCT p.id) as po_count,
                   COALESCE(SUM(li.quantity * CAST(li.unit_price AS REAL)), 0) as total_value
            FROM purchase_orders p
            LEFT JOIN line_items li ON li.po_id = p.id
            GROUP BY p.status, p.currency
            """
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            {
                "status": row["status"],
                "currency": row["currency"],
                "po_count": row["po_count"],
                "total_value": row["total_value"],
            }
            for row in rows
        ]

    async def recent_pos(self, limit: int = 10) -> list[PurchaseOrder]:
        self._conn.row_factory = aiosqlite.Row
        async with self._conn.execute(
            "SELECT * FROM purchase_orders ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            po_rows = await cursor.fetchall()

        result: list[PurchaseOrder] = []
        for po_row in po_rows:
            po_id = po_row["id"]

            async with self._conn.execute(
                "SELECT * FROM line_items WHERE po_id = ? ORDER BY sort_order",
                (po_id,),
            ) as cursor:
                item_rows = await cursor.fetchall()

            async with self._conn.execute(
                "SELECT * FROM rejection_history WHERE po_id = ? ORDER BY rejected_at",
                (po_id,),
            ) as cursor:
                rejection_rows = await cursor.fetchall()

            result.append(_reconstruct(po_row, item_rows, rejection_rows))

        return result


def _reconstruct(
    po_row: aiosqlite.Row,
    item_rows: list[aiosqlite.Row],
    rejection_rows: list[aiosqlite.Row],
) -> PurchaseOrder:
    line_items = [
        LineItem(
            part_number=row["part_number"],
            description=row["description"],
            quantity=row["quantity"],
            uom=row["uom"],
            unit_price=Decimal(row["unit_price"]),
            hs_code=row["hs_code"],
            country_of_origin=row["country_of_origin"],
        )
        for row in item_rows
    ]

    rejection_history = [
        RejectionRecord(
            comment=row["comment"],
            rejected_at=_parse_dt(row["rejected_at"]),
        )
        for row in rejection_rows
    ]

    return PurchaseOrder(
        id=po_row["id"],
        po_number=po_row["po_number"],
        status=POStatus(po_row["status"]),
        vendor_id=po_row["vendor_id"],
        buyer_name=po_row["buyer_name"],
        buyer_country=po_row["buyer_country"],
        ship_to_address=po_row["ship_to_address"],
        payment_terms=po_row["payment_terms"],
        currency=po_row["currency"],
        issued_date=_parse_dt(po_row["issued_date"]),
        required_delivery_date=_parse_dt(po_row["required_delivery_date"]),
        terms_and_conditions=po_row["terms_and_conditions"],
        incoterm=po_row["incoterm"],
        port_of_loading=po_row["port_of_loading"],
        port_of_discharge=po_row["port_of_discharge"],
        country_of_origin=po_row["country_of_origin"],
        country_of_destination=po_row["country_of_destination"],
        line_items=line_items,
        rejection_history=rejection_history,
        created_at=_parse_dt(po_row["created_at"]),
        updated_at=_parse_dt(po_row["updated_at"]),
    )
