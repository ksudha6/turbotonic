# Iteration 073 -- FREIGHT_MANAGER dashboard

## Context

Phase 4.1 dashboard cycle continues. Iter 071 shipped ADMIN + SM dashboards under `(nexus)/dashboard/`; the other four roles got a thin placeholder. Iter 072 polished iter 071 (KPI USD totals, activity curation, desktop hamburger). This iter ships the FREIGHT_MANAGER (FM) dashboard, replacing the placeholder branch with a role-specific layout.

FM's responsibilities (brainstorm-resolved 2026-04-26):
- **Shipment operations.** FM is the handoff point after production + QC. They book shipments for POs that hit the production-ready milestone, chase missing shipping documents, and mark shipments ready-to-ship.
- **OpEx + Freight invoices.** Logistics and operating expense invoices flow through FM as a review surface (informational this iter; approval routing TBD).

FM's per-role matrix (confirmed iter 071): Dashboard + Invoices in the sidebar. POs do not appear in the sidebar; they're reachable from dashboard click-through (`/po/[id]` on a ready-batch row).

Ship gates:
- Mock-clarity: the Lovable mock did not show an FM-specific layout. Brainstorm-resolved to: 4 KPIs (Ready batches, Shipments in flight, Pending invoices, Docs missing) + 3 panels (Ready batches list, Pending invoices list, Recent activity).
- Past-flow: 595 backend + 146 Playwright at iter open. Must stay green. ADMIN/SM dashboards untouched.
- Future-flow: backend `/summary` extends additively with an FM branch. Existing ADMIN/SM logic and shape unchanged.

Scope explicitly **NOT** in 073:
- New `READY_FOR_SHIPMENT` production milestone (between `QC_PASSED` and `SHIPPED`). Backlog. Iter 073 uses the existing `READY_TO_SHIP` milestone as the closest equivalent.
- Vendor → FM mapping. Today FM sees all OPEX/FREIGHT entities; later each FM is mapped to specific vendors. Backlog.
- **Seed-data extension for shipments + shipment document requirements.** Today's `seed.py` creates zero shipments. Live `make up` will render zeros for FM's shipment-side KPIs (Ready batches, Shipments in flight, Docs missing) until a seed-extension iter ships shipment booking + the document requirement scaffold. Pending invoices KPI may show non-zero from existing OpEx + Freight invoices in seed. Backlog. Tests don't depend on seed (they create fixtures via API).
- OpEx/Freight invoice approval routing. Today `canApproveInvoice` returns true only for SM (and ADMIN via inheritance). Per the iter 073 brainstorm, **SM owns procurement-only**; OpEx/Freight invoices should not be SM's approval surface. Defining the correct approver (likely FM, possibly varying per `po.po_type` / `vendor.vendor_type`) is its own iter. Iter 073 does not change `permissions.ts`.
- VENDOR / QUALITY_LAB / PROCUREMENT_MANAGER full dashboards. Their placeholders stay until their respective iters.

## JTBD (Jobs To Be Done)

- As an FM each morning, when I open the dashboard, I want to see how many POs are ready for me to book a shipment for so I can start that work without hunting through `/po`.
- As an FM tracking shipment readiness, when I see a "Docs missing" count, I want to know how much paperwork is outstanding across all my live shipments at a glance.
- As an FM reviewing OpEx and freight bills, when I see pending invoices on the dashboard, I want to click through to the invoice detail and verify line items match what was shipped — even if I can't approve the invoice myself yet.

## Tasks

### Task 1 -- Backend: extend `/dashboard/summary` for FREIGHT_MANAGER

**Files:**
- Modify: `backend/src/routers/dashboard.py`
- Modify: `backend/tests/test_dashboard_summary.py`

**Approach:** add an `FM_BRANCH` to `get_dashboard_summary` alongside the existing `_ADMIN_OR_SM` branch. When `user.role is UserRole.FREIGHT_MANAGER`, populate FM-specific KPIs + lists. Other non-ADMIN/SM/FM roles continue to receive the empty payload.

**FM payload shape:**

```
DashboardKpis {
    pending_pos: 0  # unused for FM, kept zero for shape compat
    pending_pos_value_usd: "0.00"
    awaiting_acceptance: 0  # unused
    awaiting_acceptance_value_usd: "0.00"
    in_production: 0  # unused
    in_production_value_usd: "0.00"
    outstanding_ap_usd: "0.00"  # unused for FM
}
```

