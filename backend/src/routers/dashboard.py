from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.activity_repository import ActivityLogRepository
from src.auth.dependencies import require_auth
from src.domain.user import UserRole
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.user import User
from src.domain.milestone import (
    MILESTONE_ORDER,
    MILESTONE_OVERDUE_THRESHOLDS,
    ProductionMilestone,
)
from src.domain.reference_data import RATE_TO_USD
from src.invoice_repository import InvoiceRepository
from src.milestone_repository import MilestoneRepository
from src.repository import PurchaseOrderRepository
from src.vendor_repository import VendorRepository

# Roles that receive a populated dashboard/summary payload.
_DASHBOARD_FULL_LAYOUT_ROLES = {UserRole.ADMIN, UserRole.SM, UserRole.PROCUREMENT_MANAGER}

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
    user: User = require_auth,
) -> DashboardResponse:
    vendor_id = user.vendor_id if user.role is UserRole.VENDOR else None

    # PO summary: aggregate by status, convert to USD
    raw_summary = await repo.po_summary_by_status(vendor_id=vendor_id)
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
    recent = await repo.recent_pos(10, vendor_id=vendor_id)
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
    if vendor_id is not None:
        invoice_rows = await invoice_repo._conn.fetch(
            """
            SELECT i.status, i.currency, COUNT(*) as count,
                   COALESCE(SUM(sub.subtotal), 0) as total
            FROM invoices i
            JOIN purchase_orders po ON i.po_id = po.id
            LEFT JOIN (
                SELECT invoice_id, SUM(CAST(quantity AS REAL) * CAST(unit_price AS REAL)) as subtotal
                FROM invoice_line_items GROUP BY invoice_id
            ) sub ON sub.invoice_id = i.id
            WHERE po.vendor_id = $1
            GROUP BY i.status, i.currency
            """,
            vendor_id,
        )
    else:
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
    if vendor_id is not None:
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
            WHERE p.status = 'ACCEPTED' AND p.po_type = 'PROCUREMENT' AND p.vendor_id = $1
            GROUP BY lm.milestone
            """,
            vendor_id,
        )
    else:
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
    if vendor_id is not None:
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
            WHERE p.status = 'ACCEPTED' AND p.po_type = 'PROCUREMENT' AND p.vendor_id = $1
            """,
            vendor_id,
        )
    else:
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
        threshold = MILESTONE_OVERDUE_THRESHOLDS.get(milestone_val)
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


# ---------------------------------------------------------------------------
# /summary endpoint
# ---------------------------------------------------------------------------

# Production milestones that count as "in production" (not yet shipped).
_IN_PRODUCTION_MILESTONES = (
    ProductionMilestone.RAW_MATERIALS.value,
    ProductionMilestone.PRODUCTION_STARTED.value,
    ProductionMilestone.QC_PASSED.value,
    ProductionMilestone.READY_FOR_SHIPMENT.value,
)

# Activity events excluded from the dashboard feed. Line-level negotiation deltas, force
# transitions, and convergence are noise at the dashboard level — surfaced on entity detail
# pages instead. Email send failures are an ops concern, not a workflow signal.
_DASHBOARD_EXCLUDED_EVENTS = frozenset({
    ActivityEvent.PO_LINE_MODIFIED.value,
    ActivityEvent.PO_LINE_ACCEPTED.value,
    ActivityEvent.PO_LINE_REMOVED.value,
    ActivityEvent.PO_FORCE_ACCEPTED.value,
    ActivityEvent.PO_FORCE_REMOVED.value,
    ActivityEvent.PO_CONVERGED.value,
    ActivityEvent.EMAIL_SEND_FAILED.value,
})


class DashboardKpis(BaseModel):
    pending_pos: int
    pending_pos_value_usd: str
    awaiting_acceptance: int
    awaiting_acceptance_value_usd: str
    in_production: int
    in_production_value_usd: str
    outstanding_ap_usd: str  # Decimal as string for stable serialization


class AwaitingAcceptanceItem(BaseModel):
    id: str
    po_number: str
    vendor_name: str
    total_value_usd: str
    submitted_at: datetime  # set to PO.updated_at (PENDING is the post-submit state)


