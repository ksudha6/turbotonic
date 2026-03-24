# Iteration 05 — 2026-03-19

## Context

PO document export. The PO detail page displays all header, trade, line item, and rejection history fields but there is no way to generate a printable or shareable document. Add a PDF export endpoint on the backend and a download button on the frontend PO detail page.

The PO detail includes: po_number, status, vendor (name + country), buyer (name + country), currency, payment_terms, issued_date, required_delivery_date, total_value, ship_to_address, incoterm, port_of_loading, port_of_discharge, country_of_origin, country_of_destination, terms_and_conditions, line items (part_number, description, quantity, uom, unit_price, hs_code, country_of_origin), and rejection_history. No PDF library is currently installed.

## Jobs to Be Done

1. **Export a single PO as PDF** — any status is exportable. The PDF is a clean commercial document: header, buyer/vendor, trade details, line items, terms and conditions. No rejection history.
2. **Resolve reference codes to labels** — the PDF renders human-readable labels ("Shanghai, China" not "CNSHA") for all reference data fields (currencies, countries, ports, incoterms, payment terms).
3. **Download button on PO detail page** — a button on the frontend detail view that triggers a PDF download for the currently viewed PO.

## Decisions

- Library: `reportlab` (pure Python, no system dependencies, simple)
- Rejection history excluded from PDF — operational data, not a commercial document
- All PO statuses exportable
- Reference data codes resolved to labels in the PDF
- Single PO export only, no batch/zip

## Tasks

- [x] Add `reportlab` to project dependencies
- [x] Create PDF generation service that renders a PO as a commercial document with label resolution
- [x] Add `GET /api/v1/po/{id}/pdf` endpoint returning `application/pdf`
- [x] Add download button to frontend PO detail page
- [x] Tests (100 backend, 21 frontend — all pass)

## Tests

### Permanent (backend — `backend/tests/`)
1. **PDF endpoint returns 200 with content-type `application/pdf`** — create a PO, hit the endpoint, assert response headers and non-empty body
2. **PDF endpoint returns 404 for nonexistent PO** — random UUID, assert 404
3. **PDF exports work for every PO status** — create POs in DRAFT, PENDING, ACCEPTED, REJECTED, REVISED; export each; assert 200
4. **PDF contains resolved labels, not codes** — extract text from the generated PDF bytes; assert it contains "Shanghai, China" (not "CNSHA"), "US Dollar" (not "USD"), etc.
5. **PDF excludes rejection history** — create a rejected PO with a rejection comment; export; extract text; assert rejection comment is absent

### Permanent (frontend — `frontend/tests/`)
6. **Download button visible on PO detail page** — navigate to a PO detail, assert the download/export button is present

### Scratch (iteration validation)
7. **Screenshot the download button** on the PO detail page across statuses
