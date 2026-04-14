# Iteration 041 -- Packaging specification entity

## Context

Products exist but have no packaging concept. This iteration adds PackagingSpec, a product-level entity that defines what packaging files are needed per product per marketplace (e.g. FNSKU labels for Amazon, different standards for other channels). Specs are defined here; actual file collection follows in iteration 042.

## JTBD

- When I onboard a product for a specific marketplace, I want to define what packaging specifications are required so that the vendor knows exactly what files and prep materials to provide.
- When I view a product's packaging requirements, I want to see all specs grouped by marketplace so that I can track completeness at a glance.
- When I am a vendor viewing my products, I want to see what packaging specs exist so that I know what files I need to prepare.

## Tasks

### Backend -- Schema
- [ ] Create `packaging_specs` table:
  - `id TEXT PRIMARY KEY`
  - `product_id TEXT NOT NULL REFERENCES products(id)`
  - `marketplace TEXT NOT NULL` (user-defined string, e.g. "AMAZON", "DIRECT")
  - `spec_name TEXT NOT NULL` (user-defined string, e.g. "FNSKU Label", "Suffocation Warning")
  - `description TEXT NOT NULL DEFAULT ''`
  - `requirements_text TEXT NOT NULL DEFAULT ''` (detailed requirements for the vendor)
  - `status TEXT NOT NULL DEFAULT 'PENDING'` (PENDING only at this stage; COLLECTED added in iter 042)
  - `created_at TEXT NOT NULL`
  - `updated_at TEXT NOT NULL`
  - `UNIQUE(product_id, marketplace, spec_name)` -- one spec per name per marketplace per product

### Backend -- Domain
- [ ] New file: `src/domain/packaging.py`
- [ ] `PackagingSpecStatus` enum: `PENDING` (COLLECTED added in iter 042)
- [ ] `PackagingSpec` aggregate:
  - Fields: `id: str`, `product_id: str`, `marketplace: str`, `spec_name: str`, `description: str`, `requirements_text: str`, `status: PackagingSpecStatus`, `created_at: datetime`, `updated_at: datetime`
  - `id` is immutable (property)
  - `created_at` is immutable (property)
  - Factory method `create(product_id: str, marketplace: str, spec_name: str, description: str = "", requirements_text: str = "") -> PackagingSpec`
  - `update(spec_name: str | None, description: str | None, requirements_text: str | None)` method
  - Validation in `create`: reject empty and whitespace-only strings for `product_id`, `marketplace`, `spec_name`
  - `marketplace` and `spec_name` are user-defined strings, not enums

### Backend -- DTO
- [ ] `PackagingSpecCreate` (Pydantic): `product_id: str`, `marketplace: str`, `spec_name: str`, `description: str = ""`, `requirements_text: str = ""`
- [ ] `PackagingSpecUpdate` (Pydantic): `spec_name: str | None = None`, `description: str | None = None`, `requirements_text: str | None = None`
- [ ] `PackagingSpecResponse` (Pydantic): all fields from the aggregate including `status`

### Backend -- Repository
- [ ] New file: `src/repositories/packaging_repo.py`
- [ ] `PackagingSpecRepository` with methods:
  - `save(spec: PackagingSpec)` -- upsert (INSERT or UPDATE based on existence)
  - `get(spec_id: str) -> PackagingSpec | None`
  - `list_by_product(product_id: str) -> list[PackagingSpec]`
  - `list_by_product_and_marketplace(product_id: str, marketplace: str) -> list[PackagingSpec]`
  - `delete(spec_id: str)` -- hard delete

### Backend -- Router
- [ ] New file: `src/routers/packaging.py`
- [ ] `POST /api/v1/packaging-specs` -- create a new spec. Returns 201. Role guard: SM only.
  - Validates product_id exists (404 if not)
  - Returns 409 if duplicate (product_id + marketplace + spec_name)
- [ ] `GET /api/v1/packaging-specs` -- list specs. Query params: `product_id` (required), `marketplace` (optional filter). Role guard: SM and VENDOR.
  - Returns 422 if `product_id` not provided
- [ ] `GET /api/v1/packaging-specs/{spec_id}` -- get single spec. Role guard: SM and VENDOR. Returns 404 if not found.
- [ ] `PATCH /api/v1/packaging-specs/{spec_id}` -- update spec fields. Role guard: SM only. Returns 404 if not found.
- [ ] `DELETE /api/v1/packaging-specs/{spec_id}` -- delete spec. Only allowed if status is PENDING. Role guard: SM only. Returns 409 if status is not PENDING. Returns 404 if not found.

### Frontend
- [ ] Product detail page: "Packaging Specs" tab/section listing specs grouped by marketplace
  - Each marketplace group shows spec_name, description snippet, status pill
- [ ] "Add Packaging Spec" form (SM role): marketplace (text input), spec_name (text input), description (textarea), requirements_text (textarea)
- [ ] Edit spec inline or via modal (SM role): spec_name, description, requirements_text editable
- [ ] Delete spec button with confirmation dialog (SM role, PENDING specs only)
- [ ] VENDOR role: read-only view of packaging specs list

### Tests (permanent)
- [ ] Create packaging spec: returns 201, response fields match input, status is PENDING
- [ ] Create spec with empty product_id: returns 422
- [ ] Create spec with empty spec_name: returns 422
- [ ] Create spec with empty marketplace: returns 422
- [ ] Create spec with whitespace-only spec_name: returns 422
- [ ] Create spec referencing nonexistent product_id: returns 404
- [ ] Create duplicate (same product_id + marketplace + spec_name): returns 409
- [ ] List specs by product_id: returns all specs for that product across all marketplaces
- [ ] List specs by product_id + marketplace: returns only specs for that marketplace
- [ ] List specs with missing product_id: returns 422
- [ ] Get spec by id: returns correct spec with all fields
- [ ] Get nonexistent spec: returns 404
- [ ] Update spec: changed fields update, unchanged fields stay, updated_at advances
- [ ] Delete PENDING spec: returns 204, spec no longer retrievable
- [ ] Delete nonexistent spec: returns 404

### Tests (scratch)
- [ ] Screenshot: product detail page with packaging specs section showing multiple marketplaces
- [ ] Screenshot: add packaging spec form

## Acceptance criteria
- [ ] `packaging_specs` table exists with correct schema and unique constraint on (product_id, marketplace, spec_name)
- [ ] `PackagingSpec` aggregate validates empty/whitespace strings for product_id, marketplace, spec_name
- [ ] CRUD API works: POST (201), GET list, GET by id, PATCH, DELETE (204)
- [ ] `product_id` is required on list endpoint
- [ ] `marketplace` is a user-defined string, not an enum
- [ ] `spec_name` is a user-defined string, not an enum
- [ ] Role guard: SM creates/manages; VENDOR views
- [ ] Delete only allowed on PENDING specs (returns 409 otherwise)
- [ ] Frontend shows specs grouped by marketplace on product detail
- [ ] All permanent tests pass
