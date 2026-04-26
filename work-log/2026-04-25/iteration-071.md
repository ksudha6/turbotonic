# Iteration 071 -- Phase 4.1 Dashboard for ADMIN + SM

## Context

First iteration of Phase 4.1. Iter 070 closed Phase 4.0 (UI revamp foundation) on `main` at `abe1e15` with 26 primitives, the `(nexus)` layout group, AppShell + Sidebar + TopBar + UserMenu, redirect infrastructure, and 150 Playwright passes (148 pre-existing + 2 axe AA scans).

This iter ships the first redesigned aggregate page under `(nexus)`: the dashboard for ADMIN and SM. Other four roles (VENDOR, FREIGHT_MANAGER, QUALITY_LAB, PROCUREMENT_MANAGER) get a thin placeholder branch on the same `/dashboard` route deferring their full dashboard to a later iter inside Phase 4.1+.

Five plan tasks (see `docs/superpowers/plans/2026-04-25-phase-4-1-dashboard.md`):
1. Sidebar map + permissions matrix patch — FREIGHT_MANAGER drops POs, VENDOR adds Products, PROCUREMENT_MANAGER promoted to SM-equivalent (read-only).
2. Backend `GET /api/v1/dashboard/summary` with role-scoping (ADMIN global, SM PROCUREMENT-only, others empty).
3. Frontend `(nexus)/dashboard/+page.svelte` rendering 4 KPIs + activity + awaiting-acceptance panel for ADMIN/SM, placeholder for others. Pre-revamp `frontend/src/routes/dashboard/+page.svelte` and its two specs deleted.
4. Permanent Playwright spec at `frontend/tests/nexus-dashboard.spec.ts`.
5. Phase close: this doc + `iterations-summary.md` update + push.

KPIs (locked in spec):
- PENDING POs — count where `status IN (DRAFT, PENDING, MODIFIED)`.
- AWAITING ACCEPTANCE — count where `status='PENDING' AND last_actor_role='SM'` (sent to vendor).
- IN PRODUCTION — count where `status='ACCEPTED'` and latest milestone is not SHIPPED.
- OUTSTANDING A/P — USD-converted sum of invoice subtotals where `status IN (SUBMITTED, APPROVED, DISPUTED)`.

SM scopes all of the above to `po.po_type='PROCUREMENT'`; invoice scope joins through PO→vendor where `vendor.vendor_type='PROCUREMENT'`.

Ship gates for 071:
- **Mock-clarity:** the Lovable mock dashboard layout (4 KPI grid + recent activity + a list panel) is followed exactly. KPI specifics + role-specific panel sets were brainstorm-resolved 2026-04-25; "we don't have to fully build it now" — quality KPI/panel and shipments-in-transit deferred. Recorded in spec § Phase 4.1.
- **Past-flow:** 150 Playwright + 591 backend at iter open. Must stay green minus the two pre-revamp dashboard specs intentionally deleted in Task 3.
- **Future-flow:** new endpoint `/summary` is additive (old `/api/v1/dashboard/` route stays). New page lives under `(nexus)` so non-redesigned routes remain untouched.

RFQ aggregate is a future module that will flow into PO; no RFQ-derived data on this dashboard.

## JTBD (Jobs To Be Done)

- As an SM, when I open the dashboard each morning, I want to see how many procurement POs are pending vendor acceptance so I can chase the slow ones before standup.
- As an ADMIN, when I open the dashboard, I want a single global view of every PO and invoice status regardless of PO type so I can spot system-wide bottlenecks.
- As a VENDOR (or any role outside ADMIN/SM), when I open `/dashboard` during Phase 4.1, I want a clear note that my own dashboard is on the way so I do not assume the redesigned site is broken.

## Tasks

### Task 1 -- Sidebar items + permissions matrix patch

