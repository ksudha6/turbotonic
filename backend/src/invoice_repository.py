from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import aiosqlite

from src.domain.invoice import Invoice, InvoiceLineItem, InvoiceStatus


def _iso(dt: datetime) -> str:
    # Store all datetimes as UTC ISO 8601 strings.
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    # datetime.fromisoformat handles the +00:00 suffix from isoformat().
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class InvoiceRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def next_invoice_number(self) -> str:
        today = datetime.now(UTC).strftime("%Y%m%d")
        async with self._conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE invoice_number LIKE ?",
            (f"INV-{today}-%",),
        ) as cursor:
            row = await cursor.fetchone()
            count: int = row[0] if row else 0
        return f"INV-{today}-{count + 1:04d}"

    async def save(self, invoice: Invoice) -> None:
        # Determine whether the invoice already exists in the database.
        async with self._conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE id = ?", (invoice.id,)
        ) as cursor:
            row = await cursor.fetchone()
            exists: bool = (row[0] if row else 0) > 0

        async with self._conn.execute("BEGIN"):
            pass

        try:
            if not exists:
                await self._conn.execute(
                    """
                    INSERT INTO invoices (
                        id, invoice_number, po_id, status, payment_terms, currency,
                        dispute_reason, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice.id,
                        invoice.invoice_number,
                        invoice.po_id,
                        invoice.status.value,
                        invoice.payment_terms,
                        invoice.currency,
                        invoice.dispute_reason,
                        _iso(invoice.created_at),
                        _iso(invoice.updated_at),
                    ),
                )

                for sort_order, item in enumerate(invoice.line_items):
                    await self._conn.execute(
                        """
                        INSERT INTO invoice_line_items (
                            id, invoice_id, part_number, description, quantity,
                            uom, unit_price, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid4()),
                            invoice.id,
                            item.part_number,
                            item.description,
                            item.quantity,
                            item.uom,
                            str(item.unit_price),
                            sort_order,
                        ),
                    )

            else:
                await self._conn.execute(
                    """
                    UPDATE invoices SET
                        status = ?, payment_terms = ?, currency = ?,
                        dispute_reason = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        invoice.status.value,
                        invoice.payment_terms,
                        invoice.currency,
                        invoice.dispute_reason,
                        _iso(invoice.updated_at),
                        invoice.id,
                    ),
                )

                # Replace all line items; sort_order is authoritative.
                await self._conn.execute(
                    "DELETE FROM invoice_line_items WHERE invoice_id = ?", (invoice.id,)
                )
                for sort_order, item in enumerate(invoice.line_items):
                    await self._conn.execute(
                        """
                        INSERT INTO invoice_line_items (
                            id, invoice_id, part_number, description, quantity,
                            uom, unit_price, sort_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid4()),
                            invoice.id,
                            item.part_number,
                            item.description,
                            item.quantity,
                            item.uom,
                            str(item.unit_price),
                            sort_order,
                        ),
                    )

            await self._conn.commit()

        except Exception:
            await self._conn.rollback()
            raise

    async def get_by_id(self, invoice_id: str) -> Invoice | None:
        self._conn.row_factory = aiosqlite.Row

        async with self._conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ) as cursor:
            inv_row = await cursor.fetchone()

        if inv_row is None:
            return None

        async with self._conn.execute(
            "SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY sort_order",
            (invoice_id,),
        ) as cursor:
            item_rows = await cursor.fetchall()

        return _reconstruct(inv_row, item_rows)

    async def invoiced_quantities(self, po_id: str) -> dict[str, int]:
        # Sum quantity per part_number across all non-disputed invoices for this PO.
        async with self._conn.execute(
            """
            SELECT ili.part_number, SUM(ili.quantity) AS total
            FROM invoice_line_items ili
            JOIN invoices i ON i.id = ili.invoice_id
            WHERE i.po_id = ? AND i.status != 'DISPUTED'
            GROUP BY ili.part_number
            """,
            (po_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        return {row[0]: row[1] for row in rows}

    async def list_all(
        self,
        status: str | None = None,
        po_number: str | None = None,
        vendor_name: str | None = None,
        invoice_number: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[aiosqlite.Row], int]:
        self._conn.row_factory = aiosqlite.Row

        joins = """
            FROM invoices i
            JOIN purchase_orders po ON po.id = i.po_id
            JOIN vendors v ON v.id = po.vendor_id
        """
        conditions: list[str] = []
        params: list[str] = []

        if status is not None:
            conditions.append("i.status = ?")
            params.append(status)
        if po_number is not None:
            conditions.append("po.po_number LIKE ?")
            params.append(f"%{po_number}%")
        if vendor_name is not None:
            conditions.append("v.name LIKE ?")
            params.append(f"%{vendor_name}%")
        if invoice_number is not None:
            conditions.append("i.invoice_number LIKE ?")
            params.append(f"%{invoice_number}%")
        if date_from is not None:
            conditions.append("i.created_at >= ?")
            params.append(date_from)
        if date_to is not None:
            conditions.append("i.created_at <= ?")
            params.append(f"{date_to}T23:59:59")

        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        count_query = f"SELECT COUNT(*) {joins}{where_clause}"
        async with self._conn.execute(count_query, params) as cursor:
            count_row = await cursor.fetchone()
            total: int = count_row[0] if count_row else 0

        offset = (page - 1) * page_size
        data_query = (
            f"""
            SELECT
                i.id,
                i.invoice_number,
                i.status,
                i.po_id,
                po.po_number,
                v.name AS vendor_name,
                (
                    SELECT SUM(CAST(quantity AS REAL) * CAST(unit_price AS REAL))
                    FROM invoice_line_items
                    WHERE invoice_id = i.id
                ) AS subtotal,
                i.created_at
            {joins}{where_clause}
            ORDER BY i.created_at DESC
            LIMIT ? OFFSET ?
            """
        )
        async with self._conn.execute(data_query, [*params, page_size, offset]) as cursor:
            rows = await cursor.fetchall()

        return rows, total

    async def list_by_po(self, po_id: str) -> list[Invoice]:
        self._conn.row_factory = aiosqlite.Row

        async with self._conn.execute(
            "SELECT * FROM invoices WHERE po_id = ? ORDER BY created_at",
            (po_id,),
        ) as cursor:
            inv_rows = await cursor.fetchall()

        result: list[Invoice] = []
        for inv_row in inv_rows:
            invoice_id = inv_row["id"]

            async with self._conn.execute(
                "SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY sort_order",
                (invoice_id,),
            ) as cursor:
                item_rows = await cursor.fetchall()

            result.append(_reconstruct(inv_row, item_rows))

        return result


def _reconstruct(
    inv_row: aiosqlite.Row,
    item_rows: list[aiosqlite.Row],
) -> Invoice:
    line_items = [
        InvoiceLineItem(
            part_number=row["part_number"],
            description=row["description"] or "",
            quantity=row["quantity"],
            uom=row["uom"],
            unit_price=Decimal(row["unit_price"]),
        )
        for row in item_rows
    ]

    return Invoice(
        id=inv_row["id"],
        invoice_number=inv_row["invoice_number"],
        po_id=inv_row["po_id"],
        status=InvoiceStatus(inv_row["status"]),
        payment_terms=inv_row["payment_terms"],
        currency=inv_row["currency"],
        line_items=line_items,
        dispute_reason=inv_row["dispute_reason"],
        created_at=_parse_dt(inv_row["created_at"]),
        updated_at=_parse_dt(inv_row["updated_at"]),
    )
