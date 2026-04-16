# Iteration 036a -- Export qualification type entity

## Context

Product has a boolean `requires_certification` flag, which is too coarse to distinguish between market-specific qualifications (CPC, CE, EN 71, etc.). This iteration replaces it with a `QualificationType` aggregate and a `product_qualifications` many-to-many join, migrating existing `requires_certification=true` products to a "QUALITY_CERTIFICATE" qualification. The certificate entity (iteration 038) will reference these qualification types to record what has been obtained.

## JTBD (Jobs To Be Done)

- When I manage a product's export requirements, I want to assign specific qualification types (e.g. "CPC - CPSIA", "CE - EN 71"), so that the system knows exactly which certifications are needed per target market
- When I define a new qualification type, I want to specify its name, description, target market, and applicable product category, so that I can reuse it across multiple products
- When I view a product, I want to see its list of required qualifications instead of just a boolean flag, so that I know precisely what certificates are needed

## Tasks

### Domain model

#### Create `backend/src/domain/qualification_type.py`
- [ ] `QualificationType` class:
  - Fields: id, name, description, target_market, applies_to_category, created_at
  - `id`: UUID string
  - `name`: str, non-empty, non-whitespace (e.g. "CPC - CPSIA", "CE - EN 71")
  - `description`: str, default ""
  - `target_market`: str (e.g. "US", "EU", "ALL"). The market this qualification applies to.
  - `applies_to_category`: str, default "" (e.g. "CHILDREN", "ELECTRONICS", "FOOD_CONTACT"). Optional filter.
  - `created_at`: datetime
- [ ] `QualificationType.create(name, description, target_market, applies_to_category) -> QualificationType`
  - Validate: name not empty/whitespace, target_market not empty/whitespace

#### Modify `backend/src/domain/product.py`
- [ ] Remove `requires_certification` from `Product.__init__`, `Product.create()`, `Product.update()`
- [ ] The product's qualifications are managed via the join table, not on the Product aggregate itself. Product does not hold a list of qualifications in memory.

### Schema

#### `backend/src/schema.py`
- [ ] Add `qualification_types` table:
  ```
  qualification_types (
      id                    TEXT PRIMARY KEY,
      name                  TEXT UNIQUE NOT NULL,
      description           TEXT NOT NULL DEFAULT '',
      target_market         TEXT NOT NULL,
      applies_to_category   TEXT NOT NULL DEFAULT '',
      created_at            TEXT NOT NULL
  )
  ```
- [ ] Add `product_qualifications` join table:
  ```
  product_qualifications (
      product_id            TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
      qualification_type_id TEXT NOT NULL REFERENCES qualification_types(id),
      PRIMARY KEY (product_id, qualification_type_id)
  )
  ```
- [ ] Migration: for products with `requires_certification = 1`:
  1. Create a "QUALITY_CERTIFICATE" qualification type if it doesn't exist (target_market = "ALL")
  2. Insert rows into `product_qualifications` linking those products to it
  - The `requires_certification` column stays in the DB but is no longer read by the application

### DTOs

#### Create `backend/src/qualification_type_dto.py`
- [ ] `QualificationTypeCreate(BaseModel)`: name, description (default ""), target_market, applies_to_category (default "")
  - Validators: name not empty, target_market not empty
- [ ] `QualificationTypeUpdate(BaseModel)`: name (optional), description (optional), target_market (optional), applies_to_category (optional)
- [ ] `QualificationTypeResponse(BaseModel)`: id, name, description, target_market, applies_to_category, created_at
- [ ] `QualificationTypeListItem(BaseModel)`: id, name, target_market, applies_to_category
- [ ] Converter functions: `qualification_type_to_response()`, `qualification_type_to_list_item()`

