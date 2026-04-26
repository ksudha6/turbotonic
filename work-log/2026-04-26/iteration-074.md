# Iteration 074 — Shipment booking + READY_FOR_SHIPMENT milestone

## Context

Iter 073 shipped the FREIGHT_MANAGER dashboard wired against existing primitives. KPI 1 (Ready batches) used `READY_TO_SHIP` PO milestone as a proxy and KPI 2 (Shipments in flight) summed shipments in DRAFT/DOCUMENTS_PENDING/READY_TO_SHIP — there was no "BOOKED" status to distinguish "FM has confirmed a carrier" from "physically packed and waiting." Seed data also produced single-status shipments per slot, leaving the FM dashboard sparse on a fresh `make up`.

The user's instruction: extend the seed needs the underlying booking concept to exist first. Two domain gaps:
1. The PO milestone name `READY_TO_SHIP` collides semantically with the per-shipment `READY_TO_SHIP` status. Rename the PO milestone to `READY_FOR_SHIPMENT` so the FM handoff signal is unambiguous.
2. Shipments have no BOOKED or SHIPPED states. FM cannot record a carrier booking, and there is no terminal state.

## JTBD

When I am the FREIGHT_MANAGER, I want to record that a shipment has been booked with a carrier and later mark it shipped, so that the dashboard reflects work-in-flight versus dispatched accurately and SM/ADMIN can see end-to-end shipment state.

When I am running the seed, I want the FM dashboard to render with non-zero values across all four KPIs, so that local testing and demos exercise the whole flow.

## Scope decisions

1. **Milestone rename, not insert.** `READY_TO_SHIP` PO milestone is exactly what `READY_FOR_SHIPMENT` should be. Renaming keeps the 5-stage sequence and avoids backfill ambiguity. DB migration: `UPDATE milestone_updates SET milestone='READY_FOR_SHIPMENT' WHERE milestone='READY_TO_SHIP'`.
2. **Shipment status additions.** Append `BOOKED` and `SHIPPED` to `ShipmentStatus`. Sequence: DRAFT > DOCUMENTS_PENDING > READY_TO_SHIP > BOOKED > SHIPPED. Existing `mark_ready` keeps READY_TO_SHIP as the "ready to be booked" state.
3. **Booking metadata is required at the transition, not optional.** `book_shipment(carrier, booking_reference, pickup_date)` requires all three. Storing nullable columns at rest is fine for unbooked shipments but `book_shipment` must reject empty strings / null pickup.
4. **No frontend booking UI in this iter.** Domain + API + seed + dashboard. Frontend type updates only. The "Book shipment" button on shipment detail page is iter 075+.
5. **PO milestone SHIPPED unchanged.** Still terminal. Auto-promotion when all shipments hit SHIPPED is out of scope (could be future enhancement).

## Tasks

- [x] Domain: `ProductionMilestone.READY_TO_SHIP` → `READY_FOR_SHIPMENT`. Update `MILESTONE_ORDER`.
- [x] Domain: `ShipmentStatus` add `BOOKED`, `SHIPPED`. `Shipment.book_shipment(carrier, booking_reference, pickup_date)` + `Shipment.mark_shipped()` methods with status guards. Booking metadata fields on Shipment.
- [x] Schema: ALTER TABLE shipments ADD carrier/booking_reference/pickup_date/shipped_at (all nullable). UPDATE milestone_updates literal rename.
- [x] Repository: shipment repo persists booking fields on UPDATE path; reconstructor hydrates them with key-presence guard for legacy fixtures.
- [x] Activity: `SHIPMENT_BOOKED` + `SHIPMENT_SHIPPED` events with EVENT_METADATA (LIVE, target_role=SM).
- [x] Router: `POST /shipments/{id}/book` + `POST /shipments/{id}/ship` (ADMIN + SM + FREIGHT_MANAGER). Activity event emitted on success.
- [x] Dashboard: `_SHIPMENT_IN_FLIGHT_STATUSES` adds BOOKED (excludes SHIPPED). FM SQL milestone literal = `'READY_FOR_SHIPMENT'`. `_OVERDUE_THRESHOLDS` and `_IN_PRODUCTION_MILESTONES` updated.
- [x] Seed: `_make_shipments` spans all 5 statuses; BOOKED/SHIPPED rows carry carrier metadata; first accepted PO is reserved (no shipment) and gets READY_FOR_SHIPMENT milestone via `_make_milestone_updates`.
- [x] Frontend types: BOOKED + SHIPPED added to `ShipmentStatus`. `ProductionMilestone` renamed. `MilestoneTimeline.svelte` and `po/+page.svelte` label maps updated.
- [x] Tests: test_critical_path, test_dashboard_summary milestone literals updated; test_api_shipment expected_keys widened; 6 new test_api_shipment booking tests; 9 new test_shipment_domain tests for book/ship transitions and validation.