class DashboardActivityItem(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    event: str
    detail: str | None
    category: str
    created_at: datetime


class FmKpis(BaseModel):
    ready_batches: int
    shipments_in_flight: int
    pending_invoices: int
    pending_invoices_value_usd: str
    docs_missing: int


class FmReadyBatch(BaseModel):
    po_id: str
    po_number: str
    vendor_name: str
    accepted_qty: int
    shipped_qty: int


class FmPendingInvoiceItem(BaseModel):
    id: str
    invoice_number: str
    vendor_name: str
    vendor_type: str  # 'OPEX' or 'FREIGHT'
    subtotal_usd: str
    submitted_at: datetime


class DashboardSummaryResponse(BaseModel):
    kpis: DashboardKpis
    awaiting_acceptance: list[AwaitingAcceptanceItem]
    activity: list[DashboardActivityItem]
    fm_kpis: FmKpis | None = None
    fm_ready_batches: list[FmReadyBatch] = []
    fm_pending_invoices: list[FmPendingInvoiceItem] = []


_ZERO_KPIS = DashboardKpis(
    pending_pos=0,
    pending_pos_value_usd="0.00",
    awaiting_acceptance=0,
    awaiting_acceptance_value_usd="0.00",
    in_production=0,
    in_production_value_usd="0.00",
    outstanding_ap_usd="0.00",
)

# Shipment statuses that are still "in flight" from FM's perspective.
# Iter 074: BOOKED added — shipment has a carrier but has not been picked up yet.
# SHIPPED is excluded (terminal — out of FM's daily worklist).
_SHIPMENT_IN_FLIGHT_STATUSES = (
    "DRAFT",
    "DOCUMENTS_PENDING",
    "READY_TO_SHIP",
    "BOOKED",
)


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    repo: RepoDep,
    vendor_repo: VendorRepoDep,
    invoice_repo: InvoiceRepoDep,
    milestone_repo: MilestoneRepoDep,
    activity_repo: ActivityRepoDep,
    user: User = require_auth,
) -> DashboardSummaryResponse:
    if user.role is UserRole.FREIGHT_MANAGER:
        return await _fm_summary(repo, invoice_repo, milestone_repo, activity_repo)

    if user.role not in _DASHBOARD_FULL_LAYOUT_ROLES:
        return DashboardSummaryResponse(
            kpis=_ZERO_KPIS,
            awaiting_acceptance=[],
            activity=[],
            fm_kpis=None,
            fm_ready_batches=[],
            fm_pending_invoices=[],
        )

    # SM and PROCUREMENT_MANAGER scope PO-derived KPIs to PROCUREMENT POs and invoice-derived
    # KPIs to invoices whose PO's vendor has vendor_type='PROCUREMENT'. ADMIN sees all.
    procurement_only = user.role in {UserRole.SM, UserRole.PROCUREMENT_MANAGER}
    po_type_clause = "AND p.po_type = 'PROCUREMENT'" if procurement_only else ""

    def _sum_usd(rows: list) -> Decimal:
        # Each row is one PO with its line-item subtotal in PO's native currency.
        total = Decimal("0")
        for r in rows:
            rate = RATE_TO_USD.get(r["currency"], Decimal("1"))
            total += Decimal(str(r["total_value"])) * rate
        return total.quantize(Decimal("0.01"))

    # --- KPI 1: PENDING POs ---
    pending_rows = await repo._conn.fetch(
        f"""
        SELECT p.currency,
               COALESCE(SUM(CAST(li.quantity AS REAL) * CAST(li.unit_price AS REAL)), 0) AS total_value
        FROM purchase_orders p
        LEFT JOIN line_items li ON li.po_id = p.id
        WHERE p.status IN ('DRAFT', 'PENDING', 'MODIFIED')
          {po_type_clause}
        GROUP BY p.id, p.currency
        """
    )
    pending_count = len(pending_rows)
    pending_total_usd = _sum_usd(pending_rows)

    # --- KPI 2: AWAITING ACCEPTANCE ---
    awaiting_rows_for_kpi = await repo._conn.fetch(
        f"""
        SELECT p.currency,
               COALESCE(SUM(CAST(li.quantity AS REAL) * CAST(li.unit_price AS REAL)), 0) AS total_value
        FROM purchase_orders p
        LEFT JOIN line_items li ON li.po_id = p.id
        WHERE p.status = 'PENDING'
          AND p.last_actor_role = 'SM'
          {po_type_clause}
        GROUP BY p.id, p.currency
        """
    )
    awaiting_count = len(awaiting_rows_for_kpi)
    awaiting_total_usd = _sum_usd(awaiting_rows_for_kpi)

    # --- KPI 3: IN PRODUCTION ---
    # ACCEPTED POs whose latest milestone is an in-production state.
    # SM scopes to PROCUREMENT only; ADMIN sees all po_types.
    milestone_placeholders = ", ".join(
        f"${i + 1}" for i in range(len(_IN_PRODUCTION_MILESTONES))
    )
    in_production_rows = await milestone_repo._conn.fetch(
        f"""
        SELECT p.currency,
               COALESCE(SUM(CAST(li.quantity AS REAL) * CAST(li.unit_price AS REAL)), 0) AS total_value
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
        LEFT JOIN line_items li ON li.po_id = p.id
        WHERE p.status = 'ACCEPTED'
          {po_type_clause}
          AND lm.milestone IN ({milestone_placeholders})
        GROUP BY p.id, p.currency
        """,
        *_IN_PRODUCTION_MILESTONES,
    )
    in_production_count = len(in_production_rows)
    in_production_total_usd = _sum_usd(in_production_rows)

    # --- KPI 4: OUTSTANDING A/P ---
    # Sum of invoice subtotals where status IN ('SUBMITTED','APPROVED','DISPUTED').
    # SM also joins through PO -> vendor with vendor_type='PROCUREMENT'.
    if procurement_only:
        ap_rows = await invoice_repo._conn.fetch(
            """
            SELECT i.currency,
                   COALESCE(SUM(sub.subtotal), 0) AS total
            FROM invoices i
            JOIN purchase_orders po ON i.po_id = po.id
            JOIN vendors v ON po.vendor_id = v.id
            LEFT JOIN (
                SELECT invoice_id,
                       SUM(CAST(quantity AS REAL) * CAST(unit_price AS REAL)) AS subtotal
                FROM invoice_line_items
                GROUP BY invoice_id
            ) sub ON sub.invoice_id = i.id
            WHERE i.status IN ('SUBMITTED', 'APPROVED', 'DISPUTED')
              AND v.vendor_type = 'PROCUREMENT'
            GROUP BY i.currency
            """
        )
    else:
        ap_rows = await invoice_repo._conn.fetch(
            """
            SELECT i.currency,
                   COALESCE(SUM(sub.subtotal), 0) AS total
            FROM invoices i
            LEFT JOIN (
                SELECT invoice_id,
                       SUM(CAST(quantity AS REAL) * CAST(unit_price AS REAL)) AS subtotal
                FROM invoice_line_items
                GROUP BY invoice_id
            ) sub ON sub.invoice_id = i.id
            WHERE i.status IN ('SUBMITTED', 'APPROVED', 'DISPUTED')
            GROUP BY i.currency
            """
        )

    outstanding_ap = Decimal("0")
    for row in ap_rows:
        rate = RATE_TO_USD.get(row["currency"], Decimal("1"))
        outstanding_ap += Decimal(str(row["total"])) * rate

    # --- Awaiting acceptance list (capped at 10) ---
    # total_value is computed from line_items (not stored on the PO row).
    awaiting_rows = await repo._conn.fetch(
        f"""
        SELECT p.id, p.po_number, p.vendor_id, p.currency, p.updated_at,
               COALESCE(SUM(CAST(li.quantity AS REAL) * CAST(li.unit_price AS REAL)), 0) AS total_value
        FROM purchase_orders p
        LEFT JOIN line_items li ON li.po_id = p.id
        WHERE p.status = 'PENDING'
          AND p.last_actor_role = 'SM'
          {po_type_clause}
        GROUP BY p.id, p.po_number, p.vendor_id, p.currency, p.updated_at
        ORDER BY p.updated_at DESC
        LIMIT 10
        """
    )

    # Build vendor name map for awaiting list
    all_vendors = await vendor_repo.list_vendors()
    vendor_map: dict[str, str] = {v.id: v.name for v in all_vendors}

    awaiting_list: list[AwaitingAcceptanceItem] = []
    for row in awaiting_rows:
        rate = RATE_TO_USD.get(row["currency"], Decimal("1"))
        total_usd = Decimal(str(row["total_value"])) * rate
        updated_raw: str = row["updated_at"]
        updated_dt = datetime.fromisoformat(updated_raw)
        if updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=UTC)
        awaiting_list.append(
            AwaitingAcceptanceItem(
                id=row["id"],
                po_number=row["po_number"],
                vendor_name=vendor_map.get(row["vendor_id"], ""),
                total_value_usd=str(total_usd.quantize(Decimal("0.01"))),
                submitted_at=updated_dt,
            )
        )

    # --- Activity feed (capped at 20) ---
    # ADMIN sees all events (target_role=None); SM and PROCUREMENT_MANAGER each see
    # entries targeted to their role plus universal (target_role IS NULL) entries.
    activity_target_role = (
        user.role.value
        if user.role in {UserRole.SM, UserRole.PROCUREMENT_MANAGER}
        else None
    )
    # Fetch a few extra so the dashboard exclusion filter still leaves us a useful feed.
    raw_activity = await activity_repo.list_recent(limit=40, target_role=activity_target_role)
    activity_items: list[DashboardActivityItem] = []
    for entry in raw_activity:
        if entry.event.value in _DASHBOARD_EXCLUDED_EVENTS:
            continue
        activity_items.append(
            DashboardActivityItem(
                id=entry.id,
                entity_type=entry.entity_type.value,
                entity_id=entry.entity_id,
                event=entry.event.value,
                detail=entry.detail,
                category=entry.category.value,
                created_at=entry.created_at,
            )
        )
        if len(activity_items) >= 20:
            break

    return DashboardSummaryResponse(
        kpis=DashboardKpis(
            pending_pos=pending_count,
            pending_pos_value_usd=str(pending_total_usd),
            awaiting_acceptance=awaiting_count,
            awaiting_acceptance_value_usd=str(awaiting_total_usd),
            in_production=in_production_count,
            in_production_value_usd=str(in_production_total_usd),
            outstanding_ap_usd=str(outstanding_ap.quantize(Decimal("0.01"))),
        ),
        awaiting_acceptance=awaiting_list,
        activity=activity_items,
        fm_kpis=None,
        fm_ready_batches=[],
        fm_pending_invoices=[],
    )


