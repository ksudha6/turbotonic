# Iteration 22 — Invoice PDF export (frontend)

## Context

Iteration 16 added the invoice PDF backend: `generate_invoice_pdf`, `generate_bulk_invoice_pdf`, `GET /api/v1/invoices/{id}/pdf`, and `POST /api/v1/invoices/bulk/pdf`. This iteration wires the frontend to those endpoints. PO detail already has a "Download PDF" button as a pattern to follow.

## JTBD

1. **When** I view an invoice, **I want to** click "Download PDF" **so that** I get a PDF copy without leaving the page.
2. **When** I'm on the invoice list, **I want to** select multiple invoices and download their PDFs in one click **so that** I can batch-process without opening each detail page.

## Acceptance Criteria

### Invoice detail
- "Download PDF" button on the invoice detail page, same placement as the PO detail's PDF button
- Clicking triggers `GET /api/v1/invoices/{id}/pdf` and opens/downloads the result

### Invoice list bulk download
- Per-row checkboxes on the invoice list (same pattern as PO list)
- "Download PDFs" button appears when one or more rows are selected
- Clicking POSTs `{ "invoice_ids": [...] }` to `/api/v1/invoices/bulk/pdf` and triggers browser download
- Selection clears after download

## Tasks

### Frontend — Invoice detail
- [ ] Add "Download PDF" button to `/invoice/[id]` page
- [ ] Add `downloadInvoicePdf(id)` to `api.ts` (opens `/api/v1/invoices/{id}/pdf` in new tab, same as PO PDF)

### Frontend — Invoice list bulk
- [ ] Add per-row checkboxes to invoice list page
- [ ] Track selected invoice IDs in state
- [ ] Add "Download PDFs" bulk button (visible when selection is non-empty)
- [ ] Add `downloadBulkInvoicePdf(ids)` to `api.ts` (POST, receive blob, trigger download)

### Scratch tests (`frontend/tests/scratch/iteration-22/`)
- [ ] Screenshot: Invoice detail with "Download PDF" button
- [ ] Screenshot: Invoice list with checkboxes and "Download PDFs" button after selection

## Notes

