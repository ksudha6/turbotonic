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

- [ ] Update `frontend/tests/sidebar-items.spec.ts` for new matrix.
- [ ] Run spec — expect FAIL on FREIGHT_MANAGER (still has POs), VENDOR (no Products), PROCUREMENT_MANAGER (Dashboard-only).
- [ ] Update `frontend/src/lib/ui/sidebar-items.ts` per matrix.
- [ ] Run spec — expect PASS.
- [ ] Update `frontend/src/lib/permissions.ts` (canViewProducts adds VENDOR + PROCUREMENT_MANAGER; canViewInvoices adds PROCUREMENT_MANAGER + FREIGHT_MANAGER; canViewPOs adds PROCUREMENT_MANAGER; mutate-helpers untouched).
- [ ] Run `make test-browser` — expect 150 + sidebar-items pass with new matrix.
- [ ] Commit: `Patch sidebar items + permissions per Phase 4.1 matrix (iter 071 task 1)`.

### Task 2 -- Backend `/api/v1/dashboard/summary` with role scoping

- [ ] Write `backend/tests/test_dashboard_summary.py` with four tests (ADMIN global, SM scoped ≤ ADMIN, VENDOR empty payload, unauthenticated 401).
- [ ] Run pytest — expect 4 fails (404).
- [ ] Add `@router.get("/summary")` in `backend/src/routers/dashboard.py` with role-scoped queries for the four KPIs + awaiting-acceptance list (limit 10) + activity feed (limit 20).
- [ ] Add pydantic models: `DashboardKpis`, `AwaitingAcceptanceItem`, `DashboardActivityItem`, `DashboardSummaryResponse`.
- [ ] Run `make test` — expect 595 passed.
- [ ] Commit: `Add GET /api/v1/dashboard/summary with role scoping (iter 071 task 2)`.

### Task 3 -- Frontend `(nexus)/dashboard/+page.svelte`

- [ ] Add `DashboardSummary` types + `fetchDashboardSummary()` API helper.
- [ ] Create `frontend/src/routes/(nexus)/dashboard/+page.svelte` with AppShell + 4 KpiCards + ActivityFeed + awaiting-acceptance PanelCard. Branch on `role`: ADMIN/SM full layout, others render placeholder PanelCard.
- [ ] Delete `frontend/src/routes/dashboard/+page.svelte`, `frontend/tests/dashboard.spec.ts`, `frontend/tests/dashboard-activity.spec.ts`.
- [ ] Run `cd frontend && npm run build` — expect success.
- [ ] Smoke-test locally as ADMIN, SM, VENDOR via `make up`.
- [ ] Commit: `Replace /dashboard with (nexus)/dashboard for ADMIN+SM (iter 071 task 3)`.

### Task 4 -- Permanent Playwright spec

- [ ] Create `frontend/tests/nexus-dashboard.spec.ts` (5 tests: ADMIN KPIs, SM same layout, awaiting-row click navigates, VENDOR sees placeholder, empty awaiting renders EmptyState).
- [ ] Run `make test-browser` — record exact pass count.
- [ ] Commit: `Add Playwright spec for (nexus)/dashboard (iter 071 task 4)`.

### Task 5 -- Phase 4.1.0 close

- [ ] Finalize this iter doc with test counts + commit SHAs in Notes.
- [ ] Update `work-log/iterations-summary.md` (header date, iteration log row, frontend routes, API surface, Phase 4 backlog).
- [ ] Commit and `git push origin phase-4-1-dashboard`.

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

In progress.