- [x] Update `frontend/tests/sidebar-items.spec.ts` for new matrix.
- [x] Run spec — expect FAIL on FREIGHT_MANAGER (still has POs), VENDOR (no Products), PROCUREMENT_MANAGER (Dashboard-only).
- [x] Update `frontend/src/lib/ui/sidebar-items.ts` per matrix.
- [x] Run spec — expect PASS.
- [x] Update `frontend/src/lib/permissions.ts` (canViewProducts adds VENDOR + PROCUREMENT_MANAGER; canViewInvoices adds PROCUREMENT_MANAGER + FREIGHT_MANAGER; canViewPOs adjusted; FREIGHT_MANAGER removed from canViewPOs to match matrix; mutate-helpers untouched).
- [x] Run `make test-browser` — 150 passed.
- [x] Commit `21201db`: `Patch sidebar items + permissions per Phase 4.1 matrix (iter 071 task 1)`. Also touched `frontend/tests/role-rendering.spec.ts` (pre-existing permanent spec encoding old matrix; updated to new matrix).

### Task 2 -- Backend `/api/v1/dashboard/summary` with role scoping

- [x] Write `backend/tests/test_dashboard_summary.py` with four tests (ADMIN global, SM scoped ≤ ADMIN, VENDOR empty payload, unauthenticated 401).
- [x] Run pytest — 4 fails (404) on first run.
- [x] Add `@router.get("/summary")` in `backend/src/routers/dashboard.py` with role-scoped queries for the four KPIs + awaiting-acceptance list (limit 10) + activity feed (limit 20).
- [x] Add pydantic models: `DashboardKpis`, `AwaitingAcceptanceItem`, `DashboardActivityItem`, `DashboardSummaryResponse`.
- [x] Run `make test` — 595 passed.
- [x] Commit `cb17068`: `Add GET /api/v1/dashboard/summary with role scoping (iter 071 task 2)`. Two review-loop amends folded in: spec compliance fix (IN PRODUCTION KPI made conditional on `procurement_only`; ADMIN sees OPEX) and code quality fix (KPIs 1/2/3 + awaiting list deduplicated via `po_type_clause` f-string interpolation; KPI 4 left branched because the SM JOIN delta is structural, not a single clause).

### Task 3 -- Frontend `(nexus)/dashboard/+page.svelte`

- [x] Add `DashboardSummary` types + `fetchDashboardSummary()` API helper.
- [x] Create `frontend/src/routes/(nexus)/dashboard/+page.svelte` with AppShell + 4 KpiCards + ActivityFeed + awaiting-acceptance PanelCard. Branch on `role`: ADMIN/SM full layout, others render placeholder PanelCard.
- [x] Delete `frontend/src/routes/dashboard/+page.svelte`, `frontend/tests/dashboard.spec.ts`, `frontend/tests/dashboard-activity.spec.ts`.
- [x] Run `cd frontend && npm run build` — success.
- [x] Run `make test-browser` — 139 passed (150 baseline − 11 deleted pre-revamp tests; 9 in `dashboard.spec.ts` + 2 in `dashboard-activity.spec.ts` + 1 in `invoice-list.spec.ts:198`).
- [x] Commit `cf05fac`: `Replace /dashboard with (nexus)/dashboard for ADMIN+SM (iter 071 task 3)`.

Collateral test-fixture updates required by the route migration (also in `cf05fac`):
- `frontend/src/routes/+layout.svelte` `isRevampRoute` extended to include `/dashboard` and `/dashboard/*` so the pre-revamp root nav stops doubling up over AppShell's Sidebar.
- `frontend/tests/role-rendering.spec.ts` `mockDashboardRoute` adds an empty `DashboardSummary` mock so ADMIN/SM tests don't hit the catch-all `[]` and crash the new page.
- `frontend/tests/auth-flow.spec.ts` `mockDashboard` adds the same summary mock; the "logout button redirects to /login" and "nav shows user display name" tests updated to click the UserMenu pill before asserting Log out (Log out now lives inside the UserMenu dropdown, not directly in the nav).
- `frontend/tests/notification-bell.spec.ts` `beforeEach` adds `EMPTY_DASHBOARD_SUMMARY` mock so the bell tests don't crash on the new dashboard route.
- `frontend/tests/invoice-list.spec.ts` `dashboard shows invoice summary section` test deleted (asserted on a pre-revamp section that no longer exists).

### Task 4 -- Permanent Playwright spec