That's incompatible with FM's actual KPIs. Choice point:
- **A. Reuse existing keys, repurpose semantics per role.** E.g. `pending_pos` becomes "ready batches" for FM. Confusing — every consumer needs a role check.
- **B. Add new top-level fields specific to FM** (`fm_kpis: FmKpis | null`). Kpi keys stay role-meaningful.
- **C. Make `kpis` a `dict[str, Kpi]` keyed by KPI id.** Each role returns a different set of keys. Frontend reads only the keys it knows.

**Going with B for this iter** — discrete `fm_kpis` field, optional in the response. Simple to add, easy to test, doesn't mutate existing semantics. Future role iters add their own typed nested object the same way. Down the road we can refactor to C if it becomes unwieldy.

```python
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
    accepted_qty: int  # cumulative across line items
    shipped_qty: int   # cumulative across shipments

class FmPendingInvoiceItem(BaseModel):
    id: str
    invoice_number: str
    vendor_name: str
    vendor_type: str  # 'OPEX' or 'FREIGHT'
    subtotal_usd: str
    submitted_at: datetime

class DashboardSummaryResponse(BaseModel):
    kpis: DashboardKpis  # ADMIN/SM/empty payload
    awaiting_acceptance: list[AwaitingAcceptanceItem]  # ADMIN/SM only
    activity: list[DashboardActivityItem]
    fm_kpis: FmKpis | None = None
    fm_ready_batches: list[FmReadyBatch] = []
    fm_pending_invoices: list[FmPendingInvoiceItem] = []
```

**KPI definitions:**

1. **Ready batches** — POs whose latest milestone is `READY_TO_SHIP` AND remaining unshipped quantity > 0 across line items. Computed via the existing latest-milestone CTE pattern + a join to `shipment_line_items` aggregate.
2. **Shipments in flight** — count of `shipments` with status IN (`DRAFT`, `DOCUMENTS_PENDING`, `READY_TO_SHIP`).
3. **Pending invoices** — count + USD-converted sum of invoices whose status = `SUBMITTED` AND vendor_type IN (`OPEX`, `FREIGHT`).
4. **Docs missing** — count of `shipment_document_requirements` rows with status = `PENDING` joined to shipments not yet ready (i.e. requirement still actionable).

**Activity feed for FM:** call `list_recent(limit=40, target_role='FREIGHT_MANAGER')`. Apply the same `_DASHBOARD_EXCLUDED_EVENTS` exclusion. The result naturally filters to shipment + cert events that target FM.

**Tests:**
- Add `test_fm_sees_ready_batches_and_pending_invoices` covering the four KPIs + at least one entry in each list (seed data has FM-relevant entities; verify count + ordering).
- Update `test_vendor_returns_empty_payload` to also assert `fm_kpis is None` and the FM lists are empty for non-FM roles (and that ADMIN/SM still get fm fields = None / []).

- [ ] Read `backend/src/domain/shipment.py`, `backend/src/shipment_repository.py`, `backend/src/shipment_document_requirement_dto.py`, and `backend/src/services/shipment_service.py` to understand the FM-relevant data model surface.
- [ ] Write the failing pytest tests first.
- [ ] Implement the backend endpoint extension.
- [ ] Run `make test` — expect 595+ (depends on new test count).
- [ ] Commit: `Add FREIGHT_MANAGER branch to /dashboard/summary (iter 073 task 1)`.

### Task 2 -- Frontend: render FM dashboard layout

**Files:**
- Modify: `frontend/src/lib/types.ts` — add `FmKpis`, `FmReadyBatch`, `FmPendingInvoiceItem`, extend `DashboardSummary` with the optional FM fields.
- Modify: `frontend/src/routes/(nexus)/dashboard/+page.svelte` — add an FM branch in the role conditional. Same KpiCard + PanelCard composition pattern as ADMIN/SM, different content.
- Modify: `frontend/tests/nexus-dashboard.spec.ts` — add FM tests.