async def _fm_summary(
    repo: PurchaseOrderRepository,
    invoice_repo: InvoiceRepository,
    milestone_repo: MilestoneRepository,
    activity_repo: ActivityLogRepository,
) -> DashboardSummaryResponse:
    """Compute the FREIGHT_MANAGER dashboard summary."""

    shipment_in_flight_placeholders = ", ".join(
        f"${i + 1}" for i in range(len(_SHIPMENT_IN_FLIGHT_STATUSES))
    )

    # --- FM KPI 1: ready_batches ---
    # ACCEPTED PROCUREMENT POs whose latest milestone is READY_FOR_SHIPMENT and where
    # accepted_qty > shipped_qty (i.e. still have unshipped goods).
    ready_batch_rows = await milestone_repo._conn.fetch(
        """
        WITH latest_milestone AS (
            SELECT mu.po_id, mu.milestone
            FROM milestone_updates mu
            INNER JOIN (
                SELECT po_id, MAX(posted_at) AS max_posted_at
                FROM milestone_updates
                GROUP BY po_id
            ) latest ON mu.po_id = latest.po_id AND mu.posted_at = latest.max_posted_at
        ),
        accepted_qty AS (
            SELECT li.po_id, SUM(CAST(li.quantity AS INTEGER)) AS total_accepted
            FROM line_items li
            WHERE li.status = 'ACCEPTED'
            GROUP BY li.po_id
        ),
        shipped_qty AS (
            SELECT s.po_id, SUM(CAST(sli.quantity AS INTEGER)) AS total_shipped
            FROM shipment_line_items sli
            JOIN shipments s ON sli.shipment_id = s.id
            GROUP BY s.po_id
        )
        SELECT p.id AS po_id, p.po_number, p.vendor_id, p.updated_at,
               COALESCE(aq.total_accepted, 0) AS accepted_qty,
               COALESCE(sq.total_shipped, 0) AS shipped_qty
        FROM purchase_orders p
        INNER JOIN latest_milestone lm ON lm.po_id = p.id
        LEFT JOIN accepted_qty aq ON aq.po_id = p.id
        LEFT JOIN shipped_qty sq ON sq.po_id = p.id
        WHERE p.status = 'ACCEPTED'
          AND p.po_type = 'PROCUREMENT'
          AND lm.milestone = 'READY_FOR_SHIPMENT'
          AND COALESCE(aq.total_accepted, 0) > COALESCE(sq.total_shipped, 0)
        ORDER BY p.updated_at DESC
        LIMIT 10
        """
    )

    # Count is number of distinct POs (before limit, but limit is 10 which doubles as our count cap)
    # For accurate KPI count we query separately without LIMIT.
    ready_batches_count_row = await milestone_repo._conn.fetchval(
        """
        WITH latest_milestone AS (
            SELECT mu.po_id, mu.milestone
            FROM milestone_updates mu
            INNER JOIN (
                SELECT po_id, MAX(posted_at) AS max_posted_at
                FROM milestone_updates
                GROUP BY po_id
            ) latest ON mu.po_id = latest.po_id AND mu.posted_at = latest.max_posted_at
        ),
        accepted_qty AS (
            SELECT li.po_id, SUM(CAST(li.quantity AS INTEGER)) AS total_accepted
            FROM line_items li
            WHERE li.status = 'ACCEPTED'
            GROUP BY li.po_id
        ),
        shipped_qty AS (
            SELECT s.po_id, SUM(CAST(sli.quantity AS INTEGER)) AS total_shipped
            FROM shipment_line_items sli
            JOIN shipments s ON sli.shipment_id = s.id
            GROUP BY s.po_id
        )
        SELECT COUNT(*) FROM purchase_orders p
        INNER JOIN latest_milestone lm ON lm.po_id = p.id
        LEFT JOIN accepted_qty aq ON aq.po_id = p.id
        LEFT JOIN shipped_qty sq ON sq.po_id = p.id
        WHERE p.status = 'ACCEPTED'
          AND p.po_type = 'PROCUREMENT'
          AND lm.milestone = 'READY_FOR_SHIPMENT'
          AND COALESCE(aq.total_accepted, 0) > COALESCE(sq.total_shipped, 0)
        """
    )
    ready_batches_count = int(ready_batches_count_row or 0)

    # Build vendor name map for ready batch rows
    all_vendors = await repo._conn.fetch("SELECT id, name FROM vendors")
    vendor_map: dict[str, str] = {row["id"]: row["name"] for row in all_vendors}

    fm_ready_batches: list[FmReadyBatch] = [
        FmReadyBatch(
            po_id=row["po_id"],
            po_number=row["po_number"],
            vendor_name=vendor_map.get(row["vendor_id"], ""),
            accepted_qty=int(row["accepted_qty"]),
            shipped_qty=int(row["shipped_qty"]),
        )
        for row in ready_batch_rows
    ]

    # --- FM KPI 2: shipments_in_flight ---
    shipments_in_flight = int(
        await repo._conn.fetchval(
            f"SELECT COUNT(*) FROM shipments WHERE status IN ({shipment_in_flight_placeholders})",
            *_SHIPMENT_IN_FLIGHT_STATUSES,
        )
        or 0
    )

    # --- FM KPI 3: pending_invoices + pending_invoices_value_usd ---
    # Invoices with status='SUBMITTED' from OPEX or FREIGHT vendors, with list (capped at 10).
    pending_invoice_rows = await invoice_repo._conn.fetch(
        """
        SELECT i.id, i.invoice_number, i.currency, i.created_at,
               v.name AS vendor_name, v.vendor_type,
               COALESCE(SUM(CAST(ili.quantity AS REAL) * CAST(ili.unit_price AS REAL)), 0) AS subtotal
        FROM invoices i
        JOIN purchase_orders po ON i.po_id = po.id
        JOIN vendors v ON po.vendor_id = v.id
        LEFT JOIN invoice_line_items ili ON ili.invoice_id = i.id
        WHERE i.status = 'SUBMITTED'
          AND v.vendor_type IN ('OPEX', 'FREIGHT')
        GROUP BY i.id, i.invoice_number, i.currency, i.created_at, v.name, v.vendor_type
        ORDER BY i.created_at DESC
        LIMIT 10
        """
    )

    pending_invoices_count_row = await invoice_repo._conn.fetchval(
        """
        SELECT COUNT(DISTINCT i.id)
        FROM invoices i
        JOIN purchase_orders po ON i.po_id = po.id
        JOIN vendors v ON po.vendor_id = v.id
        WHERE i.status = 'SUBMITTED'
          AND v.vendor_type IN ('OPEX', 'FREIGHT')
        """
    )
    pending_invoices_count = int(pending_invoices_count_row or 0)

    pending_invoices_total = Decimal("0")
    fm_pending_invoices: list[FmPendingInvoiceItem] = []
    for row in pending_invoice_rows:
        rate = RATE_TO_USD.get(row["currency"], Decimal("1"))
        subtotal_usd = Decimal(str(row["subtotal"])) * rate
        pending_invoices_total += subtotal_usd
        created_raw: str = row["created_at"]
        created_dt = datetime.fromisoformat(created_raw)
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=UTC)
        fm_pending_invoices.append(
            FmPendingInvoiceItem(
                id=row["id"],
                invoice_number=row["invoice_number"],
                vendor_name=row["vendor_name"],
                vendor_type=row["vendor_type"],
                subtotal_usd=str(subtotal_usd.quantize(Decimal("0.01"))),
                submitted_at=created_dt,
            )
        )

    # Sum all SUBMITTED invoices for the KPI value (not just the list's 10).
    pending_invoices_value_row = await invoice_repo._conn.fetch(
        """
        SELECT i.currency,
               COALESCE(SUM(CAST(ili.quantity AS REAL) * CAST(ili.unit_price AS REAL)), 0) AS subtotal
        FROM invoices i
        JOIN purchase_orders po ON i.po_id = po.id
        JOIN vendors v ON po.vendor_id = v.id
        LEFT JOIN invoice_line_items ili ON ili.invoice_id = i.id
        WHERE i.status = 'SUBMITTED'
          AND v.vendor_type IN ('OPEX', 'FREIGHT')
        GROUP BY i.currency
        """
    )
    pending_invoices_value_usd = Decimal("0")
    for row in pending_invoices_value_row:
        rate = RATE_TO_USD.get(row["currency"], Decimal("1"))
        pending_invoices_value_usd += Decimal(str(row["subtotal"])) * rate

    # --- FM KPI 4: docs_missing ---
    # Pending shipment document requirements scoped to in-flight shipments.
    docs_missing = int(
        await invoice_repo._conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM shipment_document_requirements sdr
            JOIN shipments s ON sdr.shipment_id = s.id
            WHERE sdr.status = 'PENDING'
              AND s.status IN ({shipment_in_flight_placeholders})
            """,
            *_SHIPMENT_IN_FLIGHT_STATUSES,
        )
        or 0
    )

    # --- Activity feed for FM ---
    raw_activity = await activity_repo.list_recent(limit=40, target_role="FREIGHT_MANAGER")
    activity_items: list[DashboardActivityItem] = []
    for entry in raw_activity:
        if entry.event.value in _DASHBOARD_EXCLUDED_EVENTS:
            continue
        activity_items.append(
            DashboardActivityItem(
                id=entry.id,
                entity_type=entry.entity_type.value,
                entity_id=entry.entity_id,
                event=entry.event.value,
                detail=entry.detail,
                category=entry.category.value,
                created_at=entry.created_at,
            )
        )
        if len(activity_items) >= 20:
            break

    return DashboardSummaryResponse(
        kpis=_ZERO_KPIS,
        awaiting_acceptance=[],
        activity=activity_items,
        fm_kpis=FmKpis(
            ready_batches=ready_batches_count,
            shipments_in_flight=shipments_in_flight,
            pending_invoices=pending_invoices_count,
            pending_invoices_value_usd=str(pending_invoices_value_usd.quantize(Decimal("0.01"))),
            docs_missing=docs_missing,
        ),
        fm_ready_batches=fm_ready_batches,
        fm_pending_invoices=fm_pending_invoices,
    )
