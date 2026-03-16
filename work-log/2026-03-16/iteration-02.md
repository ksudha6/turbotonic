# Iteration 02 — 2026-03-16

## Context

We are going to add purchase orders. Users will interact with purchase orders at /po. 

## Jobs to Be Done

1. **When** I create a purchase order, **I want to** capture the header, trade details, and at least one line item, **so that** the system holds a complete, valid PO in Draft status.

2. **When** I submit a Draft PO, **I want to** transition it to Pending, **so that** the assigned vendor can review and act on it.

3. **When** a vendor reviews a Pending or Revised PO, **I want to** accept or reject it, **so that** the PO moves to its next lifecycle state. Rejection requires a non-empty comment.

4. **When** a PO is rejected, **I want to** update its fields and resubmit it, **so that** the vendor can review the changes. Previous rejection comments are preserved as history.

5. **When** I persist a PO, **I want to** store the full aggregate in SQLite, **so that** POs survive restarts and can be queried.

6. **When** I want to review past POs, **I want to** list and filter them by status, **so that** I can find accepted, rejected, or in-progress orders.

## Acceptance Criteria

### 1. Create PO
- PO is created in Draft status
- Must have at least one line item
- Line item quantity > 0, unit price >= 0
- PO number is system-generated and unique
- All header and trade fields are captured

### 2. Submit Draft PO
- Only Draft POs can be submitted
- Status transitions to Pending
- Submitting a non-Draft PO is rejected

### 3. Accept or Reject
- Vendor can only act on Pending or Revised POs
- Accept transitions to Accepted (terminal)
- Reject transitions to Rejected, requires non-empty comment
- Empty or whitespace-only comment is rejected
- Once Accepted or Rejected, no further action is possible on that status

### 4. Revise and Resubmit
- Only Rejected POs can be revised
- Revised PO moves to Revised, then resubmitted to Pending
- Previous rejection comments are preserved in history
- A PO can cycle through Rejected → Revised → Pending multiple times

### 5. Persistence
- Full aggregate (header, trade, line items, status, rejection history) is stored in SQLite
- Data survives restart

### 6. List and Filter
- POs can be listed with filter by status
- Returns PO header fields (not full line items)

## Tasks

### Backend — Domain Model
- [x]Define PO status enum (Draft, Pending, Accepted, Rejected, Revised)
- [x]Define LineItem value object (part number, description, quantity, UoM, unit price, HS code, country of origin)
- [x]Define PurchaseOrder aggregate root (header, trade fields, line items, status, rejection history)
- [x]Implement status transition methods (submit, accept, reject, revise)
- [x]Enforce invariants: at least one line item, quantity > 0, unit price >= 0, rejection requires non-empty comment
- [x]Enforce transition guards: only valid status transitions allowed

### Backend — Persistence
- [x]Create `purchase_orders` table schema (header + trade fields + status + timestamps)
- [x]Create `po_line_items` table schema
- [x]Create `po_rejection_history` table schema
- [x]Implement PO repository: create, get by ID, list with status filter, update
- [x]Wire schema migration into app startup

### Backend — API
- [x]POST `/api/v1/po` — create PO (returns Draft)
- [x]POST `/api/v1/po/{id}/submit` — Draft → Pending
- [x]POST `/api/v1/po/{id}/accept` — Pending/Revised → Accepted
- [x]POST `/api/v1/po/{id}/reject` — Pending/Revised → Rejected (with comment)
- [x]PUT `/api/v1/po/{id}` — update Rejected PO fields (triggers Revised)
- [x]POST `/api/v1/po/{id}/resubmit` — Revised → Pending
- [x]GET `/api/v1/po` — list POs, optional status filter
- [x]GET `/api/v1/po/{id}` — get PO detail with line items and rejection history

