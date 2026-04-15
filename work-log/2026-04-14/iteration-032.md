# Iteration 032 -- Vendor-scoped data access

## Context

Role guards (iter 031) control which endpoints a VENDOR can call, but a VENDOR user currently sees all POs and invoices across every vendor. This iteration adds a `vendor_id` FK on the `users` table and filters every list/detail query so VENDOR users see only their own POs, invoices, milestones, and activity. Non-vendor roles (SM, QUALITY_LAB, FREIGHT_MANAGER) continue to see all data within their permitted endpoints.

## JTBD (Jobs To Be Done)

- When a VENDOR user lists POs, I want to see only POs assigned to my vendor, so that I cannot access another vendor's orders
- When a VENDOR user views a specific PO, I want the system to reject the request if the PO belongs to a different vendor, so that data isolation is enforced at the API level
- When a VENDOR user lists invoices, I want to see only invoices linked to my vendor's POs, so that billing data is vendor-scoped
- When a VENDOR user lists milestones or activity, I want to see only entries related to my vendor's POs, so that production tracking is vendor-scoped
- When an SM user lists any entity, I want to see all records, so that supply managers have full visibility

## Tasks

### Note: vendor_id on users
- vendor_id column, User domain field, and VENDOR-role validation already exist from iteration 030
- No schema or domain changes needed here; this iteration only adds query-level filtering

### Repository-level filtering: PurchaseOrderRepository
- [ ] Add `vendor_id` filter parameter to `list_pos_paginated()` (already has vendor_id filter, but this is the auth-level filter, not the UI filter)
  - When VENDOR: always inject `vendor_id = current_user.vendor_id` as a WHERE clause, overriding any user-supplied vendor_id filter
  - When SM/other: no additional filter (existing vendor_id filter from query params still works)
- [ ] Add vendor_id check to `get()`: after loading PO, verify `po.vendor_id == current_user.vendor_id` for VENDOR users

### Repository-level filtering: InvoiceRepository
- [ ] Add `vendor_id` filter to `list_all()` -- join invoices -> purchase_orders to filter by PO's vendor_id
- [ ] Add vendor_id check to `get_by_id()`: load invoice, then load its PO, verify vendor_id match for VENDOR users
- [ ] Add vendor_id filter to `invoiced_quantities()` and `list_by_po()` -- verify PO belongs to vendor

### Repository-level filtering: MilestoneRepository
- [ ] Add vendor_id check to `list_by_po()` -- verify PO belongs to vendor before returning milestones

### Repository-level filtering: ActivityLogRepository
- [ ] Filter `list_recent()` for VENDOR users: only return entries where entity_id refers to a PO or invoice belonging to the vendor
  - PO activity: entity_type=PO AND entity_id in (vendor's PO ids)
  - Invoice activity: entity_type=INVOICE AND entity_id in (invoice ids linked to vendor's POs)
- [ ] Filter `unread_count()` similarly for VENDOR users
- [ ] Filter `list_for_entity()`: verify the entity belongs to the vendor

### Router changes: pass current_user to repositories
- [ ] Update `backend/src/routers/purchase_order.py`: inject current_user into list/get/detail calls
  - `list_pos`: pass `current_user.vendor_id` when role is VENDOR
  - `get_po`: after loading PO, check vendor ownership for VENDOR users (return 404 if mismatch, not 403, to avoid leaking entity existence)
  - `get_po_pdf`: same ownership check
  - `list_po_invoices`: same ownership check
  - `submit_po`, `accept_po`, `reject_po`, `update_po`, `resubmit_po`: same ownership check
  - `bulk_transition`: filter po_ids to only those belonging to vendor (skip others silently or error)
- [ ] Update `backend/src/routers/invoice.py`: inject current_user
  - `list_invoices`: pass vendor_id filter for VENDOR users
  - `get_invoice`, `get_invoice_pdf`: verify invoice's PO belongs to vendor
  - `create_invoice`: verify PO belongs to vendor
  - `submit_invoice`, `approve_invoice`, `pay_invoice`, `dispute_invoice`, `resolve_invoice`: verify invoice's PO belongs to vendor
  - `get_remaining_quantities`: verify PO belongs to vendor
  - `bulk_invoice_pdf`: filter to vendor's invoices
- [ ] Update `backend/src/routers/milestone.py`: inject current_user
  - `list_milestones`: verify PO belongs to vendor
  - `post_milestone`: verify PO belongs to vendor
- [ ] Update `backend/src/routers/activity.py`: inject current_user
  - `list_activity`: pass vendor_id for VENDOR users
  - `get_unread_count`: pass vendor_id for VENDOR users
- [ ] Update `backend/src/routers/dashboard.py`: inject current_user
  - VENDOR dashboard: filter PO summary, invoice summary, recent POs, production summary, overdue POs to vendor's data only

### Tests (permanent)
- [ ] `backend/tests/test_vendor_scoping.py`
  - Setup: two vendors (V1, V2), two VENDOR users (U1 linked to V1, U2 linked to V2), one SM user, POs for each vendor, invoices for each vendor
  - VENDOR U1 listing POs sees only V1's POs, not V2's
  - VENDOR U1 getting V2's PO by ID returns 404
  - VENDOR U1 listing invoices sees only invoices linked to V1's POs
  - VENDOR U1 getting V2's invoice by ID returns 404
  - VENDOR U1 listing milestones for V2's PO returns 404
  - VENDOR U1 activity feed contains only V1-related events
  - VENDOR U1 unread count reflects only V1-related events
  - SM user listing POs sees all POs (both V1 and V2)
  - SM user can view any PO, invoice, milestone regardless of vendor
  - VENDOR U1 cannot create invoice on V2's PO (returns 404)
  - VENDOR U1 cannot post milestone on V2's PO (returns 404)
  - VENDOR registration without vendor_id returns 422
  - SM registration with vendor_id returns 422
  - VENDOR registration with nonexistent vendor_id returns 422

### Tests (scratch)
- [ ] Log in as two different VENDOR users, compare PO list responses to verify disjoint sets

## Acceptance criteria
- [ ] Users table has vendor_id column (nullable FK to vendors)
- [ ] VENDOR users must have a vendor_id; SM/QUALITY_LAB/FREIGHT_MANAGER must not
- [ ] VENDOR user listing POs sees only POs where `purchase_orders.vendor_id = user.vendor_id`
- [ ] VENDOR user accessing another vendor's PO by ID gets 404 (not 403)
- [ ] VENDOR user listing invoices sees only invoices linked to their vendor's POs
- [ ] VENDOR user accessing another vendor's invoice by ID gets 404
- [ ] VENDOR user activity feed and unread count reflect only their vendor's entities
- [ ] VENDOR user dashboard data is scoped to their vendor
- [ ] SM user sees all data across all vendors (no filtering)
- [ ] QUALITY_LAB and FREIGHT_MANAGER see all data within their role's allowed endpoints
- [ ] Vendor ownership checks use 404 (not 403) to avoid leaking entity existence
- [ ] `make test` passes with all new and existing tests
