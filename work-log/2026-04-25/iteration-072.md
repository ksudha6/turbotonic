# Iteration 072 -- Phase 4.1 Dashboard polish

## Context

First post-Phase-4.0-merge iter on `main`. Phase 4.1 dashboard for ADMIN+SM merged at `df64d4a`. Smoke-test feedback from iter 071 surfaced four polish items:

1. KPI cards show counts only. User wants the USD value alongside (e.g. "Pending POs · 4 · $52,000").
2. Recent Activity panel ships with no curation — every event type lands there with no scoping rule. Brainstorm-resolved 2026-04-26: per-role `target_role` filter, exclude low-signal line-level negotiation events, click-through to entity detail pages, color-only categorization (no pinning yet).
3. TopBar hamburger is always visible. At ≥769px viewports the sidebar is permanently rendered, so the hamburger is dead weight at desktop.
4. Sidebar is fixed-width on desktop. User wants collapsible later — backlog only, not in 072.

Ship gates:
- Mock-clarity: USD-on-KPI follows the Lovable mock pattern of "metric · supporting figure". Activity panel curation is brainstorm-resolved (no extrapolation).
- Past-flow: 595 backend + 145 Playwright at iter open. Must stay green.
- Future-flow: backend `/summary` shape extends additively; old fields stay (some test mocks may need updating but not the deleted ones).

Scope explicitly NOT in 072:
- Sidebar collapse/rail mode (backlog).
- ACTION_REQUIRED row pinning (backlog — user wants pinned + color long-term, color-only short-term).
- Other-role full dashboards (deferred to per-role iters).

## JTBD (Jobs To Be Done)

- As an SM glancing at the dashboard, when I see a Pending POs count, I want the USD total alongside so I can prioritize without drilling in (4 small POs ≠ 4 big POs).
- As an ADMIN scanning Recent activity, when I see a relevant event, I want to click through to the affected PO/invoice; when I see line-level negotiation noise, I don't want it cluttering the feed at all.
- As any user on a desktop browser, when I look at the topbar, I don't want a hamburger control that does nothing visible.

## Tasks

### Task 1 -- Backend: KPI USD totals + activity event filter

- [ ] Extend `DashboardKpis` model to include `pending_pos_value_usd: str`, `awaiting_acceptance_value_usd: str`, `in_production_value_usd: str` alongside the existing counts. (KPI 4 OUTSTANDING A/P is already a USD sum — no change.)
- [ ] Update KPI 1, 2, 3 SQL in `get_dashboard_summary` to compute `SUM(line_items.quantity * line_items.unit_price * RATE_TO_USD[currency])` per PO. Mirror the existing awaiting-list per-PO USD conversion.
- [ ] Define `_DASHBOARD_EXCLUDED_EVENTS` set in `backend/src/routers/dashboard.py` covering `PO_LINE_MODIFIED`, `PO_LINE_ACCEPTED`, `PO_LINE_REMOVED`, `PO_FORCE_ACCEPTED`, `PO_FORCE_REMOVED`, `PO_CONVERGED`, `EMAIL_SEND_FAILED`. Filter the activity list before returning.
- [ ] Pass `target_role=user.role` to the activity repository's recent-activity method. Verify the method accepts that filter; if not, extend it (separate concern in `activity_repository.py`).
- [ ] Update / extend `backend/tests/test_dashboard_summary.py` for the new KPI fields and the exclusion filter.
- [ ] Run `make test` — expect 595 (or 595+ if new tests added).
- [ ] Commit.

### Task 2 -- Frontend: KPI USD display + activity click-through + hide desktop hamburger

- [ ] Update `frontend/src/lib/types.ts` `DashboardKpis` to match new backend shape.
- [ ] In `frontend/src/routes/(nexus)/dashboard/+page.svelte`, render a secondary USD figure on Pending POs, Awaiting acceptance, In production KPI cards. Reuse `formatUsd`. Outstanding A/P stays as-is (already a USD value).
- [ ] Make activity entries clickable. Compute href from `entity_type + entity_id`: `PO → /po/[id]`, `INVOICE → /invoice/[id]`, others (`CERTIFICATE`, `PACKAGING`, `SHIPMENT`, `MILESTONE`) — gate by current role's read permissions; if no permission, render the row as non-clickable text.
- [ ] In `frontend/src/lib/ui/TopBar.svelte`, hide the `.toggle` hamburger at `≥769px` viewports via `@media (min-width: 769px) { .toggle { display: none; } }`.
- [ ] Update `frontend/tests/nexus-dashboard.spec.ts` for the new KPI USD secondary lines and an activity click-through test.
- [ ] Run `make test-browser` — expect 145+ (depends on new test count).
- [ ] Commit.

### Task 3 -- Iter 072 close

- [ ] Update this iter doc Notes with commits, test counts, and any deviations.
- [ ] Update `work-log/iterations-summary.md` (header date + iteration log row).
- [ ] Commit, push branch, merge to main with `--no-ff`, push main, delete branch.

## Existing test impact

- `backend/tests/test_dashboard_summary.py`: extend assertions for new `_value_usd` keys on KPIs. Test for activity filter (events in the exclusion set must not appear in the response).
- `frontend/tests/nexus-dashboard.spec.ts`: assertions for KPI card USD secondary lines. Add an activity click-through test.
- `frontend/tests/role-rendering.spec.ts`, `auth-flow.spec.ts`, `notification-bell.spec.ts`: their `summary` mock payload must add the new `*_value_usd` keys so the page doesn't crash when accessing `summary.kpis.pending_pos_value_usd` (or coerce to safe default in the page — leaning toward extending mocks since the field is required).

No backend tests outside `test_dashboard_summary.py` should change.

## Tests

### Permanent tests added or extended
- `test_dashboard_summary.py`: `*_value_usd` field assertions, activity exclusion test (verify no `PO_LINE_MODIFIED` appears in the response when seeded).
- `nexus-dashboard.spec.ts`: KPI USD secondary line assertion, activity click-through test.

### Scratch tests
None.

## Notes

In progress.