#### Modify `backend/src/product_dto.py`
- [ ] Remove `requires_certification` from `ProductCreate`, `ProductUpdate`, `ProductResponse`, `ProductListItem`
- [ ] Add `qualifications: list[QualificationTypeListItem]` to `ProductResponse`
- [ ] Add `qualifications: list[QualificationTypeListItem]` to `ProductListItem`
- [ ] Update `product_to_response()` to accept and include qualifications list
- [ ] Update `product_to_list_item()` to accept and include qualifications list

### Repository

#### Create `backend/src/qualification_type_repository.py`
- [ ] `QualificationTypeRepository.__init__(conn)`
- [ ] `save(qt: QualificationType) -> None` -- upsert (INSERT or UPDATE)
- [ ] `get_by_id(qt_id: str) -> QualificationType | None`
- [ ] `get_by_name(name: str) -> QualificationType | None`
- [ ] `list_all() -> list[QualificationType]`
- [ ] `delete(qt_id: str) -> bool` -- delete if no products reference it; raise ValueError if in use
- [ ] `list_by_product(product_id: str) -> list[QualificationType]` -- join query
- [ ] `assign_to_product(product_id: str, qualification_type_id: str) -> None` -- INSERT into product_qualifications (ignore if exists)
- [ ] `remove_from_product(product_id: str, qualification_type_id: str) -> None` -- DELETE from product_qualifications

#### Modify `backend/src/product_repository.py`
- [ ] Remove `requires_certification` from `save()` INSERT and UPDATE
- [ ] Remove `requires_certification` from `_reconstruct()`
- [ ] No need to load qualifications here; the router will fetch them separately via QualificationTypeRepository

### Router

#### Create `backend/src/routers/qualification_type.py`
- [ ] `POST /api/v1/qualification-types` -- create qualification type. Returns QualificationTypeResponse, 201. Role: SM only. 409 on duplicate name.
- [ ] `GET /api/v1/qualification-types` -- list all. Returns list[QualificationTypeListItem]. Role: SM only.
- [ ] `GET /api/v1/qualification-types/{qt_id}` -- get by id. Returns QualificationTypeResponse. 404 if not found. Role: SM only.
- [ ] `PATCH /api/v1/qualification-types/{qt_id}` -- update fields. Returns QualificationTypeResponse. 404 if not found. Role: SM only.
- [ ] `DELETE /api/v1/qualification-types/{qt_id}` -- delete. Returns 204. 404 if not found. 409 if in use by products. Role: SM only.
- [ ] `POST /api/v1/products/{product_id}/qualifications` -- body: `{ qualification_type_id: str }`. Assigns qualification to product. 201.
- [ ] `DELETE /api/v1/products/{product_id}/qualifications/{qt_id}` -- removes qualification from product. 204.
- [ ] `GET /api/v1/products/{product_id}/qualifications` -- list qualifications for product. Returns list[QualificationTypeListItem].
- [ ] Register in `backend/src/main.py`

#### Modify `backend/src/routers/product.py`
- [ ] In `create_product()`: remove `requires_certification` from `Product.create()` call
- [ ] In `update_product()`: remove `requires_certification` from `Product.update()` call
- [ ] In `get_product()`: fetch qualifications via QualificationTypeRepository and pass to `product_to_response()`
- [ ] In `list_products()`: fetch qualifications for all products in a single batch query (avoid N+1), pass to `product_to_list_item()`

### Frontend changes

#### `frontend/src/lib/types.ts`
- [ ] Add `QualificationType` interface: id, name, description, target_market, applies_to_category, created_at
- [ ] Add `QualificationTypeListItem` interface: id, name, target_market, applies_to_category
- [ ] Remove `requires_certification` from `ProductListItem`, `Product`, `ProductInput`
- [ ] Add `qualifications: QualificationTypeListItem[]` to `ProductListItem` and `Product`

#### `frontend/src/lib/api.ts`
- [ ] Add `listQualificationTypes()` function
- [ ] Add `createQualificationType(data)` function
- [ ] Add `assignQualification(productId, qualificationTypeId)` function
- [ ] Add `removeQualification(productId, qualificationTypeId)` function
- [ ] Add `listProductQualifications(productId)` function

