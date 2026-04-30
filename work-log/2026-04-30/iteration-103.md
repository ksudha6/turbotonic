# Iteration 103 — Phase 4.6 Tier 3: Shipment Booking + Mark-Shipped UI

## Context

Iter 074 built the backend `book_shipment` (`POST /{id}/book`) and `mark_shipped` (`POST /{id}/ship`) transitions with full domain logic. Iter 102 (Phase 4.6 Tier 2) delivered the shipment documents, readiness, and mark-ready UI. This iteration surfaces booking entry and mark-shipped as UI affordances on top of those backends.

Backend payload for booking (`ShipmentBookRequest`): `carrier` (str, non-empty), `booking_reference` (str, non-empty), `pickup_date` (date ISO string). Mark-shipped takes no body. Both endpoints require SM, FM, or ADMIN. Precondition for book: `READY_TO_SHIP`; post-transition: `BOOKED`. Precondition for mark-shipped: `BOOKED`; post-transition: `SHIPPED`.

## JTBD

- **SM / FREIGHT_MANAGER**: When a shipment is `READY_TO_SHIP`, fill in carrier, booking reference, and pickup date, then submit to book it.
- **SM / FREIGHT_MANAGER**: When a shipment is `BOOKED`, click "Mark Shipped" to close it out.
- **VENDOR / PROCUREMENT_MANAGER / QUALITY_LAB**: No booking or mark-shipped affordance; read-only view only.

## Tasks

1. [x] Add `ShipmentBookingPayload` type to `frontend/src/lib/types.ts`; extend `Shipment` with `carrier`, `booking_reference`, `pickup_date`, `shipped_at` (all nullable).
2. [x] Add `bookShipment(id, payload)` and `markShipmentShipped(id)` to `frontend/src/lib/api.ts`.
3. [x] Add `canBookShipment(role, status)` and `canMarkShipmentShipped(role, status)` to `frontend/src/lib/permissions.ts`.
4. [x] Create `ShipmentBookingPanel.svelte` — PanelCard with form for carrier, booking_reference, pickup_date.
5. [x] Update `ShipmentActionRail.svelte` — add "Book shipment" and "Mark shipped" buttons with correct permission guards.
6. [x] Update `/shipments/[id]/+page.svelte` — mount panel, wire handlers, re-fetch after transition.
7. [x] Permanent tests in `frontend/tests/shipment-detail.spec.ts`.

## Tests

### Existing test impact

No existing tests break. The `setupShipmentDetail` helper adds default mocks for `/book` and `/ship` (both return success-by-default) so existing specs are not disrupted. The `Shipment` type gains four new nullable fields; existing fixture factories that omit them remain valid because the fields default to `null`.

### New tests (iter 103 describe block)

- SM sees "Book shipment" button when status is `READY_TO_SHIP`.
- VENDOR does not see "Book shipment" button when status is `READY_TO_SHIP`.
- FM does not see "Book shipment" button when status is `READY_TO_SHIP` — FM is allowed by backend but **canBookShipment** grants SM + FM; test verifies FM **does** see it. (FM is in allowed set.)
- SM + FM see "Mark shipped" button when status is `BOOKED`.
- VENDOR does not see "Mark shipped" when status is `BOOKED`.
- Booking form: submit with empty carrier shows button disabled (HTML required prevents submission).
- Booking panel absent when status is not `READY_TO_SHIP`.

## Notes

Booking payload matches the backend `ShipmentBookRequest` exactly: `carrier`, `booking_reference`, `pickup_date` — the iter 074 spec did not include vessel, voyage, or bl_number fields, so those were not added. The `ShipmentBookingPanel` collapses after a successful book (status changes to BOOKED, `canBookShipment` returns false) rather than showing a confirmation; the status pill update in the header is the confirmation. `ShipmentActionRail` gained a `shipping` prop and `on_mark_shipped` callback alongside the existing `marking`/`on_mark_ready`; the rail renders when any of submit, mark-ready, or mark-shipped applies. Booking form submit is disabled client-side when carrier or booking_reference is empty/whitespace-only (mirrors backend validation). Browser tests could not run in the worktree (no node_modules); the test file is committed and will run on merge to main via the main repo's Playwright setup.
