from __future__ import annotations

from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import asyncpg

from src.domain.purchase_order import (
    LineEditHistoryEntry,
    LineItem,
    LineItemStatus,
    POStatus,
    POType,
    PurchaseOrder,
    RejectionRecord,
)
from src.domain.user import UserRole


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
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def next_po_number(self) -> str:
        today = datetime.now(UTC).strftime("%Y%m%d")
        count: int = await self._conn.fetchval(
            "SELECT COUNT(*) FROM purchase_orders WHERE po_number LIKE $1",
            f"PO-{today}-%",
        )
        return f"PO-{today}-{(count or 0) + 1:04d}"

    async def save(self, po: PurchaseOrder) -> None:
        # Determine whether the PO already exists in the database.
        exists_count: int = await self._conn.fetchval(
            "SELECT COUNT(*) FROM purchase_orders WHERE id = $1", po.id
        )
        exists: bool = (exists_count or 0) > 0

        async with self._conn.transaction():
            last_actor = po.last_actor_role.value if po.last_actor_role is not None else None
            advance_paid_iso = _iso(po.advance_paid_at) if po.advance_paid_at is not None else None
            if not exists:
                await self._conn.execute(
                    """
                    INSERT INTO purchase_orders (
                        id, po_number, status, vendor_id, po_type, buyer_name, buyer_country,
                        ship_to_address, payment_terms, currency,
                        issued_date, required_delivery_date,
                        terms_and_conditions, incoterm, port_of_loading,
                        port_of_discharge, country_of_origin, country_of_destination,
                        marketplace, created_at, updated_at,
                        round_count, last_actor_role, advance_paid_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24)
                    """,
                    po.id,
                    po.po_number,
                    po.status.value,
                    po.vendor_id,
                    po.po_type.value,
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
                    po.marketplace,
                    _iso(po.created_at),
                    _iso(po.updated_at),
                    po.round_count,
                    last_actor,
                    advance_paid_iso,
                )

                for sort_order, item in enumerate(po.line_items):
                    await self._conn.execute(
                        """
                        INSERT INTO line_items (
                            id, po_id, part_number, description, quantity,
                            uom, unit_price, hs_code, country_of_origin, product_id,
                            sort_order, status, required_delivery_date
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        """,
                        str(uuid4()),
                        po.id,
                        item.part_number,
                        item.description,
                        item.quantity,
                        item.uom,
                        str(item.unit_price),
                        item.hs_code,
                        item.country_of_origin,
                        item.product_id,
                        sort_order,
                        item.status.value,
                        _iso(item.required_delivery_date) if item.required_delivery_date else None,
                    )

                for record in po.rejection_history:
                    await self._conn.execute(
                        """
                        INSERT INTO rejection_history (id, po_id, comment, rejected_at)
                        VALUES ($1, $2, $3, $4)
                        """,
                        str(uuid4()), po.id, record.comment, _iso(record.rejected_at),
                    )

                for entry in po.line_edit_history:
                    await self._conn.execute(
                        """
                        INSERT INTO line_edit_history (
                            id, po_id, line_item_id, part_number, round,
                            actor_role, field, old_value, new_value, edited_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        """,
                        str(uuid4()),
                        po.id,
                        None,
                        entry.part_number,
                        entry.round,
                        entry.actor_role.value,
                        entry.field,
                        entry.old_value,
                        entry.new_value,
                        _iso(entry.edited_at),
                    )

            else:
                await self._conn.execute(
                    """
                    UPDATE purchase_orders SET
                        po_number = $1, status = $2, vendor_id = $3, po_type = $4,
                        buyer_name = $5, buyer_country = $6,
                        ship_to_address = $7, payment_terms = $8, currency = $9,
                        issued_date = $10, required_delivery_date = $11,
                        terms_and_conditions = $12, incoterm = $13,
                        port_of_loading = $14, port_of_discharge = $15,
                        country_of_origin = $16, country_of_destination = $17,
                        marketplace = $18, updated_at = $19,
                        round_count = $20, last_actor_role = $21,
                        advance_paid_at = $22
                    WHERE id = $23
                    """,
                    po.po_number,
                    po.status.value,
                    po.vendor_id,
                    po.po_type.value,
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
                    po.marketplace,
                    _iso(po.updated_at),
                    po.round_count,
                    last_actor,
                    advance_paid_iso,
                    po.id,
                )

                # Replace all line items; sort_order is authoritative.
                await self._conn.execute(
                    "DELETE FROM line_items WHERE po_id = $1", po.id
                )
                for sort_order, item in enumerate(po.line_items):
                    await self._conn.execute(
                        """
                        INSERT INTO line_items (
                            id, po_id, part_number, description, quantity,
                            uom, unit_price, hs_code, country_of_origin, product_id,
                            sort_order, status, required_delivery_date
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        """,
                        str(uuid4()),
                        po.id,
                        item.part_number,
                        item.description,
                        item.quantity,
                        item.uom,
                        str(item.unit_price),
                        item.hs_code,
                        item.country_of_origin,
                        item.product_id,
                        sort_order,
                        item.status.value,
                        _iso(item.required_delivery_date) if item.required_delivery_date else None,
                    )

                # Append only new rejection records by comparing persisted count to
                # current list length; rejection_history is append-only by domain rule.
                persisted_count: int = await self._conn.fetchval(
                    "SELECT COUNT(*) FROM rejection_history WHERE po_id = $1", po.id
                )

                for record in po.rejection_history[(persisted_count or 0):]:
                    await self._conn.execute(
                        """
                        INSERT INTO rejection_history (id, po_id, comment, rejected_at)
                        VALUES ($1, $2, $3, $4)
                        """,
                        str(uuid4()), po.id, record.comment, _iso(record.rejected_at),
                    )

                # line_edit_history is append-only; persist only the newly added entries.
                persisted_edits: int = await self._conn.fetchval(
                    "SELECT COUNT(*) FROM line_edit_history WHERE po_id = $1", po.id
                )
                for entry in po.line_edit_history[(persisted_edits or 0):]:
                    await self._conn.execute(
                        """
                        INSERT INTO line_edit_history (
                            id, po_id, line_item_id, part_number, round,
                            actor_role, field, old_value, new_value, edited_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        """,
                        str(uuid4()),
                        po.id,
                        None,
                        entry.part_number,
                        entry.round,
                        entry.actor_role.value,
                        entry.field,
                        entry.old_value,
                        entry.new_value,
                        _iso(entry.edited_at),
                    )

    async def get(self, po_id: str) -> PurchaseOrder | None:
        po_row = await self._conn.fetchrow(
            "SELECT * FROM purchase_orders WHERE id = $1", po_id
        )

        if po_row is None:
            return None

        item_rows = await self._conn.fetch(
            "SELECT * FROM line_items WHERE po_id = $1 ORDER BY sort_order",
            po_id,
        )

        rejection_rows = await self._conn.fetch(
            "SELECT * FROM rejection_history WHERE po_id = $1 ORDER BY rejected_at",
            po_id,
        )

        edit_rows = await self._conn.fetch(
            "SELECT * FROM line_edit_history WHERE po_id = $1 ORDER BY edited_at, id",
            po_id,
        )

        return _reconstruct(po_row, item_rows, rejection_rows, edit_rows)

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
        milestone: str | None = None,
        marketplace: str | None = None,
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
        param_idx = 1

        if status is not None:
            where_clauses.append(f"p.status = ${param_idx}")
            params.append(status.value)
            param_idx += 1
        if vendor_id is not None:
            where_clauses.append(f"p.vendor_id = ${param_idx}")
            params.append(vendor_id)
            param_idx += 1
        if currency is not None:
            where_clauses.append(f"p.currency = ${param_idx}")
            params.append(currency)
            param_idx += 1
        if milestone is not None:
            where_clauses.append(f"lm.milestone = ${param_idx}")
            params.append(milestone)
            param_idx += 1
        if marketplace is not None:
            where_clauses.append(f"p.marketplace = ${param_idx}")
            params.append(marketplace)
            param_idx += 1
        if search is not None:
            term = f"%{search}%"
            where_clauses.append(
                f"(p.po_number ILIKE ${param_idx} OR v.name ILIKE ${param_idx + 1} OR p.buyer_name ILIKE ${param_idx + 2})"
            )
            params.extend([term, term, term])
            param_idx += 3

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # latest_milestones: one row per PO with the most-recent milestone value.
        latest_milestones_subquery = """
            LEFT JOIN (
                SELECT mu.po_id, mu.milestone
                FROM milestone_updates mu
                INNER JOIN (
                    SELECT po_id, MAX(posted_at) AS max_posted_at
                    FROM milestone_updates
                    GROUP BY po_id
                ) latest ON mu.po_id = latest.po_id AND mu.posted_at = latest.max_posted_at
            ) lm ON lm.po_id = p.id
        """

        base_query = f"""
            SELECT
                p.id,
                p.po_number,
                p.status,
                p.vendor_id,
                p.buyer_name,
                p.buyer_country,
                p.po_type,
                p.marketplace,
                p.round_count,
                v.name AS vendor_name,
                v.country AS vendor_country,
                p.issued_date,
                p.required_delivery_date,
                p.currency,
                (SELECT COALESCE(SUM(quantity * CAST(unit_price AS REAL)), 0)
                 FROM line_items WHERE po_id = p.id) AS total_value,
                lm.milestone AS current_milestone,
                (EXISTS(SELECT 1 FROM line_items
                        WHERE po_id = p.id AND status = 'REMOVED')) AS has_removed_line
            FROM purchase_orders p
            LEFT JOIN vendors v ON v.id = p.vendor_id
            {latest_milestones_subquery}
            {where_sql}
        """

        count_query = f"""
            SELECT COUNT(*) FROM purchase_orders p
            LEFT JOIN vendors v ON v.id = p.vendor_id
            {latest_milestones_subquery}
            {where_sql}
        """

        total: int = await self._conn.fetchval(count_query, *params) or 0

        offset = (page - 1) * page_size
        data_query = f"{base_query} ORDER BY {sort_col} {sort_dir.upper()} LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        data_params = params + [page_size, offset]

        rows = await self._conn.fetch(data_query, *data_params)

        return [dict(row) for row in rows], total

    async def list_pos(self, status: POStatus | None = None) -> list[PurchaseOrder]:
        if status is not None:
            po_rows = await self._conn.fetch(
                "SELECT * FROM purchase_orders WHERE status = $1", status.value
            )
        else:
            po_rows = await self._conn.fetch("SELECT * FROM purchase_orders")

        result: list[PurchaseOrder] = []
        for po_row in po_rows:
            po_id = po_row["id"]

            item_rows = await self._conn.fetch(
                "SELECT * FROM line_items WHERE po_id = $1 ORDER BY sort_order",
                po_id,
            )

            rejection_rows = await self._conn.fetch(
                "SELECT * FROM rejection_history WHERE po_id = $1 ORDER BY rejected_at",
                po_id,
            )

            edit_rows = await self._conn.fetch(
                "SELECT * FROM line_edit_history WHERE po_id = $1 ORDER BY edited_at, id",
                po_id,
            )

            result.append(_reconstruct(po_row, item_rows, rejection_rows, edit_rows))

        return result

    async def po_summary_by_status(self, vendor_id: str | None = None) -> list[dict[str, Any]]:
        if vendor_id is not None:
            rows = await self._conn.fetch(
                """
                SELECT p.status, p.currency, COUNT(DISTINCT p.id) as po_count,
                       COALESCE(SUM(li.quantity * CAST(li.unit_price AS REAL)), 0) as total_value
                FROM purchase_orders p
                LEFT JOIN line_items li ON li.po_id = p.id
                WHERE p.vendor_id = $1
                GROUP BY p.status, p.currency
                """,
                vendor_id,
            )
        else:
            rows = await self._conn.fetch(
                """
                SELECT p.status, p.currency, COUNT(DISTINCT p.id) as po_count,
                       COALESCE(SUM(li.quantity * CAST(li.unit_price AS REAL)), 0) as total_value
                FROM purchase_orders p
                LEFT JOIN line_items li ON li.po_id = p.id
                GROUP BY p.status, p.currency
                """
            )
        return [
            {
                "status": row["status"],
                "currency": row["currency"],
                "po_count": row["po_count"],
                "total_value": row["total_value"],
            }
            for row in rows
        ]

    async def recent_pos(self, limit: int = 10, vendor_id: str | None = None) -> list[PurchaseOrder]:  # noqa: E501
        if vendor_id is not None:
            po_rows = await self._conn.fetch(
                "SELECT * FROM purchase_orders WHERE vendor_id = $1 ORDER BY updated_at DESC LIMIT $2",
                vendor_id,
                limit,
            )
        else:
            po_rows = await self._conn.fetch(
                "SELECT * FROM purchase_orders ORDER BY updated_at DESC LIMIT $1",
                limit,
            )

        result: list[PurchaseOrder] = []
        for po_row in po_rows:
            po_id = po_row["id"]

            item_rows = await self._conn.fetch(
                "SELECT * FROM line_items WHERE po_id = $1 ORDER BY sort_order",
                po_id,
            )

            rejection_rows = await self._conn.fetch(
                "SELECT * FROM rejection_history WHERE po_id = $1 ORDER BY rejected_at",
                po_id,
            )

            edit_rows_recent = await self._conn.fetch(
                "SELECT * FROM line_edit_history WHERE po_id = $1 ORDER BY edited_at, id",
                po_id,
            )

            result.append(_reconstruct(po_row, item_rows, rejection_rows, edit_rows_recent))

        return result


