# Iteration 036 -- Existing model extensions

## Context

PurchaseOrder, LineItem, Vendor, and Product lack fields needed by downstream features: PO has no `marketplace`, LineItem has no `product_id` FK, Vendor has no `address`/`account_details`, and Product has no `manufacturing_address`. This iteration adds those five columns (all nullable or defaulted) across domain models, DTOs, repositories, routers, and frontend forms. Quality gates, certification lookups, and shipping documents all depend on these fields.

## JTBD (Jobs To Be Done)

- When I create a PO, I want to specify which marketplace it targets (e.g. AMAZON, DIRECT), so that the system can determine what packaging and certification requirements apply
- When I add a line item to a PO, I want to link it to a product in the catalog, so that the system can check that product's certifications and packaging specs
- When I view a vendor, I want to see their address and bank/payment details, so that shipping and export documents can reference them
- When I view a product, I want to see its manufacturing address, so that certificates of origin and compliance documents reference the correct location

## Tasks

### Domain model changes

#### `backend/src/domain/purchase_order.py`
- [x] Add `marketplace: str | None` field to `PurchaseOrder.__init__` (after `country_of_destination`). Valid values: AMZ, 3PL_1, 3PL_2, 3PL_3. Treat as reference data (add to reference data module).
- [x] Add `marketplace` parameter to `PurchaseOrder.create()` with default `None`. Validate against marketplace reference data if provided.
- [x] Add `marketplace` parameter to `PurchaseOrder.revise()` and update it on the instance
- [x] Add `product_id: str | None = None` field to `LineItem` dataclass

#### `backend/src/domain/vendor.py`
- [x] Add `address: str` and `account_details: str` fields to `Vendor.__init__` (default `""`)
- [x] Add `address` and `account_details` parameters to `Vendor.create()` with default `""`

#### `backend/src/domain/product.py`
- [x] Add `manufacturing_address: str` field to `Product.__init__` (default `""`)
- [x] Add `manufacturing_address` parameter to `Product.create()` with default `""`
- [x] Add `manufacturing_address` to `Product.update()` as optional parameter

### Schema migration