- [x] Create `frontend/tests/nexus-dashboard.spec.ts` (6 tests: ADMIN KPIs, SM same layout, awaiting-row click navigates, VENDOR sees placeholder, empty awaiting + empty activity render EmptyState).
- [x] Run `make test-browser` — 145 passed.
- [x] Commit `4dbdf4e`: `Add Playwright spec for (nexus)/dashboard (iter 071 task 4)`.

### Task 5 -- Phase 4.1.0 close

- [x] Finalize this iter doc with test counts + commit SHAs in Notes.
- [x] Update `work-log/iterations-summary.md` (header date, iteration log row, frontend routes, API surface, Phase 4 backlog).
- [x] Commit and `git push origin phase-4-1-dashboard`.

## Existing test impact

Pre-iteration audit:
- `frontend/tests/dashboard.spec.ts` and `frontend/tests/dashboard-activity.spec.ts` test the pre-revamp dashboard route. Both are deleted in Task 3 because the route is being replaced (SvelteKit cannot host two `+page.svelte` files on the same URL path).
- `frontend/tests/sidebar-items.spec.ts` is rewritten in Task 1 to assert the new role matrix.
- `frontend/tests/primitives.spec.ts`, `nexus-shell.spec.ts`, `redirects.spec.ts` are unaffected.
- All backend tests are unaffected except the new `test_dashboard_summary.py`.
- The pre-revamp `fetchDashboard()` and `fetchActivity()` helpers in `frontend/src/lib/api.ts` and the old `GET /api/v1/dashboard/` endpoint stay during this phase. They will be deleted at end of Phase 4 once every aggregate has migrated.

No fixture, mock, or shared helper updates required.

## Tests

### Permanent tests added this iteration
- `backend/tests/test_dashboard_summary.py` — 4 tests for the new endpoint.
- `frontend/tests/nexus-dashboard.spec.ts` — 5 tests for the new dashboard page.
- `frontend/tests/sidebar-items.spec.ts` — updated to cover the new role matrix (test count may change; reported at close).

Net expected at close: **+4 backend tests** (591 → 595), **+5 frontend tests** minus deleted pre-revamp specs (final count from runner output, not predicted).

### Scratch tests
None.

### Logs
- `logs/playwright-test-browser.log` — close snapshot.
- `logs/pytest.log` — expect 595 passed.

## Notes

Iter 071 closed on 2026-04-26. Five commits landed on `phase-4-1-dashboard`:
- `0aec436` Open iter 071: Phase 4.1 dashboard plan + spec decisions log.
- `21201db` Patch sidebar items + permissions per Phase 4.1 matrix (task 1).
- `16290c2` Add GET /api/v1/dashboard/summary with role scoping (task 2). Two review-loop amends folded in: spec compliance fix (IN PRODUCTION KPI made conditional on `procurement_only` so ADMIN sees OPEX) and code quality fix (KPIs 1/2/3 + awaiting list deduplicated via a `po_type_clause` f-string fragment; KPI 4 left branched because the SM JOIN delta is structural).
- `cf05fac` Replace /dashboard with (nexus)/dashboard for ADMIN+SM (task 3). Includes collateral test fixture updates (root layout `isRevampRoute` extension, role-rendering / auth-flow / notification-bell summary mocks, and one deleted pre-revamp invoice-list dashboard test).
- `4dbdf4e` Add Playwright spec for (nexus)/dashboard (task 4). 6 new tests.

Test counts:
- Backend: 591 at iter open → 595 at close (+4 in `test_dashboard_summary.py`).
- Playwright: 150 at iter open → 145 at close. Net delta -5: -11 deleted (9 in pre-revamp `dashboard.spec.ts` + 2 in `dashboard-activity.spec.ts` + 1 retired test in `invoice-list.spec.ts`) and +6 new in `nexus-dashboard.spec.ts`. The `auth-flow.spec.ts` and `notification-bell.spec.ts` updates kept their pass counts unchanged.

### Decisions and design notes