**Layout:**
- KPI grid: Ready batches | Shipments in flight | Pending invoices | Docs missing.
- Two side-by-side panels (same grid as ADMIN/SM): "Ready batches" + "Pending invoices".
- Full-width "Recent activity" panel below (or stay in side-by-side — keep parallel to ADMIN/SM for consistency: 2 columns side by side, Activity stays in the right column. Drop "Pending invoices" panel into a third row. Decide during impl. Default: replace SM's two-column layout with three rows on FM — Ready batches row, Pending invoices row, Activity row. Each is full-width.)
- Click-through: ready-batch row → `/po/[id]`, pending-invoice row → `/invoice/[id]`, activity row → entity detail (already gated by `canViewInvoices(role)` etc.).

`canViewPOs` does NOT include FM in the matrix. So for FM, ready-batch click-through to `/po/[id]` will hit a 403 unless we extend `canViewPOs` to include FM for read-only, OR rely on the (nexus) layout's auth guard which only checks login. **Decision:** add FM read access to a NEW gate: don't widen `canViewPOs` (page-level rules untouched per "approval routing TBD"). Instead, the dashboard ready-batch click navigates to `/po/[id]` which is the pre-revamp PO detail. The pre-revamp PO detail page enforces its own role checks. If FM gets a 403 there, that's the right outcome until vendor-FM mapping lands.

Update: actually `canViewPOs(FREIGHT_MANAGER)` was REMOVED in iter 071 because the matrix said FM doesn't see POs. Re-adding FM to `canViewPOs` for read-only is required for the click-through to work. **Decision:** add `FREIGHT_MANAGER` to `canViewPOs` to enable the dashboard ready-batch click-through. The sidebar matrix still hides POs from FM (sidebar is decoupled per iter 067 design). This is a small permissions widening — confirm the change is OK during impl.

- [ ] Update `frontend/src/lib/permissions.ts` to add FREIGHT_MANAGER to `canViewPOs`. Update `frontend/tests/sidebar-items.spec.ts` if needed (sidebar still excludes FM from POs — should not need updates). Update `frontend/tests/role-rendering.spec.ts` to remain consistent.
- [ ] Add types in `frontend/src/lib/types.ts`.
- [ ] Add `(nexus)/dashboard/+page.svelte` FM branch.
- [ ] Add Playwright tests for FM dashboard.
- [ ] Run `make test-browser` — expect 146+ passes.
- [ ] Commit: `Render FREIGHT_MANAGER dashboard with shipment + invoice KPIs (iter 073 task 2)`.

### Task 3 -- Iter 073 close

- [ ] Update this iter doc Notes with commits + test counts + any deviations.
- [ ] Update `work-log/iterations-summary.md` (header date + iteration log row).
- [ ] Commit, push branch, merge to main, delete branch.

## Existing test impact

- `test_dashboard_summary.py` — extend tests for FM branch and shape additions; ensure ADMIN/SM/VENDOR tests continue to pass with the new optional fields (defaulting to None / []).
- `nexus-dashboard.spec.ts` — extend with FM tests; existing ADMIN/SM/VENDOR tests should pass without changes (the response shape is additive).
- Test fixtures in `auth-flow.spec.ts`, `notification-bell.spec.ts`, `role-rendering.spec.ts` — no changes needed (FM optional fields default sensibly when missing from mocked summaries).
- `permissions.ts` change: `canViewPOs` adds FREIGHT_MANAGER. Verify no test asserts FM cannot access PO read endpoints (would surface as a broken role-rendering or backend role-guard test).

## Tests

### Permanent tests added
- `test_dashboard_summary.py` — new FM test (~3-5 cases).
- `nexus-dashboard.spec.ts` — new FM tests (~3 cases).

### Scratch tests
None.

## Notes

In progress.

### Carry-forward backlog (will be promoted to iter doc Notes at close)

- **`READY_FOR_SHIPMENT` production milestone.** New milestone between `QC_PASSED` and `SHIPPED`, marking the explicit handoff to FM. Today's `READY_TO_SHIP` is the closest equivalent and serves the dashboard for now.
- **Vendor → FM mapping.** Each FM should be mapped to specific OPEX/FREIGHT vendors, and only their shipments + invoices appear on that FM's dashboard. Schema change: a join table or `freight_manager_id` foreign key on `vendor`. Today's iter 073 shows all FM-relevant entities globally.
- **Invoice approval routing per PO type / vendor type.** SM owns procurement; OpEx/Freight invoices need a different approver (likely FM with possible per-vendor exceptions). `permissions.ts canApproveInvoice` currently returns true only for SM/ADMIN. This is a domain-rules iter that defines who can approve which invoice types and updates the gate accordingly.