#### `backend/src/schema.py`
- [x] Add `marketplace` column to `purchase_orders` table (TEXT, nullable, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`)
- [x] Add `product_id` column to `line_items` table (TEXT, nullable, FK to `products(id)`)
- [x] Add `address` column to `vendors` table (TEXT NOT NULL DEFAULT '', `ADD COLUMN IF NOT EXISTS`)
- [x] Add `account_details` column to `vendors` table (TEXT NOT NULL DEFAULT '', `ADD COLUMN IF NOT EXISTS`)
- [x] Add `manufacturing_address` column to `products` table (TEXT NOT NULL DEFAULT '', `ADD COLUMN IF NOT EXISTS`)

### DTO changes

#### `backend/src/dto.py` (PO DTOs)
- [x] Add `marketplace: str | None = None` to `PurchaseOrderCreate`
- [x] Add `marketplace: str | None = None` to `PurchaseOrderUpdate`
- [x] Add `marketplace: str | None = None` to `PurchaseOrderResponse`
- [x] Add `marketplace: str | None = None` to `PurchaseOrderListItem`
- [x] Add `product_id: str | None = None` to `LineItemCreate`
- [x] Add `product_id: str | None = None` to `LineItemResponse`
- [x] Update `po_to_response()` to include `marketplace`
- [x] Update `po_to_list_item()` to include `marketplace`
- [x] Update `_line_item_to_response()` to include `product_id`

#### `backend/src/vendor_dto.py`
- [x] Add `address: str = ""` and `account_details: str = ""` to `VendorCreate`
- [x] Add `address: str | None = None` and `account_details: str | None = None` to a new `VendorUpdate` model (or extend existing pattern)
- [x] Add `address: str` and `account_details: str` to `VendorResponse`
- [x] Add `address: str` and `account_details: str` to `VendorListItem`
- [x] Update `vendor_to_response()` and `vendor_to_list_item()` to include new fields

#### `backend/src/product_dto.py`
- [x] Add `manufacturing_address: str = ""` to `ProductCreate`
- [x] Add `manufacturing_address: str | None = None` to `ProductUpdate`
- [x] Add `manufacturing_address: str` to `ProductResponse`
- [x] Add `manufacturing_address: str` to `ProductListItem`
- [x] Update `product_to_response()` and `product_to_list_item()` to include `manufacturing_address`

### Repository changes

#### `backend/src/repository.py` (PO repository)
- [x] Update `save()` INSERT to include `marketplace`
- [x] Update `save()` UPDATE to include `marketplace`
- [x] Update line_items INSERT to include `product_id`
- [x] Update `_reconstruct()` to read `marketplace` from PO row
- [x] Update `_reconstruct()` to read `product_id` from line item rows and pass to `LineItem`
- [x] Update `list_pos_paginated()` base query SELECT to include `p.marketplace`

#### `backend/src/vendor_repository.py`
- [x] Update `save()` INSERT to include `address`, `account_details`
- [x] Update `save()` UPDATE to include `address`, `account_details`
- [x] Update `_reconstruct()` to read `address`, `account_details`

#### `backend/src/product_repository.py`
- [x] Update `save()` INSERT to include `manufacturing_address`
- [x] Update `save()` UPDATE to include `manufacturing_address`
- [x] Update `_reconstruct()` to read `manufacturing_address`

### Router changes

#### `backend/src/routers/purchase_order.py`
- [x] Pass `marketplace` to `PurchaseOrder.create()` in `create_po()`
- [x] Pass `marketplace` to `PurchaseOrder.revise()` in `update_po()`
- [x] Update `_build_line_items()` to include `product_id` from `LineItemCreate`
- [x] Update `list_pos()` item construction to include `marketplace`

#### `backend/src/routers/vendor.py`
- [x] Pass `address`, `account_details` to `Vendor.create()` in create endpoint
- [x] Handle `address`, `account_details` in update/patch endpoint if one exists

#### `backend/src/routers/product.py`
- [x] Pass `manufacturing_address` to `Product.create()` in `create_product()`
- [x] Pass `manufacturing_address` to `Product.update()` in `update_product()`

### Frontend changes

#### `frontend/src/lib/types.ts`
- [x] Add `marketplace: string | null` to `PurchaseOrderListItem`, `PurchaseOrder`, `PurchaseOrderInput`
- [x] Add `product_id: string | null` to `LineItem`, `LineItemInput`
- [x] Add `address: string` and `account_details: string` to `Vendor`, `VendorListItem`, `VendorInput`
- [x] Add `manufacturing_address: string` to `Product`, `ProductListItem`, `ProductInput`

#### `frontend/src/lib/components/POForm.svelte`
- [x] Add marketplace dropdown (text input or select with common values: AMAZON, DIRECT)
- [x] Add optional product_id select per line item (populated from product catalog filtered by selected vendor)
- [x] Update `InitialData` interface to include `marketplace`

#### `frontend/src/routes/po/new/+page.svelte`
- [x] Pass marketplace through to API call

#### `frontend/src/routes/po/[id]/edit/+page.svelte`
- [x] Load and display marketplace; pass through on save

#### `frontend/src/routes/po/[id]/+page.svelte`
- [x] Display marketplace in PO detail header

#### `frontend/src/routes/vendors/new/+page.svelte`
- [x] Add address textarea field
- [x] Add account_details textarea field

#### `frontend/src/routes/vendors/+page.svelte`
- [x] Display address column (or in an expandable row) in vendor list

#### `frontend/src/routes/products/new/+page.svelte`
- [x] Add manufacturing_address textarea field

#### `frontend/src/routes/products/[id]/edit/+page.svelte`
- [x] Load and display manufacturing_address; include in update payload

#### `frontend/src/routes/products/+page.svelte`
- [x] Display manufacturing_address in product list (column or detail view)

#### `frontend/src/lib/api.ts`
- [x] Update any API call signatures if needed (fields are passed through existing create/update payloads, so likely no changes needed beyond types)

### PDF generation
#### `backend/src/services/po_pdf.py`
- [x] Add marketplace to PO PDF output if present (in header section)

### Tests (permanent)
- [x] `backend/tests/test_purchase_order.py` -- PO create with marketplace, revise updates marketplace, LineItem with product_id, reject invalid marketplace value
- [x] `backend/tests/test_api_purchase_order.py` -- create PO with marketplace, verify in response; create with product_id on line item; invalid marketplace returns 400; product_id from wrong vendor returns 400; marketplace in PO list response; marketplace filter on PO list
- [x] Vendor tests: create with address/account_details, verify in response; update address/account_details; backward compat (create without new fields uses defaults)
- [x] Product tests: create with manufacturing_address, update manufacturing_address; backward compat (create without new field uses default)
- [x] PDF test: PO PDF includes marketplace when present

### Tests (scratch)
- [x] Screenshot: PO create form showing marketplace dropdown
- [x] Screenshot: vendor create form showing address and account_details fields
- [x] Screenshot: product create form showing manufacturing_address field
- [x] Screenshot: PO detail page showing marketplace value

## Acceptance criteria
- [x] PO create/update accepts and persists `marketplace`; PO list and detail responses include it
- [x] LineItem create accepts and persists `product_id`; PO response line items include it
- [x] Vendor create accepts and persists `address` and `account_details`; responses include them
- [x] Product create/update accepts and persists `manufacturing_address`; responses include it
- [x] All existing tests still pass (backward compatibility: new fields are nullable or defaulted)
- [x] Frontend forms include new fields
- [x] All permanent tests pass via `make test`

## Files modified (complete list)

### Backend
- `backend/src/domain/purchase_order.py` -- marketplace on PO, product_id on LineItem
- `backend/src/domain/vendor.py` -- address, account_details
- `backend/src/domain/product.py` -- manufacturing_address
- `backend/src/schema.py` -- ALTER TABLE for all 5 new columns
- `backend/src/dto.py` -- PO and line item DTOs
- `backend/src/vendor_dto.py` -- vendor DTOs
- `backend/src/product_dto.py` -- product DTOs
- `backend/src/repository.py` -- PO repository save/reconstruct
- `backend/src/vendor_repository.py` -- vendor save/reconstruct
- `backend/src/product_repository.py` -- product save/reconstruct
- `backend/src/routers/purchase_order.py` -- pass marketplace, product_id
- `backend/src/routers/vendor.py` -- pass address, account_details
- `backend/src/routers/product.py` -- pass manufacturing_address
- `backend/src/services/po_pdf.py` -- marketplace in PDF

### Frontend
- `frontend/src/lib/types.ts` -- all type additions
- `frontend/src/lib/api.ts` -- type pass-through (if needed)
- `frontend/src/lib/components/POForm.svelte` -- marketplace dropdown, product_id per line item
- `frontend/src/routes/po/new/+page.svelte` -- marketplace pass-through
- `frontend/src/routes/po/[id]/edit/+page.svelte` -- marketplace load/save
- `frontend/src/routes/po/[id]/+page.svelte` -- marketplace display
- `frontend/src/routes/vendors/new/+page.svelte` -- address, account_details fields
- `frontend/src/routes/vendors/+page.svelte` -- display new vendor fields
- `frontend/src/routes/products/new/+page.svelte` -- manufacturing_address field
- `frontend/src/routes/products/[id]/edit/+page.svelte` -- manufacturing_address load/save
- `frontend/src/routes/products/+page.svelte` -- manufacturing_address display

### Tests
- `backend/tests/test_purchase_order.py`
- `backend/tests/test_api_purchase_order.py`

## Notes

All five new columns use ALTER TABLE ADD COLUMN IF NOT EXISTS with nullable or default values, so existing rows are unaffected. Marketplace validation uses reference data (AMZ, 3PL_1, 3PL_2, 3PL_3) at the domain level. product_id on LineItem is a loose FK with no cross-vendor validation in this iteration. Vendor address and account_details are free-text fields. Frontend forms add the fields inline with existing layouts. PO list endpoint accepts marketplace as an optional filter parameter.
