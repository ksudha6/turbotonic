# Iteration 17 — 2026-03-30

## Context
First iteration of the Production Status Tracking module. Vendors post milestone updates against Accepted POs. Milestones are ordered and append-only.

## JTBD
1. When a vendor begins production on an accepted PO, I want to post milestone updates (e.g. Raw Materials Received, Production Started, QC Passed, Ready to Ship, Shipped) so the buyer has visibility into manufacturing progress.
2. When I view a PO, I want to see the current production milestone so I know where the order stands without contacting the vendor.

## Acceptance Criteria
- Milestones are a fixed ordered enum: RAW_MATERIALS, PRODUCTION_STARTED, QC_PASSED, READY_TO_SHIP, SHIPPED
- A milestone update is append-only: records who posted it and when
- Milestones can only be posted on ACCEPTED PROCUREMENT POs
- Milestones must be posted in order (cannot skip ahead)
- A PO's current milestone is the latest one posted
- GET endpoint returns all milestones posted for a PO, in order
- POST endpoint posts the next milestone; rejects duplicates and out-of-order posts

## Tasks
- [x] Backend domain: `ProductionMilestone` enum, `MilestoneUpdate` value object (milestone, posted_at), validation (order enforcement, PO must be ACCEPTED PROCUREMENT)
- [x] Backend persistence: `milestone_updates` table (id, po_id, milestone, posted_at), `MilestoneRepository` (save, list_by_po, latest_for_po)
- [x] Backend API: `GET /api/v1/po/{po_id}/milestones`, `POST /api/v1/po/{po_id}/milestones` with `{ "milestone": "RAW_MATERIALS" }`

## Tests
- [x] Post milestone on ACCEPTED PROCUREMENT PO returns 201
- [x] Reject POST on non-accepted PO (400 or 422)
- [x] Reject POST on non-PROCUREMENT PO (400 or 422)
- [x] Reject out-of-order milestone post (e.g. posting SHIPPED before RAW_MATERIALS)
- [x] Reject duplicate milestone post
- [x] GET returns milestones in posted order
- [x] GET returns empty list when no milestones posted
- [x] Invalid milestone value returns 422

## Notes

`ProductionMilestone` enum with `MILESTONE_ORDER` tuple for sequence enforcement. `validate_next_milestone` checks the proposed milestone is the next in sequence after the latest posted one. Router validates PO is ACCEPTED PROCUREMENT before allowing milestone posts. Milestone repo uses the same `aiosqlite` connection pattern as other repos. Schema adds `milestone_updates` table with FK to purchase_orders.

