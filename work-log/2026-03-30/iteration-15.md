# Iteration 15 — 2026-03-30

## Context
Invoice list and detail views. The invoice detail page exists and is functional (status pill, line items, lifecycle actions, dispute dialog). What's missing: a top-level `/invoices` list page, a global list endpoint on the backend, an "Invoices" nav link, invoice counts on the dashboard, PO/vendor context on `InvoiceListItem`, dropdown filters, and pagination.

## JTBD

1. **When** I want to find a specific invoice, **I want to** browse a filterable list of all invoices **so that** I don't have to navigate through individual POs to find it.
2. **When** I'm reviewing invoices, **I want to** filter by status and see the source PO number and vendor **so that** I can quickly identify which invoices need attention.
3. **When** I open the dashboard, **I want to** see invoice counts and totals by status **so that** I have visibility into the invoicing pipeline alongside PO data.
4. **When** I'm looking for invoices matching specific criteria, **I want to** select from dropdowns for PO number, vendor, invoice number, and pick a date range **so that** I can narrow results without typing or scrolling through the full list.
5. **When** the invoice list grows large, **I want to** page through results **so that** the page loads fast and I can navigate systematically.

## Acceptance Criteria

### 1. Invoice List Endpoint
- `GET /api/v1/invoices/` returns paginated invoices with optional filters: `status`, `po_number`, `vendor_name`, `invoice_number`, `date_from`, `date_to`, `page`, `page_size`
- Response shape: `{ items, total, page, page_size }`
- Text filters use case-insensitive substring matching
- Date filters use inclusive range
- Each list item includes `id`, `invoice_number`, `status`, `subtotal`, `created_at`, `po_number`, `vendor_name`
- Sorted by `created_at` descending (newest first)

### 2. Invoice List Page (`/invoices`)
- Table with columns: Invoice #, PO #, Vendor, Status, Subtotal, Created
- Filter bar: status dropdown, invoice # dropdown, PO # dropdown, vendor dropdown, date from, date to
- Dropdown options populated from available data (vendors from API, PO#/invoice# from invoice data)
- Clear button resets all filters
- Invoice number links to `/invoice/{id}`
- PO number links to `/po/{po_id}`
- Pagination: Previous/Next, page size selector, "Showing X-Y of Z"
- Empty state when no invoices match

### 3. Nav Link
- "Invoices" added to the nav bar between "Purchase Orders" and "Vendors"

### 4. Dashboard Invoice Summary
- Invoice status breakdown: count and USD-equivalent total per status
- Displayed alongside existing PO summary

## Tasks

### Backend — Global invoice list endpoint
- [x] Add `InvoiceRepository.list_all(status?)` returning invoices joined with PO number and vendor name
- [x] Add enriched `InvoiceListItemWithContext` DTO: extends `InvoiceListItem` with `po_id`, `po_number`, `vendor_name`
- [x] Add `GET /api/v1/invoices/` route with optional `status` query param
- [x] Add invoice summary to dashboard endpoint: count and USD total per invoice status

### Backend — Invoice list filters
- [x] Extend `GET /api/v1/invoices/` with query params: `po_number`, `vendor_name`, `invoice_number`, `date_from`, `date_to`
- [x] Extend `InvoiceRepository.list_all` to accept and apply these filters (LIKE for text, >= / <= for dates)

### Backend — Pagination
- [x] Add `page` and `page_size` query params to `GET /api/v1/invoices/`
- [x] Add `PaginatedInvoiceList` DTO with `items`, `total`, `page`, `page_size`
- [x] `InvoiceRepository.list_all` returns `(rows, total_count)` with LIMIT/OFFSET

### Frontend — Invoice list page
- [x] Add `listAllInvoices(params?)` to `api.ts`
- [x] Create `/invoices` route (`frontend/src/routes/invoices/+page.svelte`)
- [x] Table: Invoice #, PO #, Vendor, Status (pill), Subtotal, Created
- [x] Invoice # links to detail, PO # links to PO detail
- [x] Empty state message

### Frontend — Dropdown filters
- [x] Status dropdown (static options)
- [x] Vendor dropdown (populated from vendors API)
- [x] PO # dropdown (populated from invoice data)
- [x] Invoice # dropdown (populated from invoice data)
- [x] Date from/to date pickers
- [x] Clear filters button (visible only when a filter is active)
- [x] All filter changes reset page to 1

### Frontend — Pagination
- [x] Page state, page size selector (10/20/50)
- [x] Previous/Next buttons, "Showing X-Y of Z", "Page N of M"
- [x] `listAllInvoices` passes `page` and `page_size`, reads back `total`

### Frontend — Nav and dashboard
- [x] Add "Invoices" link to nav bar in `+layout.svelte`
- [x] Add invoice summary section to dashboard page

### Permanent tests — Backend (`backend/tests/`)
- [x] `test_list_invoices_returns_all` — create 2 invoices on different POs, list returns both with po_number and vendor_name
- [x] `test_list_invoices_filter_by_status` — create invoices in different statuses, filter returns only matching
- [x] `test_list_invoices_empty` — no invoices returns paginated empty envelope
- [x] `test_dashboard_includes_invoice_summary` — create invoices, verify dashboard response has invoice status counts
- [x] `test_list_invoices_filter_by_po_number` — filter by partial PO number returns matching invoices
- [x] `test_list_invoices_filter_by_vendor_name` — filter by vendor name substring returns matching invoices
- [x] `test_list_invoices_filter_by_invoice_number` — filter by invoice number substring returns matching invoices
- [x] `test_list_invoices_filter_by_date_range` — filter by date_from/date_to returns invoices within range

### Permanent tests — Frontend (`frontend/tests/`)
- [x] Invoice list loads and displays invoice rows with PO and vendor context
- [x] Status filter narrows displayed invoices
- [x] Invoice row links navigate to detail and PO pages
- [x] Dashboard shows invoice summary section

### Scratch tests (`frontend/tests/scratch/iteration-15/`)
- [x] Screenshot: Invoice list page with multiple invoices
- [x] Screenshot: Invoice list filtered by status
- [x] Screenshot: Dashboard with invoice summary

## Notes

Invoice list built as a paginated read model with PO and vendor context joined at query time. Filters use dropdowns for structured values (status, PO#, vendor, invoice#) and date pickers for range. Dropdown options for PO# and invoice# are populated from a one-time large fetch of invoice data; vendor dropdown uses the existing vendors API. Pagination follows the same pattern as the PO list (page/page_size with LIMIT/OFFSET in SQLite). Dashboard extended with invoice status summary using the same USD conversion as PO totals.
