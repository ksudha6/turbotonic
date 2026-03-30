# Iteration 12 — 2026-03-30

## Context
I want to build an invoicing module for every PO. An Accepted PO unlocks invoicing based on the payment terms on the PO. This is limited to procurement POs only.

## JTBD
1. **When** a PO reaches Accepted status, **I want to** create an invoice against it **so that** I can track payment obligations for that order.
2. **When** I create an invoice, **I want to** see it pre-populated with the PO's payment terms and line items **so that** I don't re-enter data already captured on the order.
3. **When** I view an invoice, **I want to** transition it through its lifecycle (Draft, Submitted, Approved, Paid, Disputed) **so that** the system reflects the actual payment state.
4. **When** I try to invoice a non-Accepted or non-Procurement PO, **I want to** be blocked **so that** only valid procurement orders enter the invoicing workflow.


## Tasks
- [x]Add `Invoice` domain model: id, invoice_number, po_id, status (Draft/Submitted/Approved/Paid/Disputed), payment_terms, line_items, amounts, timestamps
- [x]Add `InvoiceStatus` enum and lifecycle transitions: Draft→Submitted→Approved→Paid, Submitted→Disputed→Submitted
- [x]Create `invoices` table in schema; gate invoice creation on PO status=Accepted and po_type=Procurement
- [x]Add invoice repository with CRUD and query by PO
- [x]Add invoice API routes: create (pre-populate from PO), get, list by PO, transition endpoints
- [x]Add invoice creation UI on PO detail page: "Create Invoice" button visible only for Accepted Procurement POs
- [x]Add invoice detail page: show line items, amounts, payment terms, status with transition actions
- [x]Add invoice list view on PO detail page: show all invoices for that PO
- [x]Scratch tests — backend domain (`test_invoice_domain.py`):
    - Create invoice from Accepted Procurement PO (happy path, status=DRAFT, fields copied)
    - Reject create from non-Accepted PO (ValueError)
    - Reject create from non-Procurement PO (ValueError)
    - Reject create with empty line items (ValueError)
    - Draft→Submitted, Submitted→Approved, Approved→Paid transitions
    - Submitted→Disputed (with reason), Disputed→Submitted (resolve)
    - Dispute rejects empty/whitespace reason
    - All transitions reject after Paid (terminal state)
    - Subtotal computation matches sum of line item totals
- [x]Scratch tests — backend API (`test_invoice_api.py`):
    - POST /invoices/ from Accepted Procurement PO returns 201 with pre-populated fields
    - POST /invoices/ from non-Accepted PO returns 409
    - POST /invoices/ from Accepted OpEx PO returns 409
    - GET /invoices/{id} returns invoice detail
    - GET /po/{po_id}/invoices returns list of invoices for that PO
    - Full lifecycle walk: Draft→Submitted→Approved→Paid
    - Dispute and resolve cycle: Submitted→Disputed→Submitted
- [x]Scratch tests — frontend (`invoice-creation.spec.ts`, `invoice-lifecycle.spec.ts`):
    - "Create Invoice" button visible on Accepted Procurement PO detail page
    - "Create Invoice" button hidden on non-Accepted PO and on Accepted OpEx PO
    - Invoice detail page shows pre-populated line items, payment terms, currency
    - Submit, Approve, Pay transitions update status display
    - Dispute dialog accepts reason, status changes to Disputed

## Notes
Invoice aggregate gated on Accepted Procurement POs. Line items and payment terms pre-populated from PO on creation. Lifecycle: Draft, Submitted, Approved, Paid (terminal), with a Disputed side-state requiring a reason. Multiple invoices per PO allowed (no unique constraint on po_id). Invoice number format mirrors PO numbering (INV-YYYYMMDD-XXXX). DisputeDialog follows the RejectDialog pattern. Frontend scratch tests not run -- require live dev server. Backend domain tests (13) and API tests (7) all pass.
