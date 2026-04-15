from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import require_auth
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.user import User
from src.domain.milestone import MILESTONE_ORDER, ProductionMilestone
from src.domain.reference_data import RATE_TO_USD
from src.invoice_repository import InvoiceRepository
from src.milestone_repository import MilestoneRepository
from src.repository import PurchaseOrderRepository
from src.vendor_repository import VendorRepository

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


async def get_repo() -> AsyncIterator[PurchaseOrderRepository]:
    async with get_db() as conn:
        yield PurchaseOrderRepository(conn)


async def get_vendor_repo() -> AsyncIterator[VendorRepository]:
    async with get_db() as conn:
        yield VendorRepository(conn)


async def get_invoice_repo() -> AsyncIterator[InvoiceRepository]:
    async with get_db() as conn:
        yield InvoiceRepository(conn)


async def get_milestone_repo() -> AsyncIterator[MilestoneRepository]:
    async with get_db() as conn:
        yield MilestoneRepository(conn)


async def get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


RepoDep = Annotated[PurchaseOrderRepository, Depends(get_repo)]
VendorRepoDep = Annotated[VendorRepository, Depends(get_vendor_repo)]
InvoiceRepoDep = Annotated[InvoiceRepository, Depends(get_invoice_repo)]
MilestoneRepoDep = Annotated[MilestoneRepository, Depends(get_milestone_repo)]
ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo)]


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


class ProductionStageSummary(BaseModel):
    milestone: str
    count: int


class OverduePO(BaseModel):
    id: str
    po_number: str
    vendor_name: str
    milestone: str
    days_since_update: int


# Days before a PO at a given milestone is considered overdue.
# SHIPPED is never overdue (terminal production milestone).
_OVERDUE_THRESHOLDS: dict[str, int] = {
    ProductionMilestone.RAW_MATERIALS.value: 7,
    ProductionMilestone.PRODUCTION_STARTED.value: 7,
    ProductionMilestone.QC_PASSED.value: 3,
    ProductionMilestone.READY_TO_SHIP.value: 3,
}


class DashboardResponse(BaseModel):
    po_summary: list[POStatusSummary]
    vendor_summary: VendorSummary
    recent_pos: list[RecentPO]
    invoice_summary: list[InvoiceStatusSummary]
    production_summary: list[ProductionStageSummary]
    overdue_pos: list[OverduePO]


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    invoice_repo: InvoiceRepoDep,
    milestone_repo: MilestoneRepoDep,
    activity_repo: ActivityRepoDep,
    _user: User = require_auth,
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
    invoice_rows = await invoice_repo._conn.fetch(
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
    )

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

    # Production summary: count of ACCEPTED PROCUREMENT POs at each milestone stage.
    prod_rows = await milestone_repo._conn.fetch(
        """
        SELECT lm.milestone, COUNT(*) AS cnt
        FROM purchase_orders p
        INNER JOIN (
            SELECT mu.po_id, mu.milestone
            FROM milestone_updates mu
            INNER JOIN (
                SELECT po_id, MAX(posted_at) AS max_posted_at
                FROM milestone_updates
                GROUP BY po_id
            ) latest ON mu.po_id = latest.po_id AND mu.posted_at = latest.max_posted_at
        ) lm ON lm.po_id = p.id
        WHERE p.status = 'ACCEPTED' AND p.po_type = 'PROCUREMENT'
        GROUP BY lm.milestone
        """
    )

    prod_counts: dict[str, int] = {row["milestone"]: row["cnt"] for row in prod_rows}
    # Return summary in MILESTONE_ORDER sequence, omitting stages with zero POs.
    production_summary = [
        ProductionStageSummary(milestone=m.value, count=prod_counts[m.value])
        for m in MILESTONE_ORDER
        if m.value in prod_counts
    ]

    # Overdue POs: ACCEPTED PROCUREMENT POs whose latest milestone has been stuck
    # longer than the per-milestone threshold. SHIPPED is never overdue.
    now_utc = datetime.now(UTC)
    overdue_rows = await milestone_repo._conn.fetch(
        """
        SELECT p.id, p.po_number, p.vendor_id, lm.milestone, lm.max_posted_at
        FROM purchase_orders p
        INNER JOIN (
            SELECT mu.po_id, mu.milestone, mu.posted_at AS max_posted_at
            FROM milestone_updates mu
            INNER JOIN (
                SELECT po_id, MAX(posted_at) AS max_posted_at
                FROM milestone_updates
                GROUP BY po_id
            ) latest ON mu.po_id = latest.po_id AND mu.posted_at = latest.max_posted_at
        ) lm ON lm.po_id = p.id
        WHERE p.status = 'ACCEPTED' AND p.po_type = 'PROCUREMENT'
        """
    )

    overdue_pos: list[OverduePO] = []
    for row in overdue_rows:
        milestone_val: str = row["milestone"]
        threshold = _OVERDUE_THRESHOLDS.get(milestone_val)
        if threshold is None:
            # SHIPPED — never overdue
            continue
        posted_at_raw: str = row["max_posted_at"]
        posted_at = datetime.fromisoformat(posted_at_raw)
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=UTC)
        days_since = (now_utc - posted_at).days
        if days_since >= threshold:
            overdue_pos.append(
                OverduePO(
                    id=row["id"],
                    po_number=row["po_number"],
                    vendor_name=vendor_map.get(row["vendor_id"], ""),
                    milestone=milestone_val,
                    days_since_update=days_since,
                )
            )

    for overdue in overdue_pos:
        if not await activity_repo.has_delayed_entry(overdue.id, overdue.milestone):
            await activity_repo.append(
                EntityType.PO,
                overdue.id,
                ActivityEvent.MILESTONE_OVERDUE,
                detail=f"{overdue.milestone} overdue by {overdue.days_since_update} days",
            )

    return DashboardResponse(
        po_summary=po_summary,
        vendor_summary=vendor_summary,
        recent_pos=recent_pos,
        invoice_summary=invoice_summary,
        production_summary=production_summary,
        overdue_pos=overdue_pos,
    )
