# Iteration 21 — OPEX invoicing

## Context

Invoicing is currently gated to PROCUREMENT POs only (iteration 12 decision). OPEX POs also need to be invoiced and paid out. Unlike PROCUREMENT, OPEX invoices do not support partial quantity splits — one invoice covers the full PO.

## JTBD

1. When I have an accepted OPEX PO, I want to create an invoice against it so I can process payment for services or expenses.
2. When I create an OPEX invoice, I want the full PO quantity copied automatically with no line-item editing so the process is simple for non-goods purchases.

## Acceptance Criteria

1. "Create Invoice" button is visible on ACCEPTED OPEX POs.
2. Clicking it creates the invoice immediately with no quantity dialog; all PO line items are copied at full quantity.
3. A second "Create Invoice" attempt on the same OPEX PO returns an error; the frontend surfaces this as an inline message.
4. OPEX invoices follow the same lifecycle as PROCUREMENT invoices: Draft -> Submitted -> Approved -> Paid, with Dispute available from Submitted or Approved.
5. The invoice list page shows OPEX invoices alongside PROCUREMENT invoices with no filtering difference.
6. Sending a `line_items` param when creating an OPEX invoice returns 422 (full-quantity-only rule enforced by the backend).

## Tasks

### Backend
- [x] Remove the PROCUREMENT-only guard from the invoice creation endpoint
- [x] For OPEX POs, reject the `line_items` request body param with 422
- [x] For OPEX POs, enforce one-invoice-per-PO and return 409 on a second attempt
- [x] Copy all PO line items at full quantity when creating an OPEX invoice

### Frontend
- [x] Show "Create Invoice" button on ACCEPTED OPEX PO detail page
- [x] On click, call the create invoice endpoint directly with no quantity dialog
- [x] Display an error message if the endpoint returns 409 (invoice already exists)

## Tests

### Permanent backend
- Creating an invoice against an ACCEPTED OPEX PO returns 201 with all line items at full quantity.
- Creating a second invoice against the same OPEX PO returns 409.
- Creating an OPEX invoice with a `line_items` body param returns 422.
- OPEX invoice follows the full lifecycle: Draft -> Submitted -> Approved -> Paid.

### Permanent frontend
- OPEX PO detail page shows the "Create Invoice" button when status is ACCEPTED.
- Clicking the button creates the invoice and navigates to the invoice detail page.
- If the PO already has an invoice, the button triggers an inline error message.

### Scratch
- Screenshot: ACCEPTED OPEX PO detail with "Create Invoice" button visible.
- Screenshot: invoice detail page after creating from an OPEX PO.
- Screenshot: error state when a second invoice is attempted.

## Notes

OPEX invoice creation reuses the existing code path that copies all PO line items when no `line_items` param is provided. The PROCUREMENT-only guard was replaced with per-type branching: OPEX rejects explicit line_items (422) and enforces one-invoice-per-PO by checking `invoiced_quantities` (409 if any part already has invoiced > 0). Domain model `Invoice.create` now accepts both PROCUREMENT and OPEX po_type values. Frontend shows a direct "Create Invoice" button for OPEX (no quantity dialog) with inline error display on conflict.

