from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import asyncpg

from src.domain.shipment import Shipment, ShipmentLineItem, ShipmentStatus
from src.domain.shipment_document_requirement import (
    DocumentRequirementStatus,
    ShipmentDocumentRequirement,
)


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
                # Iter 044: update weight/dimension fields on existing line items
                for item in shipment.line_items:
                    await self._conn.execute(
                        """
                        UPDATE shipment_line_items SET
                            net_weight = $1,
                            gross_weight = $2,
                            package_count = $3,
                            dimensions = $4,
                            country_of_origin = $5
                        WHERE shipment_id = $6 AND part_number = $7
                        """,
                        str(item.net_weight) if item.net_weight is not None else None,
                        str(item.gross_weight) if item.gross_weight is not None else None,
                        item.package_count,
                        item.dimensions,
                        item.country_of_origin,
                        shipment.id,
                        item.part_number,
                    )

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

    async def save_requirement(self, req: ShipmentDocumentRequirement) -> None:
        count = await self._conn.fetchval(
            "SELECT COUNT(*) FROM shipment_document_requirements WHERE id = $1", req.id
        )
        exists = (count or 0) > 0

        if not exists:
            await self._conn.execute(
                """
                INSERT INTO shipment_document_requirements (
                    id, shipment_id, document_type, is_auto_generated,
                    status, document_id, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                req.id,
                req.shipment_id,
                req.document_type,
                1 if req.is_auto_generated else 0,
                req.status.value,
                req.document_id,
                _iso(req.created_at),
                _iso(req.updated_at),
            )
        else:
            await self._conn.execute(
                """
                UPDATE shipment_document_requirements SET
                    status = $1,
                    document_id = $2,
                    updated_at = $3
                WHERE id = $4
                """,
                req.status.value,
                req.document_id,
                _iso(req.updated_at),
                req.id,
            )

    async def save_requirements_batch(
        self, requirements: list[ShipmentDocumentRequirement]
    ) -> None:
        # Bulk insert on status transition; each requirement is new, no update path needed
        async with self._conn.transaction():
            for req in requirements:
                await self._conn.execute(
                    """
                    INSERT INTO shipment_document_requirements (
                        id, shipment_id, document_type, is_auto_generated,
                        status, document_id, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    req.id,
                    req.shipment_id,
                    req.document_type,
                    1 if req.is_auto_generated else 0,
                    req.status.value,
                    req.document_id,
                    _iso(req.created_at),
                    _iso(req.updated_at),
                )

    async def list_requirements(
        self, shipment_id: str
    ) -> list[ShipmentDocumentRequirement]:
        rows = await self._conn.fetch(
            """
            SELECT * FROM shipment_document_requirements
            WHERE shipment_id = $1
            ORDER BY created_at
            """,
            shipment_id,
        )
        return [_reconstruct_requirement(row) for row in rows]

    async def get_requirement(
        self, requirement_id: str
    ) -> ShipmentDocumentRequirement | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM shipment_document_requirements WHERE id = $1",
            requirement_id,
        )
        if row is None:
            return None
        return _reconstruct_requirement(row)

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


def _reconstruct_requirement(row: asyncpg.Record) -> ShipmentDocumentRequirement:
    return ShipmentDocumentRequirement(
        id=row["id"],
        shipment_id=row["shipment_id"],
        document_type=row["document_type"],
        is_auto_generated=bool(row["is_auto_generated"]),
        status=DocumentRequirementStatus(row["status"]),
        document_id=row["document_id"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


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
            net_weight=_decimal_or_none(r["net_weight"]) if "net_weight" in r.keys() else None,
            gross_weight=_decimal_or_none(r["gross_weight"]) if "gross_weight" in r.keys() else None,
            package_count=r["package_count"] if "package_count" in r.keys() else None,
            dimensions=r["dimensions"] if "dimensions" in r.keys() else None,
            country_of_origin=r["country_of_origin"] if "country_of_origin" in r.keys() else None,
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
