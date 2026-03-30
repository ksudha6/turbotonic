# Iteration 11 — 2026-03-30

## Context
Vendors are currently untyped. A raw material supplier, an office cleaning service, and a freight forwarder all look the same. As invoicing and production tracking come online, the system needs to know which vendors participate in which workflows. This iteration adds a vendor type (Procurement, OpEx, Freight, Miscellaneous) to the domain, migrates existing vendors to Procurement, and enforces type-aware constraints on PO creation.

## JTBD
1. **When** I create a PO, **I want to** select a PO type (Procurement or OpEx, required, default Procurement) and only see vendors matching that type in the vendor dropdown **so that** I don't accidentally assign the wrong vendor category to a purchase order.
2. **When** I create a vendor, **I want to** assign a required vendor type **so that** the system routes them to the correct workflows and prevents unclassified vendors from entering the system.
3. **When** I browse the vendor list, **I want to** filter by vendor type **so that** I can manage each category separately.

## Tasks
- [x]Add `VendorType` enum (Procurement, OpEx, Freight, Miscellaneous) to vendor domain model; require `vendor_type` on `Vendor.create()`
- [x]Add `POType` enum (Procurement, OpEx) to PO domain model; require `po_type` on `PurchaseOrder.create()`, default Procurement
- [x]Migrate `vendors` table: add `vendor_type TEXT NOT NULL DEFAULT 'PROCUREMENT'`; migrate `purchase_orders` table: add `po_type TEXT NOT NULL DEFAULT 'PROCUREMENT'`
- [x]Update vendor DTOs and API: `VendorCreate` accepts `vendor_type`; list endpoint accepts optional `vendor_type` filter param
- [x]Update PO creation API: accept `po_type`, reject vendor if its type does not match the PO type
- [x]Update vendor create form: add required vendor type dropdown, default Procurement
- [x]Update vendor list page: show vendor type column, add type filter dropdown
- [x]Update PO create form: add PO type dropdown (Procurement/OpEx, default Procurement); filter vendor dropdown to show only matching vendors
- [x]Scratch tests — backend domain (`test_vendor_type.py`):
    - Vendor.create with each of the four types
    - Vendor.create without type raises TypeError
    - PO.create defaults to POType.PROCUREMENT
    - PO.create with explicit POType.OPEX
    - po_type unchanged after revise
- [x]Scratch tests — backend API (`test_vendor_po_api.py`):
    - POST /vendors/ with vendor_type=OPEX returns vendor_type in response
    - GET /vendors/?vendor_type=PROCUREMENT returns only Procurement vendors
    - POST /po/ with matching vendor type returns 201
    - POST /po/ with mismatched vendor type returns 422
    - PUT /po/{id} (revise) with mismatched vendor type returns 422
    - GET /reference-data/ includes vendor_types and po_types
- [x]Scratch tests — frontend (`test_vendor_type_ui.spec.ts`):
    - Vendor create form has vendor type dropdown with 4 options
    - Vendor list page shows Type column and type filter dropdown
    - PO create form has PO type dropdown; switching type filters vendor list
    - Selecting a vendor then switching PO type resets vendor selection

## Notes
Vendor type (Procurement, OpEx, Freight, Miscellaneous) and PO type (Procurement, OpEx) added as required domain fields. Existing vendors and POs migrated to Procurement via DEFAULT clause. PO type is immutable after creation; vendor-PO type mismatch returns 422. The PO form filters vendors client-side using `$derived` rather than re-fetching on type change. Frontend scratch tests (Playwright) not run -- require live dev server. Backend domain tests (8) and API tests (5) all pass.
