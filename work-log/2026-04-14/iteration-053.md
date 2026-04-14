# Iteration 053 -- Detail pages redesign

## Context

PO and invoice detail pages use inline CSS for headers, info grids, and action bars, while vendor and product have no dedicated detail pages at all. This iteration introduces a shared DetailLayout (header + InfoGrid + Tabs + actions) and applies it to all six detail pages, creating new ones for vendor, product, certificate, and shipment. It eliminates all inline `.detail-header`, `.info-grid`, and `.actions` CSS.

## JTBD (Jobs To Be Done)

- When viewing any entity's detail page, I want a consistent layout (header, info grid, tabbed sections), so that I learn the UI pattern once and apply it everywhere.
- When I need to take action on an entity (submit, approve, reject), I want context-sensitive action buttons clearly placed, so that I know what I can do.
- When viewing a complex entity like a PO, I want tabbed sections to organize line items, invoices, milestones, and activity, so that I'm not overwhelmed by a long scrolling page.
- When reviewing the history of an entity, I want a timeline of events, so that I can trace what happened and when.

## Tasks

### Detail layout component (`frontend/src/lib/components/DetailLayout.svelte`)
- [ ] Slots: `header`, `info`, `tabs`, `actions`
- [ ] Header zone: entity identifier (large text), status badge (right-aligned), primary action buttons
- [ ] Info zone: key-value grid (2 columns on desktop, 1 on mobile)
- [ ] Tabs zone: Tabs component with content panels
- [ ] Actions zone: fixed at bottom or inline with header
- [ ] PDF download button placement: secondary action in header

### InfoGrid component (`frontend/src/lib/components/InfoGrid.svelte`)
- [ ] Props: `items` (array of `{label, value}`)
- [ ] Renders label/value pairs in a responsive 2-3 column grid
- [ ] Replaces inline `.info-grid`, `.info-item`, `.field-label`, `.value` patterns

### PO detail page (`routes/po/[id]/+page.svelte`)
- [ ] Header: PO number (h1), status Badge, type Badge (Procurement/OpEx)
- [ ] Info grid:
  - Vendor: name (link to vendor detail)
  - Buyer: name, country
  - Currency, Issued Date, Delivery Date, Total Value, Payment Terms
- [ ] Tabs:

