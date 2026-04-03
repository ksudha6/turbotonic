# Iteration 16 — Invoice PDF export (backend)

## Context

PO PDF export exists (`generate_po_pdf` in `services/po_pdf.py`, served at `GET /api/v1/po/{id}/pdf`). No equivalent exists for invoices. This iteration builds the PDF generation service and API endpoints. Frontend wiring is handled in iteration 22.

## JTBD

1. **When** a system consumer requests an invoice PDF, **I want** the backend to generate and return it **so that** downstream consumers (frontend, integrations) can serve it to users.
2. **When** multiple invoice PDFs are requested at once, **I want** the backend to return a single combined PDF **so that** bulk operations don't require N individual requests.

## Acceptance Criteria

### Invoice PDF content
- PDF includes: invoice number, status, PO number, vendor name, buyer name, payment terms (resolved label), currency, created date
- Line items table: part number, description, quantity, UoM, unit price, line total
- Subtotal below the table
- Dispute reason shown if invoice is DISPUTED
- Layout follows PO PDF style (reportlab, letter size, same margins and fonts)

### Single PDF endpoint
- `GET /api/v1/invoices/{id}/pdf` returns PDF bytes with `Content-Disposition: attachment; filename="INV-YYYYMMDD-XXXX.pdf"`
- 404 if invoice not found

### Bulk PDF endpoint
- `POST /api/v1/invoices/bulk/pdf` accepts `{ "invoice_ids": [<id>, ...] }`
- Returns a single PDF with one invoice per page
- 400 if `invoice_ids` is empty
- Skips IDs that do not resolve to an existing invoice

## Tasks

### Backend — Invoice PDF service
- [ ] Create `backend/src/services/invoice_pdf.py` with `generate_invoice_pdf(invoice, po, vendor_name, vendor_country) -> bytes`
- [ ] Handle DISPUTED status: include dispute reason section
- [ ] Create `generate_bulk_invoice_pdf(invoices_with_context) -> bytes` for multi-invoice PDF

### Backend — PDF endpoints
- [ ] Add `GET /api/v1/invoices/{id}/pdf` route
- [ ] Add `POST /api/v1/invoices/bulk/pdf` route accepting `{ "invoice_ids": [] }`

### Permanent tests — Backend (`backend/tests/`)
- [ ] `test_invoice_pdf_returns_bytes` — create invoice, GET PDF, verify content-type and non-empty body
- [ ] `test_invoice_pdf_not_found` — GET PDF for nonexistent ID returns 404
- [ ] `test_bulk_invoice_pdf` — create 2 invoices, POST bulk PDF, verify content-type and non-empty body
- [ ] `test_bulk_invoice_pdf_empty_ids` — POST with empty list returns 400
- [ ] `test_bulk_invoice_pdf_skips_missing` — POST with mix of valid and missing IDs returns 200

## Notes

