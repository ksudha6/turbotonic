# Iteration 24 — Notification bell and detail page timelines

## Context

Iteration 23 added the `activity_log` table, event recording on all PO/invoice/milestone transitions, delayed overdue notifications, and a dashboard activity feed. This iteration adds the notification bell (unread count, dropdown, mark-read) and per-entity timelines on PO and invoice detail pages.

## JTBD

1. **When** I glance at any page, **I want** a notification bell with an unread count **so that** I know something needs attention without navigating to the dashboard.
2. **When** I view a PO detail page, **I want** to see a timeline of events for that PO **so that** I understand its history.
3. **When** I view an invoice detail page, **I want** to see a timeline of events for that invoice **so that** I understand its history.

## Acceptance Criteria

### Notification bell (frontend + backend)
1. `read_at` (nullable timestamp) column on `activity_log` (added in iteration 23 schema).
2. `GET /api/v1/activity/unread-count` returns the count of events where `read_at IS NULL`.
3. `POST /api/v1/activity/mark-read` accepts `{"event_ids": [...]}` or `{"all": true}` and sets `read_at` to now.
4. Bell icon in the top nav bar with a numeric badge showing unread count. Badge hidden when count is 0.
5. Clicking the bell opens a dropdown listing recent events (up to 10).
6. Each dropdown entry shows: event description, entity link, relative timestamp.
7. "Mark all read" button in the dropdown.
8. Unread count refreshes on page navigation.

### Detail page timelines
9. PO detail page shows an "Activity" section listing events for that PO, ordered chronologically.
10. Invoice detail page shows the same section for that invoice.
11. Each entry shows: colored dot by category, event label, detail text (if present), and formatted timestamp.
12. Uses `GET /api/v1/activity?entity_type=PO&entity_id=UUID`.

## Tasks

### Backend — Read state (built in iteration 23)
- [x] `read_at` column on `activity_log` table
- [x] `unread_count` method on `ActivityLogRepository`
- [x] `mark_read` method on `ActivityLogRepository` (by IDs or all)
- [x] `GET /api/v1/activity/unread-count` route
- [x] `POST /api/v1/activity/mark-read` route

### Frontend — Notification bell
- [x] `NotificationBell.svelte` component (bell SVG icon + badge)
- [x] Added to top nav layout via `.nav-actions`
- [x] Fetches unread count on mount
- [x] Dropdown with recent events on click
- [x] Mark-all-read button in dropdown
- [x] Click-outside overlay closes dropdown

### Frontend — Detail page timelines
- [x] `ActivityTimeline.svelte` component (vertical timeline with colored dots)
- [x] Added Activity section to PO detail page
- [x] Added Activity section to invoice detail page

### Tests (permanent backend — covered in iteration 23 test file)
- [x] `GET /api/v1/activity/unread-count` returns correct count
- [x] `POST /api/v1/activity/mark-read` with all=true marks all events
- [x] `POST /api/v1/activity/mark-read` with event_ids marks only those events
- [x] `GET /api/v1/activity?entity_type=PO&entity_id=X` returns only that PO's events

### Tests (permanent frontend)
- [ ] Notification bell shows badge with correct unread count (carried forward)
- [ ] PO detail page shows activity timeline section (carried forward)
- [ ] Invoice detail page shows activity timeline section (carried forward)

### Tests (scratch)
- [ ] Screenshot: notification bell with unread badge (carried forward)
- [ ] Screenshot: PO detail with activity timeline (carried forward)
- [ ] Screenshot: invoice detail with activity timeline (carried forward)