def _reconstruct(
    po_row: asyncpg.Record,
    item_rows: list[asyncpg.Record],
    rejection_rows: list[asyncpg.Record],
    edit_rows: list[asyncpg.Record] | None = None,
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
            product_id=row["product_id"],
            status=LineItemStatus(row["status"]) if row["status"] else LineItemStatus.PENDING,
            required_delivery_date=(
                _parse_dt(row["required_delivery_date"])
                if row.get("required_delivery_date")
                else None
            ),
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

    line_edit_history: list[LineEditHistoryEntry] = []
    if edit_rows is not None:
        for row in edit_rows:
            line_edit_history.append(
                LineEditHistoryEntry(
                    part_number=row["part_number"],
                    round=int(row["round"]),
                    actor_role=UserRole(row["actor_role"]),
                    field=row["field"],
                    old_value=row["old_value"] or "",
                    new_value=row["new_value"] or "",
                    edited_at=_parse_dt(row["edited_at"]),
                )
            )

    last_actor = po_row["last_actor_role"] if po_row.get("last_actor_role") else None

    raw_advance = po_row.get("advance_paid_at")
    advance_paid_at = _parse_dt(raw_advance) if raw_advance else None

    return PurchaseOrder(
        id=po_row["id"],
        po_number=po_row["po_number"],
        status=POStatus(po_row["status"]),
        po_type=POType(po_row["po_type"]),
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
        marketplace=po_row["marketplace"],
        line_items=line_items,
        rejection_history=rejection_history,
        created_at=_parse_dt(po_row["created_at"]),
        updated_at=_parse_dt(po_row["updated_at"]),
        round_count=int(po_row.get("round_count") or 0),
        last_actor_role=UserRole(last_actor) if last_actor else None,
        line_edit_history=line_edit_history,
        advance_paid_at=advance_paid_at,
    )
