from __future__ import annotations

import asyncpg


async def line_has_downstream_artifacts(
    conn: asyncpg.Connection, po_id: str, part_number: str
) -> bool:
    """True when a PO line is referenced by any invoice or shipment line.

    Matching is by (po_id, part_number) because neither invoice_line_items nor
    shipment_line_items carry a foreign-key back to line_items.id; the line
    identity within a PO is the part_number, which is immutable by domain rule.

    The shipment tables are probed via information_schema so early environments
    that predate iter 043 stay compatible. Once the table exists the probe is a
    trivial one-row lookup; we accept that one-extra-query cost per call.
    """
    invoice_hit = await conn.fetchval(
        """
        SELECT 1
        FROM invoice_line_items ili
        JOIN invoices inv ON inv.id = ili.invoice_id
        WHERE inv.po_id = $1 AND ili.part_number = $2
        LIMIT 1
        """,
        po_id,
        part_number,
    )
    if invoice_hit:
        return True

    shipment_table_exists = await conn.fetchval(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'shipment_line_items'
        LIMIT 1
        """
    )
    if not shipment_table_exists:
        return False

    shipment_hit = await conn.fetchval(
        """
        SELECT 1
        FROM shipment_line_items sli
        JOIN shipments s ON s.id = sli.shipment_id
        WHERE s.po_id = $1 AND sli.part_number = $2
        LIMIT 1
        """,
        po_id,
        part_number,
    )
    return bool(shipment_hit)