### Frontend — PO List View (`/po`)
- [x]Data table: PO Number, Vendor, Issued Date, Required Delivery Date, Total Value, Status
- [x]Status pills with color coding (Draft=gray, Pending=amber, Accepted=green, Rejected=red, Revised=blue)
- [x]Status filter dropdown
- [x]"New PO" button
- [x]Row click navigates to detail view

### Frontend — PO Detail View (`/po/:id`)
- [x]Header card: PO number, status pill, vendor, dates, currency, total value
- [x]Trade details section: incoterm, ports, countries
- [x]Terms and conditions section
- [x]Line items table
- [x]Rejection history section
- [x]Action bar: Edit/Submit (Draft), Accept/Reject (Pending/Revised), read-only (Accepted/Rejected)

### Frontend — Create/Edit PO (`/po/new`, `/po/:id/edit`)
- [x]Form with header, trade, and terms sections
- [x]Dynamic line item rows (add/remove)
- [x]Inline validation (quantity > 0, unit price >= 0, at least one line item)
- [x]Submit creates Draft or updates Rejected PO

### Frontend — Styling
- [x]Hand-written CSS, Tailwind-inspired spacing and color palette
- [x]Card-based layout, clean borders, status-colored pills
- [x]Rejection modal with required comment field

### Permanent Tests — Backend (`backend/tests/`)
- [x]PO created in Draft status with valid line items
- [x]Reject PO creation with zero line items
- [x]Reject line item with quantity <= 0
- [x]Reject line item with unit price < 0
- [x]Submit Draft → Pending
- [x]Reject submit on non-Draft PO (Pending, Accepted, Rejected, Revised)
- [x]Accept Pending → Accepted
- [x]Accept Revised → Accepted
- [x]Reject Pending → Rejected with comment
- [x]Reject Revised → Rejected with comment
- [x]Reject with empty/whitespace comment fails
- [x]No action allowed on Accepted PO
- [x]Revise Rejected → Revised
- [x]Resubmit Revised → Pending
- [x]Rejection history preserved across multiple reject/revise cycles
- [x]API: POST create returns Draft with generated PO number
- [x]API: GET list returns POs filtered by status
- [x]API: GET detail returns full aggregate with line items and rejection history
- [x]API: invalid transitions return 409
- [x]Persistence: PO survives app restart (create, stop, reload, fetch)

### Permanent Tests — Frontend (`frontend/tests/`)
- [x]PO list view loads and displays PO table
- [x]Status filter narrows displayed POs
- [x]Click row navigates to detail view
- [x]Detail view shows header, trade, line items, status pill
- [x]Detail view shows rejection history when present
- [x]Draft PO shows Edit and Submit buttons
- [x]Pending PO shows Accept and Reject buttons
- [x]Accepted PO shows read-only view, no action buttons
- [x]Create PO form validates at least one line item
- [x]Create PO form rejects quantity <= 0 and unit price < 0
- [x]Reject modal requires non-empty comment before submit
- [x]Full cycle: create → submit → reject with comment → revise → resubmit → accept

### Scratch Tests (`frontend/tests/scratch/iteration-02/`)
- [x]Screenshot: PO list view with mixed statuses
- [x]Screenshot: PO detail view in Draft status
- [x]Screenshot: PO detail view in Pending status with action buttons
- [x]Screenshot: PO detail view in Accepted status (read-only)
- [x]Screenshot: PO detail view in Rejected status with rejection history
- [x]Screenshot: Create PO form with line items
- [x]Screenshot: Reject modal with comment field

## Notes

PO aggregate follows a confirmation workflow: created in Draft, submitted to vendor, then accepted or rejected. Rejection requires a comment, preserved as append-only history across reject/revise cycles. The portal creates POs directly (no ERP), so all fields are mutable in Draft and Rejected states. Compliance fields (LC, export license, packing list, bill of lading) were deferred. Roles and permissions were deferred. Field-level mutability rules tied to lifecycle status were deferred. PO number uses a sequential-per-day format (PO-YYYYMMDD-XXXX) generated by the repository.
