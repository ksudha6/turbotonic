# Iteration 28 — Partial PO acceptance

## Context

PO acceptance is all-or-nothing: the vendor accepts or rejects the entire PO. In practice, a vendor may accept some line items and reject others (e.g. can supply 3 of 5 SKUs). This requires per-line-item status tracking and a new acceptance flow.

## JTBD

1. **When** I receive a PO with multiple line items, **I want to** accept some and reject others **so that** the buyer knows exactly which items I can fulfill.
2. **When** some line items are rejected, **I want** the buyer to see which items need attention **so that** they can revise or source elsewhere.
3. **When** all line items on a PO are accepted, **I want** the PO to transition to ACCEPTED automatically **so that** the normal flow continues.

## Acceptance Criteria

### Domain model
1. `LineItem` gets a `status` field: PENDING, ACCEPTED, REJECTED. Default PENDING.
2. `line_items` table gets a `status TEXT NOT NULL DEFAULT 'PENDING'` column.
3. New method `PurchaseOrder.accept_lines(accepted: list[str], rejected: list[str], comment: str | None)` where lists contain part_numbers.
4. Every line item on a PENDING PO must be either accepted or rejected (no partial response). Omitting a line item returns 422.
5. If all lines accepted: PO status becomes ACCEPTED.
6. If any lines rejected: PO status becomes REJECTED, rejection comment is recorded.
7. The existing `accept()` method (accept all) continues to work as a shortcut.
8. `reject()` continues to reject the entire PO.

### API
9. `POST /api/v1/po/{po_id}/accept-lines` with body `{"accepted": ["PN-001", "PN-003"], "rejected": ["PN-002"], "comment": "Cannot source PN-002"}`.
10. Returns the updated PO with per-line statuses visible.

### Frontend
11. When a vendor views a PENDING PO, each line item has accept/reject toggles.
12. A "Submit Response" button sends the accept-lines request.
13. PO detail page shows per-line status pills after partial acceptance.
14. Accepted lines show green, rejected lines show red.

### Read model
15. PO list shows a "Partially Accepted" indicator when some lines are accepted and some rejected (this is a display concern; the PO status itself is REJECTED with a comment explaining the partial response).

### Invoicing impact
16. Only accepted line items are available for invoicing. Rejected lines have `remaining = 0`.

## Tasks

### Backend — Schema
- [ ] Add `status` column to `line_items` table (TEXT, default 'PENDING')
- [ ] Add `LineItemStatus` enum to domain (PENDING, ACCEPTED, REJECTED)

### Backend — Domain
- [ ] Add `status` field to `LineItem` dataclass
- [ ] Add `accept_lines()` method to PurchaseOrder
- [ ] Validate all lines are addressed (no omissions)
- [ ] Transition rules: all accepted -> ACCEPTED, any rejected -> REJECTED with comment
- [ ] Existing `accept()` sets all lines to ACCEPTED

### Backend — API
- [ ] `POST /api/v1/po/{po_id}/accept-lines` endpoint
- [ ] Update PO response to include line item status
- [ ] Update invoicing to exclude REJECTED lines from remaining quantities

### Backend — Repository
- [ ] Persist line item status on save
- [ ] Read line item status on reconstruction

### Frontend
- [ ] Per-line accept/reject toggles on PENDING PO detail
- [ ] Submit Response button
- [ ] Per-line status pills on PO detail (after response)

### Tests (permanent backend)
- [ ] Accept all lines via accept-lines: PO becomes ACCEPTED, all lines ACCEPTED
- [ ] Reject one line: PO becomes REJECTED, comment recorded, line statuses correct
- [ ] Omitting a line item returns 422
- [ ] Existing accept() still works (backward compat)
- [ ] Invoicing excludes REJECTED lines from remaining quantities
- [ ] accept-lines on non-PENDING PO returns 409

### Tests (scratch)
- [ ] Screenshot: PENDING PO with per-line accept/reject toggles
- [ ] Screenshot: PO detail after partial acceptance showing line statuses
