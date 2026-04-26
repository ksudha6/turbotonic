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

- [x] Extend `DashboardKpis` model with `pending_pos_value_usd`, `awaiting_acceptance_value_usd`, `in_production_value_usd` alongside the existing counts.
- [x] Refactor KPI 1, 2, 3 queries to return one row per matching PO (currency + line-items subtotal). Sum USD-converted in Python via shared `_sum_usd` helper.
- [x] Add `_DASHBOARD_EXCLUDED_EVENTS` frozenset filtering line-level negotiation events, force transitions, convergence, and email-send failures.
- [x] Pass `target_role=user.role.value` to `list_recent` only for SM (ADMIN passes `None` to see everything; the existing `list_recent` `target_role IS NULL OR target_role = $X` clause handles the rest).
- [x] Fetch 40 raw entries and trim to 20 after exclusion so the curated feed stays useful.
- [x] Extend `test_dashboard_summary.py` with USD field assertions and an exclusion check.
- [x] `make test` — 595 passed.
- [x] Commit `9b8ef27`.

### Task 2 -- Frontend: KPI USD display + activity click-through + hide desktop hamburger

- [x] `frontend/src/lib/types.ts` `DashboardKpis` updated with the three new `*_value_usd` fields.
- [x] `(nexus)/dashboard/+page.svelte`: KPI cards 1-3 now render USD via `KpiCard`'s `delta` prop with `tone: 'neutral'`; KPI 4 stays as the value itself (already USD).
- [x] Activity rows render as `<a href={href}>` when permitted (`PO + canViewPOs(role)` → `/po/[id]`; `INVOICE + canViewInvoices(role)` → `/invoice/[id]`), otherwise as a non-clickable `<span>`. Replaced `ActivityFeed` primitive with an inline `<ul>` because the primitive has no click contract; primitive remains untouched.
- [x] `TopBar.svelte` hides `.toggle` at `≥769px` via media query — no logic change.
- [x] Test fixture updates in `auth-flow.spec.ts`, `notification-bell.spec.ts`, `role-rendering.spec.ts`, `nexus-dashboard.spec.ts` for the new KPI shape. Added click-through test.
- [x] `make test-browser` — 146 passed (145 + 1 new).
- [x] Commit `344ee09`.

### Task 3 -- Iter 072 close

- [x] Iter doc Notes finalized with commits and test counts.
- [x] `work-log/iterations-summary.md` updated.
- [x] Commit, push branch, merge to main with `--no-ff`, delete branch.

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

Iter 072 closed on 2026-04-26. Three commits landed on `iter-072-dashboard-polish`:
- `d046654` Open iter 072 doc.
- `9b8ef27` Backend KPI USD totals + activity event filter.
- `344ee09` Frontend KPI USD display + clickable activity rows + hide desktop hamburger.

Test counts: backend 595 unchanged (existing 4 dashboard tests now assert 7 KPI keys instead of 4 + verify exclusion filter); frontend 145 → 146 (+1 activity click-through test).

### Decisions

- **KPI USD rendering reuses `KpiCard.delta`.** `delta` was meant for percentage/diff chips but the structural fit is clean — small chip below the main value with neutral tone. No new prop on the primitive.
- **Activity click-through bypasses the `ActivityFeed` primitive.** The primitive renders a static `<ul>` with no link/click contract. Adding an `href` prop would creep its scope; instead the dashboard page renders its own `<ul>` with conditional `<a>` vs `<span>` based on per-row permission. Primitive untouched, can be reused elsewhere when read-only feeds are needed.
- **Activity scoping uses `target_role` only for SM.** ADMIN passes `None` so it sees all rows; SM passes `'SM'` and inherits the `target_role IS NULL OR = $X` clause already in `ActivityLogRepository.list_recent`. Other roles never reach this branch (empty payload returned earlier).
- **Activity fetch oversample: limit=40, trim to 20 after exclusion.** Ensures the dashboard feed has 20 useful events even when raw events include excluded line-level deltas.
- **Hamburger hidden at desktop, not removed.** AppShell still owns the `sidebarOpen` state machine for mobile; removing the desktop button is purely cosmetic. `@media (min-width: 769px)` matches the existing breakpoint convention in `AppShell.svelte`.

### DDD vocab assessment

No new domain terms. `docs/ddd-vocab.md` unchanged.

### Carry-forward backlog

- Sidebar collapse/rail mode for desktop. Lovable mock didn't show a collapsed state; brainstorm needed before building. User explicitly deferred to a later iter.
- ACTION_REQUIRED row pinning on the activity feed. User wants pinned + color long-term; iter 072 ships color-only. Follow-up iter to add pinning.
- `ActivityFeed` primitive could grow an `onClick`/`href` contract so the dashboard's custom rendering can collapse back into the primitive. Cosmetic — defer.
- Activity entry click-through for `CERTIFICATE`, `PACKAGING`, `SHIPMENT`, `MILESTONE` event types. Today they render as non-clickable rows because no `(nexus)` aggregate page exists for them yet. Wire when those phases ship.
