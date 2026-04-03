# Iteration 14 — 2026-03-30

## Context
Invoice creation with quantity control. Backend CRUD, lifecycle transitions, and a basic creation UI already exist, but creation copies all PO line items at full quantity with no editing. This iteration adds editable quantities on the creation form, a cumulative over-invoicing guard (total invoiced per line cannot exceed ordered), and remaining-quantity visibility on the PO detail.

## JTBD
1. **When** I create an invoice against an accepted PO, **I want to** specify the quantity per line item (pre-filled with the remaining uninvoiced quantity) **so that** I can invoice partial shipments without exceeding what was ordered.
2. **When** I'm filling in invoice quantities, **I want** the system to reject any line where cumulative invoiced quantity would exceed the PO's ordered quantity **so that** the buyer is never billed for more than they agreed to.
3. **When** I view the PO detail, **I want to** see how much of each line item has already been invoiced **so that** I know what's left before creating another invoice.

## Tasks

### Backend — Invoiced quantity aggregation
- [x] Add `InvoiceRepository.invoiced_quantities(po_id) -> dict[str, int]` — sums quantity per part_number across all non-DISPUTED invoices for a PO
- [x] Add `GET /api/v1/invoices/po/{po_id}/remaining` — returns per-line remaining quantity (PO ordered minus invoiced)

**AC:** Endpoint returns `{ "lines": [{ "part_number": "X", "ordered": 100, "invoiced": 60, "remaining": 40 }, ...] }`. DISPUTED invoices are excluded from the sum.

### Backend — Over-invoicing guard
- [x] Extend `InvoiceCreate` DTO to accept optional `line_items: list[InvoiceLineItemCreate]` with `part_number` and `quantity`
- [x] When `line_items` is provided, use caller quantities; when omitted, fall back to current behavior (full PO quantities) for backward compatibility
- [x] In `create_invoice` router, fetch invoiced quantities and validate: for each line, `invoiced + requested <= ordered`
- [x] Return 409 with per-line detail on violation

**AC:** Creating an invoice with quantity 60 on a line with ordered=100 and already-invoiced=50 returns 409. Creating with quantity 50 succeeds. Omitting `line_items` still works if full quantity is available.

### Frontend — Invoice creation form
- [x] Replace one-click "Create Invoice" with a modal/page showing PO line items in an editable table
- [x] Pre-fill each line's quantity with the remaining (from `/remaining` endpoint)
- [x] Quantity input clamped: min=0, max=remaining; lines with remaining=0 are read-only
- [x] Lines with quantity=0 are excluded from the created invoice
- [x] Submit sends `{ po_id, line_items: [{ part_number, quantity }] }` to `POST /api/v1/invoices/`
- [x] Disable submit if all quantities are 0

**AC:** User sees each line with part number, description, ordered qty, already invoiced, remaining, and an editable quantity field. Cannot type a value above remaining. Submitting with some lines at 0 creates an invoice with only the non-zero lines.

### Frontend — PO detail invoicing progress
- [x] In the line items table on PO detail, add "Invoiced" and "Remaining" columns (only when PO is ACCEPTED and PROCUREMENT)
- [x] Fetch data from `/remaining` endpoint

**AC:** PO detail line items table shows invoiced/remaining per line. Values update after creating a new invoice.

### Permanent tests — Backend (`backend/tests/`)
- [x] `test_invoiced_quantities_excludes_disputed` — create two invoices, dispute one, verify aggregation excludes it
- [x] `test_over_invoicing_rejected` — create invoice consuming 60 of 100, attempt second with 50, expect 409
- [x] `test_partial_invoice_accepted` — create invoice with 40 of 100, verify success and remaining=60
- [x] `test_zero_quantity_lines_excluded` — send line_items with some qty=0, verify created invoice omits those lines
- [x] `test_remaining_endpoint` — create PO with two lines, invoice partially, verify `/remaining` returns correct values

### Scratch tests — Frontend (`frontend/tests/scratch/iteration-14/`)
- [x] Invoice creation modal shows remaining quantities pre-filled
- [x] Quantity input rejects values above remaining
- [x] PO detail shows invoiced/remaining columns after partial invoice

## Notes
Invoice creation changed from a one-click copy to an editable form with per-line quantity control. The over-invoicing guard lives in the router, not the domain model, because it requires cross-aggregate state (summing across all invoices for a PO). DISPUTED invoices are excluded from the cumulative total so a disputed invoice doesn't permanently consume quantity. Backward compatibility preserved: omitting `line_items` in the request still works but now validates against remaining quantities. DDD vocab updated with Invoiced Quantity, Remaining Quantity, and Over-invoicing Guard.