## Tests

### Existing test impact

Files referencing the old milestone literal and shipment status set:
- `backend/tests/test_critical_path.py` — likely posts READY_TO_SHIP milestone; rename literal.
- `backend/tests/test_dashboard_summary.py` — FM tests assert `ready_batches` count; SQL literal will change. Already shape-only, low risk.
- `backend/tests/test_shipment_domain.py` — existing happy-path covers DRAFT > DOCUMENTS_PENDING > READY_TO_SHIP. Add BOOKED + SHIPPED transitions.
- `backend/tests/test_api_shipment.py` — adjust if any shipment-status assertions break; add booking endpoint smoke test.
- `backend/src/seed.py` test (`test_seed.py`) — variety thresholds: increment milestone variety to expect new milestone name; shipment statuses now span 5 values not 3.
- Frontend: no Playwright fixture references the old PO milestone literal directly (verified `MILESTONE` filter on PO list shows label not enum); `nexus-dashboard.spec.ts` uses zero-shaped fixtures.

### New tests

- `test_shipment_domain.py` — book_shipment from READY_TO_SHIP transitions to BOOKED, populates fields; mark_shipped from BOOKED transitions to SHIPPED, populates shipped_at; book_shipment rejects from non-READY_TO_SHIP states; mark_shipped rejects from non-BOOKED states; booking with empty carrier/ref/pickup raises.
- `test_api_shipment.py` — book endpoint round-trips fields, requires FM/SM/ADMIN role; ship endpoint round-trips.
- `test_seed.py` — assert at least one shipment in BOOKED, at least one in SHIPPED, at least one PO at READY_FOR_SHIPMENT milestone with no shipment.

## Notes

Renamed the PO milestone instead of inserting a new one because `READY_TO_SHIP` PO milestone and `ShipmentStatus.READY_TO_SHIP` were already representing the same lifecycle moment at different granularities. One name removed the ambiguity; FM now reads "READY_FOR_SHIPMENT" milestone as their hand-off signal and tracks individual shipments through DRAFT → DOCUMENTS_PENDING → READY_TO_SHIP → BOOKED → SHIPPED. The schema migration is a one-shot UPDATE on init_db; existing data is rewritten on first boot of the new code.

Booking metadata is required at the transition (`book_shipment` rejects empty/whitespace carrier and booking_reference) but stored as nullable columns at rest because pre-booking shipments legitimately have nothing to record. SHIPPED is terminal — `mark_shipped` is the last status transition; no auto-promotion of the PO milestone to SHIPPED yet. That coupling is a fair candidate for a future iter once the FM workflow is exercised in practice.

Dashboard semantics: `_SHIPMENT_IN_FLIGHT_STATUSES` now includes BOOKED so an FM looking at "Shipments in flight" sees everything that hasn't yet left the dock. SHIPPED drops out (out of FM's daily worklist). KPI 4 (Docs missing) likewise scoped to in-flight, so SHIPPED requirements no longer skew the count.

Seed extension reserves the first accepted PO (no shipments, READY_FOR_SHIPMENT milestone) so the FM ready-batches KPI is non-zero on a fresh `make up`. Remaining 5 accepted POs get shipments cycling through all 5 statuses, two of which (BOOKED, SHIPPED) carry carrier metadata.

### Carry-forward backlog
- Frontend "Book shipment" + "Mark shipped" UI on `/shipments/[id]` page (currently no UI to invoke the new endpoints).
- Vendor → FM mapping schema change (FM scoped to specific OPEX/FREIGHT vendors).
- OpEx/Freight invoice approval routing (SM owns procurement only).
- Auto-promote PO milestone to SHIPPED when all shipments hit SHIPPED.
- Shipment list page (currently only detail page exists).
- ACTION_REQUIRED activity row pinning + color helper.
- Sidebar collapse mode for desktop.
- End-of-Phase-4 cleanup: drop legacy `GET /api/v1/dashboard/`.