- **Endpoint additivity.** The pre-revamp `GET /api/v1/dashboard/` endpoint stays intact during transition. Phase 4.1 adds `/summary` alongside it. Both will live on until the end-of-revamp cleanup once every aggregate has migrated to a `(nexus)` page.
- **`isRevampRoute` extension.** Adding `/dashboard` to the root layout's revamp-route set was necessary collateral. As more pages move to `(nexus)`, this set will grow. A path-based check is the cleanest signal we have without baking SvelteKit-internal knowledge of route groups into the layout. Each future phase adds its aggregate's path here.
- **Read-only enforcement for PROCUREMENT_MANAGER.** The Phase 4.1 matrix promotes PROCUREMENT_MANAGER to SM-equivalent read access (Dashboard, POs, Invoices, Products). Read-helpers in `permissions.ts` updated; mutation helpers (`canCreatePO`, `canEditPO`, `canSubmitPO`, `canApproveInvoice`, etc.) intentionally untouched — PROCUREMENT_MANAGER is read-only by virtue of not appearing in any mutate guard.
- **`canViewPOs` correction.** Iter 067 had FREIGHT_MANAGER in `canViewPOs`. The Phase 4.1 matrix removes POs from FREIGHT_MANAGER's sidebar; the page-level guard had to follow. Removed FREIGHT_MANAGER, added PROCUREMENT_MANAGER.
- **Spec gap caught in review.** Task 2's first cut applied `AND po_type = 'PROCUREMENT'` unconditionally on the IN PRODUCTION KPI, which would have hidden OPEX POs from ADMIN's count. Spec compliance reviewer caught it; fix branched the query on `procurement_only`. The bug was inherited from the existing `get_dashboard()` endpoint — left alone there since that endpoint is being retired.
- **UserMenu interaction shift.** The pre-revamp root nav put "Log out" directly in the navigation bar; the new `UserMenu` primitive hides it inside a click-to-open dropdown. `auth-flow.spec.ts` two tests (`logout button redirects to /login` and `nav shows user display name when authenticated`) updated to click the user pill before asserting the Log out menuitem is visible.

### DDD vocab assessment

No new domain terms emerged. `KPI`, `awaiting acceptance`, and `outstanding A/P` are presentation-layer rollups, not domain concepts. `docs/ddd-vocab.md` unchanged.

### Carry-forward backlog

Logged in `work-log/iterations-summary.md` for later iters:
- KPI cards should also surface the USD value of the POs alongside the count (e.g. "Pending POs: 4 · $52,000"). Backend `/summary` already computes USD-converted PO totals for the awaiting list — extend the KPI counts to return `{ count, total_usd }` and update KpiCard usage to show both. User feedback from iter 071 smoke test.
- Recent activity panel needs a definition. Iter 071 ships the raw event stream (PO_SUBMITTED, INVOICE_APPROVED, MILESTONE_POSTED, etc.) with relative-time + tone, but the panel needs: (1) which events belong on the dashboard vs only on detail pages, (2) per-role filtering (target_role on the event already exists; ADMIN/SM scoping rules unclear), (3) what makes an event ACTION_REQUIRED vs LIVE in the dashboard context, (4) deep-link click-through behavior (currently no click handler — entries are read-only). Brainstorm before any further panel work.
- TaskGroup fan-out for dashboard summary queries (deferred — iter-scoped to keep connection-pool semantics conservative; hit a transaction-related deadlock in this iter when an over-engineered test attempted shared-connection patching).
- VENDOR / FREIGHT_MANAGER / QUALITY_LAB / PROCUREMENT_MANAGER full dashboards (placeholder shipped this iter; per-role panel sets in subsequent iters).
- Quality flags KPI/panel for SM (line-level cert join — needs Certificate-status read paths integrated into the dashboard query; was discussed during brainstorm and explicitly deferred).
- Shipments-in-transit KPI (waits on shipment aggregate completion).
- QUALITY_LAB lab-scoping requires `User.lab` schema column — its own iter.
- ADMIN dashboard module summary expansions: as more aggregates ship under `(nexus)`, ADMIN may want filterable per-module rollups; not in scope for 4.1.
- Backend cleanup at end of Phase 4: drop `GET /api/v1/dashboard/` and the `fetchDashboard()`/`fetchActivity()` frontend helpers once every aggregate has its own `(nexus)` page.
