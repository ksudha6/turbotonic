from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import asyncpg

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
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def next_invoice_number(self) -> str:
        today = datetime.now(UTC).strftime("%Y%m%d")
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM invoices WHERE invoice_number LIKE $1",
            f"INV-{today}-%",
        )
        return f"INV-{today}-{(count or 0) + 1:04d}"

    async def save(self, invoice: Invoice) -> None:
        # Determine whether the invoice already exists in the database.
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM invoices WHERE id = $1", invoice.id
        )
        exists: bool = (count or 0) > 0

        async with self._conn.transaction():
            if not exists:
                await self._conn.execute(
                    """
                    INSERT INTO invoices (
                        id, invoice_number, po_id, status, payment_terms, currency,
                        dispute_reason, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    invoice.id,
                    invoice.invoice_number,
                    invoice.po_id,
                    invoice.status.value,
                    invoice.payment_terms,
                    invoice.currency,
                    invoice.dispute_reason,
                    _iso(invoice.created_at),
                    _iso(invoice.updated_at),
                )

                for sort_order, item in enumerate(invoice.line_items):
                    await self._conn.execute(
                        """
                        INSERT INTO invoice_line_items (
                            id, invoice_id, part_number, description, quantity,
                            uom, unit_price, sort_order
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        str(uuid4()),
                        invoice.id,
                        item.part_number,
                        item.description,
                        item.quantity,
                        item.uom,
                        str(item.unit_price),
                        sort_order,
                    )

            else:
                await self._conn.execute(
                    """
                    UPDATE invoices SET
                        status = $1, payment_terms = $2, currency = $3,
                        dispute_reason = $4, updated_at = $5
                    WHERE id = $6
                    """,
                    invoice.status.value,
                    invoice.payment_terms,
                    invoice.currency,
                    invoice.dispute_reason,
                    _iso(invoice.updated_at),
                    invoice.id,
                )

                # Replace all line items; sort_order is authoritative.
                await self._conn.execute(
                    "DELETE FROM invoice_line_items WHERE invoice_id = $1", invoice.id
                )
                for sort_order, item in enumerate(invoice.line_items):
                    await self._conn.execute(
                        """
                        INSERT INTO invoice_line_items (
                            id, invoice_id, part_number, description, quantity,
                            uom, unit_price, sort_order
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        str(uuid4()),
                        invoice.id,
                        item.part_number,
                        item.description,
                        item.quantity,
                        item.uom,
                        str(item.unit_price),
                        sort_order,
                    )

    async def get_by_id(self, invoice_id: str) -> Invoice | None:
        inv_row = await self._conn.fetchrow(
            "SELECT * FROM invoices WHERE id = $1", invoice_id
        )

        if inv_row is None:
            return None

        item_rows = await self._conn.fetch(
            "SELECT * FROM invoice_line_items WHERE invoice_id = $1 ORDER BY sort_order",
            invoice_id,
        )

        return _reconstruct(inv_row, item_rows)

    async def invoiced_quantities(self, po_id: str) -> dict[str, int]:
        # Sum quantity per part_number across all non-disputed invoices for this PO.
        rows = await self._conn.fetch(
            """
            SELECT ili.part_number, SUM(ili.quantity) AS total
            FROM invoice_line_items ili
            JOIN invoices i ON i.id = ili.invoice_id
            WHERE i.po_id = $1 AND i.status != 'DISPUTED'
            GROUP BY ili.part_number
            """,
            po_id,
        )

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
        vendor_id: str | None = None,
        brand_ids: list[str] | None = None,
    ) -> tuple[list[asyncpg.Record], int]:
        joins = """
            FROM invoices i
            JOIN purchase_orders po ON po.id = i.po_id
            JOIN vendors v ON v.id = po.vendor_id
        """
        conditions: list[str] = []
        params: list[object] = []
        counter = 1

        if status is not None:
            conditions.append(f"i.status = ${counter}")
            params.append(status)
            counter += 1
        if po_number is not None:
            conditions.append(f"po.po_number LIKE ${counter}")
            params.append(f"%{po_number}%")
            counter += 1
        if vendor_name is not None:
            conditions.append(f"v.name LIKE ${counter}")
            params.append(f"%{vendor_name}%")
            counter += 1
        if invoice_number is not None:
            conditions.append(f"i.invoice_number LIKE ${counter}")
            params.append(f"%{invoice_number}%")
            counter += 1
        if date_from is not None:
            conditions.append(f"i.created_at >= ${counter}")
            params.append(date_from)
            counter += 1
        if date_to is not None:
            conditions.append(f"i.created_at <= ${counter}")
            params.append(f"{date_to}T23:59:59")
            counter += 1
        if vendor_id is not None:
            conditions.append(f"po.vendor_id = ${counter}")
            params.append(vendor_id)
            counter += 1
        if brand_ids is not None and len(brand_ids) > 0:
            # Iter 111: filter invoices to those whose parent PO is in the accessible brands.
            conditions.append(f"po.brand_id = ANY(${counter})")
            params.append(brand_ids)
            counter += 1

        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        count_query = f"SELECT COUNT(*) {joins}{where_clause}"
        total: int = await self._conn.fetchval(count_query, *params) or 0

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
            LIMIT ${counter} OFFSET ${counter + 1}
            """
        )
        rows = await self._conn.fetch(data_query, *params, page_size, offset)

        return rows, total

    async def list_by_po(self, po_id: str) -> list[Invoice]:
        inv_rows = await self._conn.fetch(
            "SELECT * FROM invoices WHERE po_id = $1 ORDER BY created_at",
            po_id,
        )

        result: list[Invoice] = []
        for inv_row in inv_rows:
            invoice_id = inv_row["id"]

            item_rows = await self._conn.fetch(
                "SELECT * FROM invoice_line_items WHERE invoice_id = $1 ORDER BY sort_order",
                invoice_id,
            )

            result.append(_reconstruct(inv_row, item_rows))

        return result


def _reconstruct(
    inv_row: asyncpg.Record,
    item_rows: list[asyncpg.Record],
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