#### `frontend/src/routes/products/new/+page.svelte`
- [ ] Remove `requires_certification` checkbox
- [ ] (Qualification assignment happens after product creation, on the product detail/edit page)

#### `frontend/src/routes/products/[id]/edit/+page.svelte`
- [ ] Remove `requires_certification` checkbox
- [ ] Add qualifications section: list current qualifications, add/remove buttons
- [ ] Fetch available qualification types on mount
- [ ] Add qualification: dropdown + assign button
- [ ] Remove qualification: delete button per row

#### `frontend/src/routes/products/+page.svelte`
- [ ] Replace `requires_certification` column with qualifications count or list display

### Existing test impact
- `backend/tests/test_product.py`: tests that set or assert `requires_certification` break. Remove `requires_certification` from test inputs and assertions. Replace with qualification assignment where applicable.
- `backend/tests/test_api_product.py`: same. Product response no longer includes `requires_certification`; now includes `qualifications` list.
- Frontend Playwright tests that render the product create/edit form (if any reference the certification checkbox): update to use qualifications section instead.
- `tools/seed_data.py`: creates products with `requires_certification=true`. Update to create QualificationTypes and assign them via `product_qualifications`.

### Tests (permanent)
- [ ] `backend/tests/test_qualification_type.py` -- domain model tests:
  - Create with valid inputs
  - Reject empty name, empty target_market
- [ ] `backend/tests/test_api_qualification_type.py` -- API tests:
  - CRUD for qualification types (create, list, get, update, delete)
  - Create with duplicate name returns 409
  - Delete in-use qualification type returns 409
  - Assign qualification to product, list product qualifications, remove
  - Product response includes qualifications list
  - Product list items include qualifications list

### Tests (scratch)
- [ ] Screenshot: product edit page showing qualifications section
- [ ] Screenshot: product list with qualification indicators
- [ ] Verify migration: create a product with requires_certification=true before migration, verify it gets QUALITY_CERTIFICATE qualification after

## Acceptance criteria
- [ ] QualificationType CRUD works: POST, GET list, GET by id, PATCH, DELETE
- [ ] DELETE qualification type that is assigned to a product returns 409
- [ ] Assigning and removing qualifications from products works via API
- [ ] Product response includes `qualifications` list (not `requires_certification`)
- [ ] Migration converts `requires_certification=true` products to have QUALITY_CERTIFICATE qualification
- [ ] Frontend product pages show qualifications instead of boolean flag
- [ ] All existing tests pass (backward compatibility maintained for data)
- [ ] All permanent tests pass via `make test`

## Files created
- `backend/src/domain/qualification_type.py`
- `backend/src/qualification_type_dto.py`
- `backend/src/qualification_type_repository.py`
- `backend/src/routers/qualification_type.py`
- `backend/tests/test_qualification_type.py`
- `backend/tests/test_api_qualification_type.py`

## Files modified
- `tools/seed_data.py` -- replace requires_certification with qualification type creation and assignment
- `backend/src/domain/product.py` -- remove requires_certification
- `backend/src/schema.py` -- add qualification_types, product_qualifications tables; migration
- `backend/src/product_dto.py` -- replace requires_certification with qualifications list
- `backend/src/product_repository.py` -- remove requires_certification from save/reconstruct
- `backend/src/routers/product.py` -- fetch and include qualifications, remove requires_certification
- `backend/src/main.py` -- register qualification_type router
- `frontend/src/lib/types.ts` -- add QualificationType types, update Product types
- `frontend/src/lib/api.ts` -- add qualification API functions
- `frontend/src/routes/products/new/+page.svelte` -- remove requires_certification
- `frontend/src/routes/products/[id]/edit/+page.svelte` -- add qualifications management
- `frontend/src/routes/products/+page.svelte` -- display qualifications
