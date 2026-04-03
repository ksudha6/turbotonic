from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, AsyncIterator

import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.db import get_db
from src.domain.reference_data import RATE_TO_USD
from src.invoice_repository import InvoiceRepository
from src.repository import PurchaseOrderRepository
from src.schema import init_db
from src.vendor_repository import VendorRepository

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


async def get_repo() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield PurchaseOrderRepository(conn)


async def get_vendor_repo() -> AsyncIterator[VendorRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield VendorRepository(conn)


async def get_invoice_repo() -> AsyncIterator[InvoiceRepository]:
    async with get_db() as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield InvoiceRepository(conn)


RepoDep = Annotated[PurchaseOrderRepository, Depends(get_repo)]
VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo)]
InvoiceRepoDep = Annotated[InvoiceRepository, Depends(get_invoice_repo)]


class POStatusSummary(BaseModel):
    status: str
    count: int
    total_usd: str


class InvoiceStatusSummary(BaseModel):
    status: str
    count: int
    total_usd: str


class VendorSummary(BaseModel):
    active: int
    inactive: int


class RecentPO(BaseModel):
    id: str
    po_number: str
    status: str
    vendor_name: str
    total_value: str
    currency: str
    updated_at: datetime


class DashboardResponse(BaseModel):
    po_summary: list[POStatusSummary]
    vendor_summary: VendorSummary
    recent_pos: list[RecentPO]
    invoice_summary: list[InvoiceStatusSummary]


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    invoice_repo: InvoiceRepoDep,
) -> DashboardResponse:
    # PO summary: aggregate by status, convert to USD
    raw_summary = await repo.po_summary_by_status()
    status_agg: dict[str, dict[str, Any]] = {}
    for row in raw_summary:
        st = row["status"]
        rate = RATE_TO_USD.get(row["currency"], Decimal("1"))
        usd_value = Decimal(str(row["total_value"])) * rate
        if st not in status_agg:
            status_agg[st] = {"count": 0, "total_usd": Decimal("0")}
        status_agg[st]["count"] += row["po_count"]
        status_agg[st]["total_usd"] += usd_value

    po_summary = [
        POStatusSummary(
            status=st,
            count=data["count"],
            total_usd=str(data["total_usd"].quantize(Decimal("0.01"))),
        )
        for st, data in sorted(status_agg.items())
    ]

    # Vendor summary
    vendor_counts = await vendor_repo.vendor_count_by_status()
    vendor_summary = VendorSummary(
        active=vendor_counts.get("ACTIVE", 0),
        inactive=vendor_counts.get("INACTIVE", 0),
    )

    # Recent POs with vendor names
    recent = await repo.recent_pos(10)
    vendors = await vendor_repo.list_vendors()
    vendor_map: dict[str, str] = {v.id: v.name for v in vendors}
    recent_pos = [
        RecentPO(
            id=po.id,
            po_number=po.po_number,
            status=po.status.value,
            vendor_name=vendor_map.get(po.vendor_id, ""),
            total_value=str(po.total_value),
            currency=po.currency,
            updated_at=po.updated_at,
        )
        for po in recent
    ]

    # Invoice summary: aggregate by status and currency, convert to USD
    invoice_repo._conn.row_factory = aiosqlite.Row
    async with invoice_repo._conn.execute(
        """
        SELECT i.status, i.currency, COUNT(*) as count,
               COALESCE(SUM(sub.subtotal), 0) as total
        FROM invoices i
        LEFT JOIN (
            SELECT invoice_id, SUM(CAST(quantity AS REAL) * CAST(unit_price AS REAL)) as subtotal
            FROM invoice_line_items GROUP BY invoice_id
        ) sub ON sub.invoice_id = i.id
        GROUP BY i.status, i.currency
        """
    ) as cursor:
        invoice_rows = await cursor.fetchall()

    inv_agg: dict[str, dict[str, Any]] = {}
    for row in invoice_rows:
        st = row["status"]
        rate = RATE_TO_USD.get(row["currency"], Decimal("1"))
        usd_value = Decimal(str(row["total"])) * rate
        if st not in inv_agg:
            inv_agg[st] = {"count": 0, "total_usd": Decimal("0")}
        inv_agg[st]["count"] += row["count"]
        inv_agg[st]["total_usd"] += usd_value

    invoice_summary = [
        InvoiceStatusSummary(
            status=st,
            count=data["count"],
            total_usd=str(data["total_usd"].quantize(Decimal("0.01"))),
        )
        for st, data in sorted(inv_agg.items())
    ]

    return DashboardResponse(
        po_summary=po_summary,
        vendor_summary=vendor_summary,
        recent_pos=recent_pos,
        invoice_summary=invoice_summary,
    )
