from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import asyncpg

from src.domain.shipment import Shipment, ShipmentLineItem, ShipmentStatus


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class ShipmentRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def save(self, shipment: Shipment) -> None:
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM shipments WHERE id = $1", shipment.id
        )
        exists = (count or 0) > 0

        async with self._conn.transaction():
            if not exists:
                await self._conn.execute(
                    """
                    INSERT INTO shipments (
                        id, po_id, shipment_number, marketplace, status, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    shipment.id,
                    shipment.po_id,
                    shipment.shipment_number,
                    shipment.marketplace,
                    shipment.status.value,
                    _iso(shipment.created_at),
                    _iso(shipment.updated_at),
                )
                for sort_order, item in enumerate(shipment.line_items):
                    await self._conn.execute(
                        """
                        INSERT INTO shipment_line_items (
                            id, shipment_id, part_number, product_id,
                            description, quantity, uom, sort_order
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        str(uuid4()),
                        shipment.id,
                        item.part_number,
                        item.product_id,
                        item.description,
                        item.quantity,
                        item.uom,
                        sort_order,
                    )
            else:
                await self._conn.execute(
                    """
                    UPDATE shipments SET
                        status = $1,
                        updated_at = $2
                    WHERE id = $3
                    """,
                    shipment.status.value,
                    _iso(shipment.updated_at),
                    shipment.id,
                )
                # Line items are immutable after creation; no update needed

    async def get(self, shipment_id: str) -> Shipment | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM shipments WHERE id = $1", shipment_id
        )
        if row is None:
            return None
        item_rows = await self._conn.fetch(
            "SELECT * FROM shipment_line_items WHERE shipment_id = $1 ORDER BY sort_order",
            shipment_id,
        )
        return _reconstruct(row, item_rows)

    async def list_by_po(self, po_id: str) -> list[Shipment]:
        rows = await self._conn.fetch(
            "SELECT * FROM shipments WHERE po_id = $1 ORDER BY created_at",
            po_id,
        )
        result: list[Shipment] = []
        for row in rows:
            item_rows = await self._conn.fetch(
                "SELECT * FROM shipment_line_items WHERE shipment_id = $1 ORDER BY sort_order",
                row["id"],
            )
            result.append(_reconstruct(row, item_rows))
        return result

    async def list_all(self) -> list[Shipment]:
        rows = await self._conn.fetch(
            "SELECT * FROM shipments ORDER BY created_at DESC"
        )
        result: list[Shipment] = []
        for row in rows:
            item_rows = await self._conn.fetch(
                "SELECT * FROM shipment_line_items WHERE shipment_id = $1 ORDER BY sort_order",
                row["id"],
            )
            result.append(_reconstruct(row, item_rows))
        return result

    async def get_line_item_rows(self, shipment_id: str) -> list[dict[str, object]]:
        rows = await self._conn.fetch(
            "SELECT * FROM shipment_line_items WHERE shipment_id = $1 ORDER BY sort_order",
            shipment_id,
        )
        return [dict(r) for r in rows]

    async def get_shipped_quantities(self, po_id: str) -> dict[str, int]:
        """Cumulative shipped quantity per part_number across all shipments for a PO."""
        rows = await self._conn.fetch(
            """
            SELECT sli.part_number, SUM(sli.quantity) AS total
            FROM shipment_line_items sli
            JOIN shipments s ON s.id = sli.shipment_id
            WHERE s.po_id = $1
            GROUP BY sli.part_number
            """,
            po_id,
        )
        return {row["part_number"]: int(row["total"]) for row in rows}


def _reconstruct(
    row: asyncpg.Record,
    item_rows: list[asyncpg.Record],
) -> Shipment:
    line_items = [
        ShipmentLineItem(
            part_number=r["part_number"],
            product_id=r["product_id"],
            description=r["description"] or "",
            quantity=r["quantity"],
            uom=r["uom"],
        )
        for r in item_rows
    ]
    return Shipment(
        id=row["id"],
        po_id=row["po_id"],
        shipment_number=row["shipment_number"],
        marketplace=row["marketplace"],
        status=ShipmentStatus(row["status"]),
        line_items=line_items,
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )
