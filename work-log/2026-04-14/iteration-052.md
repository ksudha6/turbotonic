# Iteration 052 -- List pages redesign

## Context

Seven list pages each implement their own table markup, filter bar, pagination, and empty/loading states with varying levels of completeness (PO list has bulk actions and cross-page selection; vendor and product lists lack pagination entirely). This iteration rewires all seven to use DataTable, Pagination, FilterBar, and Badge from the component library, and builds the three new Phase 3 list pages (certificates, packaging, shipments) on the same pattern.

## JTBD (Jobs To Be Done)

- When viewing any list of entities, I want consistent column sorting, filtering, pagination, and actions, so that I can find and act on data efficiently regardless of which entity type I'm browsing.
- When no data matches my filters, I want a clear empty state message, so that I know the result is empty rather than broken.
- When data is loading, I want a skeleton placeholder, so that I see progress instead of a blank page.
- When I need to act on multiple items, I want consistent bulk selection and actions, so that I can operate efficiently.

## Tasks

### Shared FilterBar component (`frontend/src/lib/components/FilterBar.svelte`)
- [ ] Props: `filters` (array of filter definitions), `onApply`, `onClear`
- [ ] Filter types: dropdown (select from options), text (free text search), dateRange (from/to date inputs)
- [ ] "Clear all" button appears when any filter is active
- [ ] Responsive: wraps on narrow screens

### PO list page (`routes/po/+page.svelte`)
- [ ] Replace inline table with DataTable component
- [ ] Columns:

| Column | Key | Sortable | Align |
|--------|-----|----------|-------|
| (checkbox) | _select | no | center |
| PO Number | po_number | yes | left |
| Type | po_type | no | left |
| Vendor | vendor_name | no | left |
| Issued Date | issued_date | yes | left |
| Delivery Date | required_delivery_date | yes | left |
| Total Value | total_value | yes | right |
| Status | status | no | left |
| Production | current_milestone | no | left |

- [ ] Filters: text search (PO#, vendor, buyer), status dropdown, vendor dropdown, currency dropdown, milestone dropdown
- [ ] Sort default: `created_at` descending
- [ ] Pagination: page sizes [10, 20, 50, 100, 200]
- [ ] Bulk actions: Submit, Accept, Reject (context-sensitive by selected statuses)
- [ ] Row click navigates to PO detail
- [ ] "New PO" button in page header (SM role only)
- [ ] Replace inline reject modal with Modal component

### Invoice list page (`routes/invoices/+page.svelte`)
- [ ] Replace inline table with DataTable component
- [ ] Columns:

| Column | Key | Sortable | Align |
|--------|-----|----------|-------|
| (checkbox) | _select | no | center |
| Invoice # | invoice_number | yes | left |
| PO # | po_number | no | left |
| Vendor | vendor_name | no | left |
| Status | status | no | left |
| Subtotal | subtotal | yes | right |
| Created | created_at | yes | left |

- [ ] Filters: status dropdown, invoice # dropdown, PO # dropdown, vendor dropdown, date range (from/to)
- [ ] Sort default: `created_at` descending
- [ ] Pagination: page sizes [10, 20, 50]
- [ ] Bulk actions: Download PDFs (when items selected)
- [ ] Row click navigates to invoice detail

### Vendor list page (`routes/vendors/+page.svelte`)
- [ ] Replace inline table with DataTable component
- [ ] Add pagination (currently no pagination)
- [ ] Columns:

| Column | Key | Sortable | Align |
|--------|-----|----------|-------|
| Name | name | yes | left |
| Country | country | no | left |
| Type | vendor_type | no | left |
| Status | status | no | left |
| Actions | _actions | no | right |

- [ ] Filters: status dropdown (Active/Inactive), type dropdown (Procurement/OpEx/Freight/Miscellaneous)
- [ ] Sort default: `name` ascending
- [ ] Pagination: page sizes [10, 20, 50]
- [ ] Row actions: Deactivate (for active), Reactivate (for inactive) -- rendered as small buttons or dropdown
- [ ] "New Vendor" button in page header (SM role only)
- [ ] Status rendered with Badge component (active = success, inactive = neutral)

### Product list page (`routes/products/+page.svelte`)
- [ ] Replace inline table with DataTable component
- [ ] Add pagination (currently no pagination)
- [ ] Columns:

| Column | Key | Sortable | Align |
|--------|-----|----------|-------|
| Part Number | part_number | yes | left |
| Description | description | no | left |
| Vendor | vendor_name | no | left |
| Requires Cert | requires_certification | no | center |
| Actions | _actions | no | right |

- [ ] Filters: vendor dropdown
- [ ] Sort default: `part_number` ascending
- [ ] Pagination: page sizes [10, 20, 50]
- [ ] Row actions: Edit button
- [ ] "New Product" button in page header (SM role only)
- [ ] Cert status rendered with Badge component (yes = warning "Required", no = neutral "No")

### Certificate list page (`routes/certificates/+page.svelte`) -- new in Phase 3
- [ ] Columns:

| Column | Key | Sortable | Align |
|--------|-----|----------|-------|
| Cert # | cert_number | yes | left |
| Product | product_name | no | left |
| Qualification | qualification_type | no | left |
| Issuer | issuer | no | left |
| Status | status | no | left |
| Issue Date | issue_date | yes | left |
| Expiry Date | expiry_date | yes | left |
| Target Market | target_market | no | left |

- [ ] Filters: status dropdown (Pending/Valid/Expired), product dropdown, qualification type dropdown, target market dropdown
- [ ] Sort default: `issue_date` descending
- [ ] Pagination: page sizes [10, 20, 50]
- [ ] Status rendered with Badge: VALID = success, PENDING = warning, EXPIRED = error
- [ ] Row click navigates to certificate detail

### Packaging spec list page (`routes/packaging/+page.svelte`) -- new in Phase 3
- [ ] Columns:

| Column | Key | Sortable | Align |
|--------|-----|----------|-------|
| Spec Name | spec_name | yes | left |
| Product | product_name | no | left |
| Marketplace | marketplace | no | left |
| Status | status | no | left |
| Actions | _actions | no | right |

- [ ] Filters: marketplace dropdown, status dropdown (Pending/Collected), product dropdown
- [ ] Sort default: `spec_name` ascending
- [ ] Pagination: page sizes [10, 20, 50]
- [ ] Status rendered with Badge: COLLECTED = success, PENDING = warning
- [ ] Row actions: View/Upload files
- [ ] "New Spec" button in page header (SM role only)

### Shipment list page (`routes/shipments/+page.svelte`) -- new in Phase 3
- [ ] Columns:

| Column | Key | Sortable | Align |
|--------|-----|----------|-------|
| Shipment # | shipment_number | yes | left |
| PO # | po_number | no | left |
| Marketplace | marketplace | no | left |
| Status | status | no | left |
| Created | created_at | yes | left |

- [ ] Filters: status dropdown (Draft/Documents Pending/Ready to Ship), PO # dropdown, marketplace dropdown
- [ ] Sort default: `created_at` descending
- [ ] Pagination: page sizes [10, 20, 50]
- [ ] Status rendered with Badge: DRAFT = neutral, DOCUMENTS_PENDING = warning, READY_TO_SHIP = success
- [ ] Row click navigates to shipment detail
- [ ] "New Shipment" button in page header (SM and FREIGHT_MANAGER roles)

### Tests (scratch)
- [ ] Screenshot each list page at 1280px with data (5+ rows)
- [ ] Screenshot each list page at 1280px with no data (empty state)
- [ ] Screenshot each list page at 1280px in loading state (skeleton)
- [ ] Screenshot PO list with active filters and bulk selection toolbar
- [ ] Screenshot each list page at 375px (mobile) -- verify horizontal scroll on table, stacked filters
- [ ] Verify permanent Playwright tests still pass

## Acceptance criteria
- [ ] All 7 list pages use the DataTable component from iteration 049
- [ ] All 7 list pages use the Pagination component
- [ ] All 7 list pages use the FilterBar component or equivalent filter pattern
- [ ] All status values rendered using Badge component
- [ ] Sort indicators visible and functional on sortable columns
- [ ] Empty state and loading skeleton present on every list page
- [ ] PO list retains bulk actions (submit, accept, reject) and cross-page selection
- [ ] Invoice list retains bulk PDF download
- [ ] No inline table CSS remains in page files -- all table styling comes from DataTable
- [ ] All existing permanent Playwright tests pass without modification