| Tab | Contents |
|-----|----------|
| Details | Trade details (incoterm, ports, countries), ship-to address, terms & conditions |
| Line Items | DataTable with part number, description, qty, invoiced, remaining, UoM, unit price, HS code, origin, cert status |
| Invoices | DataTable of linked invoices (invoice #, status, subtotal, created) with links to invoice detail |
| Milestones | MilestoneTimeline component (for accepted Procurement POs) |
| Activity | ActivityTimeline component |

- [ ] Actions (context-sensitive by status):
  - DRAFT: Edit, Submit, Download PDF
  - PENDING: Accept, Reject, Download PDF
  - REJECTED: Edit, Download PDF
  - REVISED: Resubmit, Download PDF
  - ACCEPTED: Create Invoice, Download PDF
- [ ] Reject action opens Modal with comment textarea
- [ ] Create Invoice action opens Modal with remaining quantities table

### Invoice detail page (`routes/invoice/[id]/+page.svelte`)
- [ ] Header: Invoice number (h1), status Badge
- [ ] Info grid:
  - PO: PO number (link to PO detail)
  - Vendor: name
  - Currency, Payment Terms, Subtotal, Created Date
- [ ] Tabs:

| Tab | Contents |
|-----|----------|
| Line Items | DataTable with part number, description, qty, UoM, unit price |
| Activity | ActivityTimeline component |

- [ ] Dispute reason: shown as an alert/banner above tabs when status is DISPUTED
- [ ] Actions (context-sensitive by status):
  - DRAFT: Submit, Download PDF
  - SUBMITTED: Approve, Dispute, Download PDF
  - APPROVED: Pay, Download PDF
  - DISPUTED: Resolve, Download PDF
  - PAID: Download PDF
- [ ] Dispute action opens Modal with reason textarea

### Vendor detail page (`routes/vendors/[id]/+page.svelte`) -- new page
- [ ] Currently there is no vendor detail page; the vendor list has inline deactivate/reactivate buttons
- [ ] Header: Vendor name (h1), status Badge (Active/Inactive), type Badge
- [ ] Info grid:
  - Country, Address, Account Details, Created Date
- [ ] Tabs:

| Tab | Contents |
|-----|----------|
| Purchase Orders | DataTable of POs for this vendor (PO#, status, total, dates) |
| Products | DataTable of products for this vendor (part number, description, cert required) |
| Invoices | DataTable of invoices for POs from this vendor |

- [ ] Actions: Deactivate (if active), Reactivate (if inactive), Edit (future)

### Product detail page (`routes/products/[id]/+page.svelte`) -- new page
- [ ] Currently there is no product detail page; only an edit page
- [ ] Header: Part number (h1), vendor name subtitle, cert required Badge
- [ ] Info grid:
  - Vendor (link), Description, Manufacturing Address, Created Date
- [ ] Tabs:

| Tab | Contents |
|-----|----------|
| Qualifications | List of qualification types assigned to this product, with certificate status per qualification |
| Certificates | DataTable of certificates for this product (cert #, type, status, issuer, dates) |
| Packaging | DataTable of packaging specs for this product (spec name, marketplace, status) |

- [ ] Actions: Edit

### Certificate detail page (`routes/certificates/[id]/+page.svelte`) -- new in Phase 3
- [ ] Header: Certificate number (h1), status Badge (Valid/Pending/Expired)
- [ ] Info grid:
  - Product (link), Qualification Type, Issuer, Testing Lab
  - Test Date, Issue Date, Expiry Date (highlighted if expired or expiring within 30 days)
  - Target Market, Document (download link)
- [ ] Tabs:

| Tab | Contents |
|-----|----------|
| Details | Full certificate information |
| Activity | Certificate-related activity events |

- [ ] Actions: Download Document, Update (re-upload)

### Shipment detail page (`routes/shipments/[id]/+page.svelte`) -- new in Phase 3
- [ ] Header: Shipment number (h1), status Badge (Draft/Documents Pending/Ready to Ship), marketplace Badge
- [ ] Info grid:
  - PO (link to PO detail), PO Number, Marketplace
  - Created Date
- [ ] Tabs:

| Tab | Contents |
|-----|----------|
| Line Items | DataTable: description, quantity, net weight, gross weight, package count, dimensions, country of origin |
| Documents | Document checklist with status per document (generated/uploaded/missing), download links, upload buttons |
| Quality | Certificate status per product in shipment (valid/missing/expired) |
| Packaging | Packaging file status per product (collected/missing) |
| Readiness | Combined readiness gate: documents + certificates + packaging -- all-green = ready to ship |
| Activity | Shipment-related activity events |

- [ ] Actions (context-sensitive by status):
  - DRAFT: Edit line items, transition to Documents Pending
  - DOCUMENTS_PENDING: Upload documents, generate packing list PDF, generate export CI PDF
  - READY_TO_SHIP: Download all documents

### Tests (scratch)
- [ ] Screenshot PO detail at 1280px: each tab visible, with action buttons for DRAFT, PENDING, ACCEPTED statuses
- [ ] Screenshot invoice detail at 1280px: each tab, with actions for SUBMITTED and DISPUTED statuses
- [ ] Screenshot vendor detail at 1280px: each tab
- [ ] Screenshot product detail at 1280px: each tab
- [ ] Screenshot certificate detail at 1280px: expired certificate highlighting
- [ ] Screenshot shipment detail at 1280px: readiness tab showing green/red indicators
- [ ] Screenshot PO detail at 375px (mobile): tabs navigation, info grid stacked
- [ ] Verify permanent Playwright tests still pass

## Acceptance criteria
- [ ] All 6 detail pages use DetailLayout component
- [ ] All info grids use InfoGrid component
- [ ] All tabbed sections use Tabs component from iteration 049
- [ ] All tables within detail pages use DataTable component
- [ ] All status values rendered with Badge component
- [ ] All action buttons use Button component
- [ ] All dialogs (reject, dispute, create invoice) use Modal component
- [ ] Vendor detail page exists at `/vendors/[id]` (new)
- [ ] Product detail page exists at `/products/[id]` (new, separate from edit)
- [ ] Info grids responsive: 2 columns on desktop, 1 column on mobile
- [ ] No inline `.detail-header`, `.info-grid`, `.info-item`, `.actions` CSS in page files
- [ ] All existing permanent Playwright tests pass without modification
