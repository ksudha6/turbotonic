# Iteration 26 — Permanent frontend Playwright tests for activity features

## Context

Iterations 23-24 added the activity log, dashboard feed, notification bell, and detail page timelines. Scratch tests verified the UI visually. This iteration adds permanent Playwright specs that protect against regression using mocked API routes (same pattern as the existing specs in `frontend/tests/`).

## JTBD

1. **When** the dashboard activity feed, notification bell, or detail page timelines change, **I want** automated tests to catch regressions **so that** the features stay working across iterations.

## Acceptance Criteria

1. Dashboard spec covers the activity feed section: renders entries, shows category dots, shows relative time, entries link to correct entity.
2. Notification bell spec: badge appears with mocked unread count, dropdown opens on click, entries render, mark-all-read calls the API.
3. PO detail spec covers the activity timeline section: renders entries with category-colored dots.
4. Invoice detail spec covers the activity timeline section: same.
5. All specs use `page.route()` to mock API responses (no real backend needed).
6. `make test-browser` passes with all new and existing specs.

## Tasks

### Frontend tests
- [x] Add activity API mocks (`unread-count`, activity list) to all existing spec files via `test.beforeEach`
- [x] Add `dashboard-activity.spec.ts` (4 tests: feed entries, PO navigation, invoice navigation, empty state)
- [x] Add `notification-bell.spec.ts` (5 tests: badge visible, badge hidden, dropdown entries, empty dropdown, mark-all-read)
- [x] Add `activity-timeline.spec.ts` (6 tests: PO heading/entries, PO dot color, PO empty, invoice heading/entries, invoice dot color, invoice empty)
- [x] Run `make test-browser` and verify all pass — 59 passed

## Notes

Added `test.beforeEach` activity API mocks to all 5 existing spec files to handle the `NotificationBell` component's `fetchUnreadCount` call on every page mount. Playwright evaluates routes in LIFO order, so `unread-count` is registered after the catch-all `activity/**` to get priority. No new domain terms emerged.
