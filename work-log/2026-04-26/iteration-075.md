# Iteration 075 — PROCUREMENT_MANAGER dashboard parity

## Context

PROCUREMENT_MANAGER renders the "coming in a later iteration" placeholder on `/dashboard`. Backend [backend/src/routers/dashboard.py:24](backend/src/routers/dashboard.py#L24) gates the full payload to `_ADMIN_OR_SM = {UserRole.ADMIN, UserRole.SM}`; PM falls through to `_ZERO_KPIS`. Frontend [frontend/src/routes/(nexus)/dashboard/+page.svelte:30](frontend/src/routes/(nexus)/dashboard/+page.svelte#L30) mirrors with `isFullLayout = role === 'ADMIN' || role === 'SM'`.

PM should receive the SM payload: same `procurement_only` scoping, same KPIs, same panels. Activity feed filters by `target_role=PROCUREMENT_MANAGER`.

## JTBD

When I sign in as PROCUREMENT_MANAGER, I want the same procurement-scoped dashboard the supply manager sees so I can monitor pending POs, awaiting-acceptance work, in-production batches, and outstanding A/P without action capabilities I don't have.

## Tasks

1. Backend: add `PROCUREMENT_MANAGER` to `TargetRole` enum in [backend/src/domain/activity.py](backend/src/domain/activity.py). Without this, `_row_to_entry` raises `ValueError` on any row with `target_role='PROCUREMENT_MANAGER'`.
2. Backend: rename `_ADMIN_OR_SM` to `_DASHBOARD_FULL_LAYOUT_ROLES` and add `UserRole.PROCUREMENT_MANAGER`.
3. Backend: extend `procurement_only` to `True` for `{SM, PROCUREMENT_MANAGER}` (PM scopes the same way SM does).
4. Backend: extend the activity-feed `target_role` filter so PM passes `target_role="PROCUREMENT_MANAGER"`. ADMIN keeps `None`.
5. Frontend: extend [+page.svelte:30](frontend/src/routes/(nexus)/dashboard/+page.svelte#L30) `isFullLayout` to include PM.
6. Update `docs/ddd-vocab.md` if any new terms emerge (none expected).

### Out of scope (follow-up)
- Fan-out of activity events to PROCUREMENT_MANAGER. Today every seeded event uses the EVENT_METADATA default (`target_role=SM`), so PM's activity panel will be near-empty on a fresh seed. Revisit which events should fan out to PM in a separate iter.

## Tests

### Existing test impact
- `backend/tests/test_dashboard_summary.py::test_vendor_returns_empty_payload` — still valid (VENDOR remains on the empty branch until iter 076). No change.
- `frontend/tests/nexus-dashboard.spec.ts` — `VENDOR sees the placeholder panel` is still valid. No PM assertion exists.
- No fixtures or mocks need updating.

### Permanent — backend
1. `test_pm_sees_procurement_scoped_summary` — mirror `test_sm_scopes_to_procurement`: seed one PROCUREMENT and one OPEX PO (both PENDING). Assert `kpis.pending_pos == 1`, OPEX PO's value not in `pending_pos_value_usd`. Assert `fm_kpis is None` and `fm_ready_batches == []` (PM is not FM).
2. `test_pm_activity_feed_scoped_by_target_role` — append three activity entries via `ActivityLogRepository.append`: one with `target_role=TargetRole.PROCUREMENT_MANAGER`, one with `target_role=TargetRole.SM`, one with `target_role=None`. Assert PM payload's `activity` contains the PM-targeted entry and the universal entry by ID; assert the SM-targeted entry's ID is absent.

### Permanent — frontend
1. `nexus-dashboard.spec.ts::PROCUREMENT_MANAGER sees the full KPI grid` — mock `/auth/me` with PM role + `/dashboard/summary` with non-zero counts (each `awaiting_acceptance` item must include `submitted_at`). Assert the four KPI test-ids render and `panel-placeholder` is absent.

### Scratch
None. Backend parity test + frontend KPI test cover the change end-to-end.

## Notes

PM receives the SM payload verbatim — no PM-specific KPI variants this iter. Activity panel reads near-empty on a fresh seed because `EVENT_METADATA` defaults `target_role` to SM; per-event fan-out to PM is deferred to a future iter rather than swapping the default, so the seed stays representative of the SM-centric flow. The `TargetRole` enum extension was the load-bearing prerequisite — without it, any seeded row with `target_role='PROCUREMENT_MANAGER'` raises `ValueError` in `_row_to_entry` and the dashboard 500s. Renamed `_ADMIN_OR_SM` to `_DASHBOARD_FULL_LAYOUT_ROLES` so future role additions to the full layout don't fight the constant name.

