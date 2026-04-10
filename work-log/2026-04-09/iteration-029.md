# Iteration 29 — Product master

## Context

SKUs exist only as free-text `part_number` on line items. With quality certificates, shipments, and customs coming, we need a proper `Product` entity to hang attributes off. This iteration introduces a product master table scoped to vendor/part_number pairs, with `requires_certification` as the first attribute. Line items continue to embed their own prices and quantities (those vary per PO), but product-level attributes live on the master.

**User model note:** Products are scoped to a vendor. When roles are introduced, vendor users will manage their own product catalog. Another surface that needs future role separation.

## JTBD

1. **When** I create a PO with line items, **I want** part numbers to reference a known product catalog **so that** product-level attributes (like certification requirements) are consistent across POs.
2. **When** I manage my product catalog, **I want to** add, view, and update products **so that** the system knows which SKUs exist and what attributes they carry.
3. **When** a product requires certification, **I want** that flag stored on the product (not per PO) **so that** every PO referencing that SKU inherits the requirement.

## Acceptance Criteria

### Domain model
1. New entity `Product` with fields: `id`, `vendor_id`, `part_number`, `description`, `requires_certification` (bool, default false).
2. `vendor_id` + `part_number` is unique (a vendor cannot have duplicate SKUs).
3. `Product.create()` validates: part_number non-empty, vendor_id non-empty.

### Schema
4. New `products` table: `id TEXT PK`, `vendor_id TEXT NOT NULL`, `part_number TEXT NOT NULL`, `description TEXT`, `requires_certification INTEGER NOT NULL DEFAULT 0`, `created_at TEXT NOT NULL`.
5. Unique constraint on `(vendor_id, part_number)`.

### API
6. `POST /api/v1/products/` — create a product.
7. `GET /api/v1/products/` — list products, filterable by `vendor_id`.
8. `GET /api/v1/products/{id}` — get a single product.
9. `PATCH /api/v1/products/{id}` — update product attributes (description, requires_certification).

### Frontend
10. Products list page (table: part number, description, vendor, requires cert).
11. Add product form.
12. Edit product (inline or detail page).
13. Navigation entry for products.

### Integration
14. PO detail line items show `requires_certification` from the product master (read-only, not editable on the PO).

## Tasks

### Backend — Schema
- [x] Create `products` table migration
- [x] Unique constraint on (vendor_id, part_number)

### Backend — Domain
- [x] `Product` dataclass with create/update validation
- [x] `requires_certification` field

### Backend — Repository
- [x] `ProductRepository`: save, get_by_id, list (with vendor_id filter), get_by_vendor_and_part_number
- [x] Handle unique constraint violation (return 409)

### Backend — API
- [x] `POST /api/v1/products/`
- [x] `GET /api/v1/products/`
- [x] `GET /api/v1/products/{id}`
- [x] `PATCH /api/v1/products/{id}`

### Frontend
- [x] Products list page
- [x] Add product form
- [x] Edit product
- [x] Nav entry for products
- [x] PO detail: show requires_certification from product master on line items

### Tests (permanent backend)
- [x] Create product, retrieve, verify fields
- [x] Duplicate vendor_id + part_number returns 409
- [x] Update requires_certification
- [x] List products filtered by vendor_id
- [x] Empty/whitespace part_number rejected

### Tests (scratch)
- [x] Screenshot: products list page
- [x] Screenshot: add/edit product form
