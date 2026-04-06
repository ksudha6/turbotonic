# Iteration 23 — Activity log and dashboard feed

## Context

No event history exists in the system. Status changes on POs and invoices, milestone posts, and invoice creation are fire-and-forget: only the current state is stored. The dashboard's "Recent Activity" is just the 10 most recently updated POs, not a real event feed.

This iteration adds a domain event log that records what happened, when, and to what. Actor (`who`) is left nullable until auth lands. Three notification categories exist from the start: **live** (something happened), **action_required** (someone needs to act), and **delayed** (entity is overdue). Categories map to future role-based routing (SM vs vendor). Delayed notifications are generated on dashboard load from existing overdue milestone thresholds. The dashboard feed replaces the current placeholder.

## JTBD

1. **When** a PO or invoice changes status, **I want** the system to record the event **so that** I have an audit trail of what happened.
2. **When** I open the dashboard, **I want** to see a chronological activity feed **so that** I can track activity across the system at a glance.
3. **When** a PO's production milestone is overdue, **I want** a delayed notification generated **so that** I'm alerted without manually checking each PO.

## Acceptance Criteria

### Domain event log (backend)
1. `activity_log` table: `id`, `entity_type` (PO | INVOICE), `entity_id`, `event` (enum stored as text), `category` (LIVE | ACTION_REQUIRED | DELAYED), `target_role` (nullable, SM | VENDOR), `actor_id` (nullable), `detail` (nullable text), `read_at` (nullable timestamp), `created_at`.
2. Events recorded:
   - PO: created, submitted, accepted, rejected (with rejection comment in detail), revised
   - Invoice: created, submitted, approved, paid, disputed (with dispute reason in detail)
   - Milestone: posted (with milestone name in detail)
3. Each domain method that triggers a status change appends to the log via repository.
4. `GET /api/v1/activity?limit=N` returns the most recent N events (default 20).
5. `GET /api/v1/activity?entity_type=PO&entity_id=UUID` returns events for a single entity.

### Delayed notifications (backend)
6. On dashboard load, compute overdue milestones using existing thresholds (7 days for RAW_MATERIALS/PRODUCTION_STARTED, 3 days for QC_PASSED/READY_TO_SHIP).
7. Insert a DELAYED activity_log entry for each newly overdue PO (idempotent: skip if a DELAYED entry for that PO + milestone already exists).
8. Delayed events surface in the same feed.

### Dashboard feed (frontend)
9. Replace the current "Recent Activity" (10 most recent POs) with a feed from `GET /api/v1/activity?limit=20`.
10. Each entry shows: icon by category, event description, entity link (PO number or invoice number), and relative timestamp.

## Tasks

### Backend — Schema and model
- [x] Add `activity_log` table to `schema.py`
- [x] Add `ActivityEvent` enum (PO_CREATED, PO_SUBMITTED, PO_ACCEPTED, PO_REJECTED, PO_REVISED, INVOICE_CREATED, INVOICE_SUBMITTED, INVOICE_APPROVED, INVOICE_PAID, INVOICE_DISPUTED, MILESTONE_POSTED, MILESTONE_OVERDUE)
- [x] Add `NotificationCategory` enum (LIVE, ACTION_REQUIRED, DELAYED)
- [x] Add `ActivityLogEntry` dataclass
- [x] Add `ActivityLogRepository` with `append`, `list_recent`, `list_for_entity`

### Backend — Event recording
- [x] PO actions (create, submit, accept, reject, revise, resubmit) append to activity log
- [x] Invoice actions (create, submit, approve, pay, dispute, resolve) append to activity log
- [x] Milestone post appends to activity log
- [x] Map each event to its category and target_role via `EVENT_METADATA`

### Backend — Delayed notifications
- [x] `has_delayed_entry` check + inline append in dashboard endpoint (idempotent)
- [x] Called from the dashboard endpoint after computing overdue POs

### Backend — API routes
- [x] `GET /api/v1/activity` (list recent, optional entity filter)
- [x] `GET /api/v1/activity/unread-count` (for iteration 24)
- [x] `POST /api/v1/activity/mark-read` (for iteration 24)

### Frontend — Dashboard feed
- [x] Add `fetchActivity(limit)` to `api.ts`
- [x] Replace "Recent Activity" section with event feed component
- [x] Render colored dot per category, event text, entity link, relative time

### Tests (permanent backend)
- [x] PO submit creates activity_log entry with event=PO_SUBMITTED, category=ACTION_REQUIRED
- [x] PO reject creates entry with event=PO_REJECTED, detail contains rejection comment
- [x] Invoice create creates entry with event=INVOICE_CREATED
- [x] Invoice dispute creates entry with detail containing dispute reason
- [x] Milestone post creates entry with event=MILESTONE_POSTED, detail contains milestone name
- [x] Overdue milestone generates DELAYED entry; second call is idempotent (no duplicate)
- [x] `GET /api/v1/activity` returns events in reverse chronological order
- [x] `GET /api/v1/activity?entity_type=PO&entity_id=X` returns only events for that PO
- [x] Unread count and mark-read work correctly
- [x] Mark-read with specific IDs marks only those events

### Tests (permanent frontend)
- [ ] Dashboard renders activity feed section with event entries (carried forward)
- [ ] Each feed entry links to the correct PO or invoice detail page (carried forward)

### Tests (scratch)
- [ ] Screenshot: dashboard with activity feed showing mixed event types (carried forward)
