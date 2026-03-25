# Iteration 06 — 2026-03-24

## Context

The PO list page (`/po`) displays a table with columns: PO Number, Vendor, Issued Date, Delivery Date, Total Value, and Status. A status dropdown filter exists and calls `GET /api/v1/po?status={status}`. No other filtering, search, or pagination exists. The backend returns all matching POs without limit via `PurchaseOrderRepository.list_pos(status)`.

The list item payload includes: `id`, `po_number`, `status`, `vendor_id`, `buyer_name`, `buyer_country`, `vendor_name`, `vendor_country`, `issued_date`, `required_delivery_date`, `total_value`, `currency`. All of these are potential filter/search dimensions.

Add text search and multi-field filtering to the PO list so users can find specific POs quickly as volume grows. The backend should support the filtering to avoid transferring the full dataset to the client.

## Jobs to Be Done

1. **When** I'm looking for a specific PO, **I want to** type a PO number, vendor name, or buyer name into a search box, **so that** I can find it without scrolling through the full list.
2. **When** I need to review POs by vendor, currency, or status, **I want to** filter the list by those dimensions together, **so that** I can narrow down to the relevant subset.
3. **When** the PO list grows large, **I want** results paginated and sorted, **so that** the page loads quickly and results are in a predictable order.
4. **When** I apply filters or search, **I want** the URL to reflect my selections, **so that** I can bookmark or share the filtered view.

## Tasks

### Backend
- [x] Extend `GET /api/v1/po` with query params: `search`, `vendor_id`, `currency`, `status` (keep existing), `sort_by`, `sort_dir`, `page`, `page_size`
- [x] Update `list_pos` repository method to build filtered, sorted, paginated SQL with total count
- [x] Response wrapper: `{ items, total, page, page_size }`
- [x] Search matches against `po_number`, `vendor_name`, `buyer_name` (case-insensitive LIKE)

### Frontend
- [x] Replace standalone status dropdown with unified filter bar: search input (debounced), status/vendor/currency dropdowns
- [x] Add sort controls (default: `created_at` desc)
- [x] Add pagination controls (prev/next, page indicator)
- [x] Sync all filter/search/sort/page state to URL query params
- [x] Wire filters to API; load vendor list and reference data for dropdown options

### Tests

#### Permanent (backend)
1. Search by PO number substring returns matching POs only
2. Search by vendor name substring returns matching POs only
3. Search by buyer name substring returns matching POs only
4. Search is case-insensitive
5. Filter by status returns correct subset
6. Filter by vendor_id returns correct subset
7. Filter by currency returns correct subset
8. Combined filters (status + search + vendor_id) intersect correctly
9. Sort by issued_date asc/desc returns correct order
10. Default sort is created_at desc
11. Invalid sort_by returns 422
12. Pagination: page_size=2 on 5 POs returns 2 items with total=5
13. Page beyond last returns empty items with correct total
14. Empty search string treated as no filter

#### Permanent (frontend)
15. Filter bar renders search input, status/vendor/currency dropdowns
16. Pagination controls appear and clicking Next sends page=2
17. URL state: navigating to `/po?status=DRAFT&search=foo` pre-populates filters

#### Scratch
18. Screenshot filter bar and pagination controls across states

## Notes

Added `list_pos_paginated` to the repository, querying `purchase_orders JOIN vendors` directly in SQL with a `total_value` subquery over `line_items`. This avoids the N+1 pattern of the original `list_pos` (which loaded full aggregates plus a separate vendor lookup). Search uses case-insensitive `LIKE` against `po_number`, `vendor_name`, and `buyer_name`. Sort column comes from an allowlist to prevent injection. The response shape changed from a flat array to `{ items, total, page, page_size }`, requiring a coordinated update of backend, frontend, and all existing tests. Frontend filter/search/sort/page state syncs to URL query params via `goto` with `replaceState`, so filtered views are bookmarkable. Fixed a pre-existing issue where frontend API calls lacked trailing slashes, causing FastAPI 307 redirects to bypass the Vite dev proxy.
