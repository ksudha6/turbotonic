# Iteration 26 — Permanent frontend Playwright tests for activity features

## Context

Iterations 23-24 added the activity log, dashboard feed, notification bell, and detail page timelines. Scratch tests verified the UI visually. This iteration adds permanent Playwright specs that protect against regression using mocked API routes (same pattern as the 5 existing specs in `frontend/tests/`).

## JTBD

1. **When** the dashboard activity feed, notification bell, or detail page timelines change, **I want** automated tests to catch regressions **so that** the features stay working across iterations.

## Acceptance Criteria

1. Dashboard spec covers the activity feed section: renders entries, shows category dots, shows relative time, entries link to correct entity.
2. Notification bell spec: badge appears with mocked unread count, dropdown opens on click, entries render, mark-all-read calls the API.
3. PO detail spec covers the activity timeline section: renders entries in chronological order.
4. Invoice detail spec covers the activity timeline section: same.
5. All specs use `page.route()` to mock API responses (no real backend needed).
6. `make test-browser` passes with all new and existing specs.

## Tasks

### Frontend tests
- [ ] Add activity feed assertions to `dashboard.spec.ts` (or new `dashboard-activity.spec.ts`)
- [ ] Add `notification-bell.spec.ts`
- [ ] Add activity timeline assertions to PO detail test (or new spec)
- [ ] Add activity timeline assertions to invoice detail test (or new spec)
- [ ] Run `make test-browser` and verify all pass
