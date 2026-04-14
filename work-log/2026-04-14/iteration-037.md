# Iteration 037 -- Partial PO acceptance

## Context

PO acceptance is all-or-nothing: the vendor accepts or rejects the entire PO. In practice, a vendor may accept some line items and reject others (e.g. can supply 3 of 5 SKUs). This iteration adds per-line-item status tracking and a new acceptance flow. Originally scoped as iteration 028 but carried forward without implementation.

Existing domain: `LineItem` is a value object on `PurchaseOrder` with fields `part_number`, `description`, `quantity`, `uom`, `unit_price`, `hs_code`, `country_of_origin`. No status field exists. `PurchaseOrder.accept()` transitions the entire PO from PENDING to ACCEPTED. The over-invoicing guard in the invoice router uses remaining quantities computed from PO line items minus cumulative invoiced quantities.

## JTBD

- When I receive a PO with multiple line items, I want to accept some and reject others so that the buyer knows exactly which items I can fulfill.
- When some line items are rejected, I want the buyer to see which items need attention so that they can revise or source elsewhere.
- When all line items on a PO are accepted, I want the PO to transition to ACCEPTED automatically so that the normal flow continues.
- When I create an invoice against a partially-accepted PO, I want rejected lines excluded from available quantities so that I only invoice for accepted items.

## Tasks

### Backend -- Schema
- [ ] Add `status` column to `line_items` table: `TEXT NOT NULL DEFAULT 'PENDING'`
- [ ] Migration: existing line items on ACCEPTED POs get status `ACCEPTED`; existing line items on all other POs keep `PENDING`

### Backend -- Domain
- [ ] Add `LineItemStatus` enum to `purchase_order.py`: `PENDING`, `ACCEPTED`, `REJECTED`
- [ ] Add `status: LineItemStatus` field to `LineItem` dataclass, default `PENDING`
- [ ] Add `accept_lines(decisions: list[dict[str, str]], comment: str | None)` method to `PurchaseOrder`:
  - `decisions` is a list of `{"part_number": str, "status": "ACCEPTED" | "REJECTED"}`
  - Requires PO status `PENDING`; raises `ValueError` otherwise
  - Every line item must appear in decisions exactly once (match by `part_number`); omissions or extras raise `ValueError`
  - Sets each line item's status to the corresponding decision
  - If all lines ACCEPTED: PO status becomes `ACCEPTED`
  - If any line REJECTED: PO status becomes `REJECTED`, rejection comment is recorded via `RejectionRecord`
  - `comment` is required when any line is rejected; raise `ValueError` if missing
- [ ] Update existing `accept()` method: set all line items to `ACCEPTED` (backward compat)
- [ ] Update existing `reject()` method: set all line items to `REJECTED`

### Backend -- Repository
- [ ] Persist `line_item.status` on save (INSERT and UPDATE)
- [ ] Read `line_item.status` on reconstruction from DB row

### Backend -- API
- [ ] `POST /api/v1/po/{po_id}/accept-lines`
  - Request body: `{"decisions": [{"part_number": "PN-001", "status": "ACCEPTED"}, {"part_number": "PN-002", "status": "REJECTED"}], "comment": "Cannot source PN-002"}`
  - Returns updated PO with per-line statuses in the response
  - 422 if any line item is omitted or an unknown part_number is included
  - 409 if PO is not in PENDING status
  - Role guard: VENDOR only
- [ ] Update PO response DTO to include `status` field on each line item
- [ ] Update remaining quantities endpoint: exclude REJECTED lines (remaining = 0 for rejected lines)

### Backend -- DTO
- [ ] Add `status: str` to line item response DTO (default "PENDING")
- [ ] Add `AcceptLinesRequest` DTO with `decisions: list[LineDecision]` and `comment: str | None`
- [ ] Add `LineDecision` DTO with `part_number: str` and `status: str` (validated to ACCEPTED or REJECTED)

### Frontend
- [ ] PO detail page (PENDING status, VENDOR role): show accept/reject toggle per line item
  - Default state: all toggles unset (neither accepted nor rejected)
  - Each line item row gets a two-state toggle: Accept (green) / Reject (red)
- [ ] "Submit Response" button: enabled only when all line items have a decision
- [ ] Comment field: appears when any line is marked REJECTED; required before submit
- [ ] After submission: PO detail shows per-line status pills (ACCEPTED green, REJECTED red, PENDING grey)
- [ ] PO list: show "Partial" indicator when PO is REJECTED and has a mix of ACCEPTED and REJECTED lines

### Tests (permanent)
- [ ] Accept all lines via accept-lines: PO becomes ACCEPTED, all lines ACCEPTED
- [ ] Reject one line: PO becomes REJECTED, comment recorded, each line has correct status
- [ ] Omitting a line item returns 422
- [ ] Including an unknown part_number returns 422
- [ ] Existing `accept()` still works and sets all lines to ACCEPTED
- [ ] Existing `reject()` still works and sets all lines to REJECTED
- [ ] accept-lines on non-PENDING PO returns 409
- [ ] Remaining quantities endpoint returns 0 for REJECTED lines
- [ ] Invoice creation excludes REJECTED lines from quantity validation
- [ ] Comment required when any line is rejected; missing comment returns 422

### Tests (scratch)
- [ ] Screenshot: PENDING PO with per-line accept/reject toggles
- [ ] Screenshot: PO detail after partial acceptance showing line status pills

## Acceptance criteria
- [ ] `LineItem` has a `status` field with values PENDING, ACCEPTED, REJECTED
- [ ] `accept_lines()` requires every line item to be addressed; no omissions
- [ ] All accepted -> PO ACCEPTED; any rejected -> PO REJECTED with comment
- [ ] Existing `accept()` and `reject()` methods continue to work unchanged
- [ ] `POST /api/v1/po/{po_id}/accept-lines` endpoint works with role guard VENDOR
- [ ] Invoicing excludes REJECTED lines from remaining quantities
- [ ] Frontend shows per-line toggles for VENDOR on PENDING POs
- [ ] All permanent tests pass
