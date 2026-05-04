# Iteration 108 — Brand entity foundation (backend)

## Context

The system handles purchase orders, invoices, and shipments on behalf of an implicit single buyer. The buyer block on the auto-generated Commercial Invoice and Packing List is hardcoded in the PDF generators. The backlog has flagged "Buyer as first-class entity (currently hardcoded)" since the early iterations.
For an operator running multiple brands (the horizontal-SaaS exit path called out in the product vision) this is a foundation gap that affects every layer:

- **Procurement**: a PO is placed on behalf of a brand. Brand A and Brand B have different vendor lists, different legal entities, different tax IDs, different banking. Today PO has no `brand_id`.
- **Invoicing**: the vendor invoices Brand A specifically — Brand A's legal name, address, payment terms. Today an invoice carries no brand context.
- **Customs**: the CI declares Buyer = Brand A's legal entity + tax_id. The PDF generator emits operator constants regardless of which PO drives it.

Iter 102 split the customs-doc work: no-schema joins (iter 104), vessel/voyage
schema (iter 106), and a remaining "schema additions" piece for tax IDs /
pallet count / export reason. Tax IDs cannot live on the PO; they belong on
the Brand. This iter introduces the Brand aggregate and rewires the buyer
block on PL/CI to read from it. The customs-paper tail (Vendor.tax_id,
Shipment.pallet_count, Shipment.export_reason) follows in iter 110.

This iter is backend-only. The frontend `/brands` admin pages and the PO
create-form `BrandSelect` integration land in iter 109, mirroring the
iter 095 (backend) → iter 100 (frontend) split for user management.

## JTBD

- ADMIN needs to register one or more brands the operator runs procurement for, each with its own legal name, address, country, and tax_id. The
  operator-as-IOR alternative model is out of scope; in this iter Brand IS
  the importer of record on customs documents.
- SM creating a PO needs to pick which brand the PO is for, and the vendor
  list must restrict to vendors linked to that brand.
- The auto-generated Commercial Invoice and Packing List on a Shipment must
  emit the buyer block from the PO's brand, not from operator-level constants.
- All existing POs must continue to work after migration. A single Default
  Brand is created and every existing PO + vendor is associated with it.

## Tasks

### Domain + schema

1. New domain module `backend/src/domain/brand.py`:
   - `BrandStatus(StrEnum)`: `ACTIVE`, `INACTIVE`.
   - `Brand` dataclass: `id: int`, `name: str`, `legal_name: str`,
     `address: str`, `country: str`, `tax_id: str`, `status: BrandStatus`,
     `created_at: datetime`, `updated_at: datetime`.
   - Mutation methods: `Brand.deactivate()` (rejects when already INACTIVE
     with `BrandStatusError`), `Brand.reactivate()` (rejects when already
     ACTIVE), `Brand.update(name?, legal_name?, address?, country?, tax_id?)`
     (rejects empty / whitespace-only strings on any provided field with
     `BrandValidationError`; chain exceptions with `from`).
   - `country` validated against `domain.reference_data.COUNTRY_CODES` at
     construction; raise `BrandValidationError` on unknown.
   - `tax_id` accepted as opaque string in this iter (jurisdiction-specific
     format validation deferred — name the deferral in Notes at close).
2. New table migration in `backend/src/schema.py` (the existing flat schema bootstrap):
   ```sql
   CREATE TABLE brands (
       id BIGSERIAL PRIMARY KEY,
       name TEXT NOT NULL,
       legal_name TEXT NOT NULL,
       address TEXT NOT NULL,
       country TEXT NOT NULL,
       tax_id TEXT NOT NULL DEFAULT '',
       status TEXT NOT NULL DEFAULT 'ACTIVE',
       created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );
   CREATE UNIQUE INDEX brands_name_unique ON brands (name);
   ```
3. New join table:
   ```sql
   CREATE TABLE brand_vendors (
       brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
       vendor_id BIGINT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
       PRIMARY KEY (brand_id, vendor_id)
   );
   ```
4. Add column `purchase_orders.brand_id BIGINT REFERENCES brands(id)`,
   nullable initially. Backfill in step 5. Then alter to `NOT NULL`.
5. Migration step (single SQL block in the schema bootstrap):
   - Insert one row into `brands`: `name='Default'`, `legal_name='Default
     Brand — please update'`, `address=''`, `country='USA'`, `tax_id=''`,
     `status='ACTIVE'`. Capture the inserted id.
   - Insert into `brand_vendors` one row per existing vendor pointing at the
     default brand id.
   - `UPDATE purchase_orders SET brand_id = <default_id> WHERE brand_id IS
     NULL`.
   - `ALTER TABLE purchase_orders ALTER COLUMN brand_id SET NOT NULL`.

### Repository

6. New `backend/src/brand_repository.py` (matches existing flat layout: `vendor_repository.py`, `product_repository.py`, etc.):
   - `create(name, legal_name, address, country, tax_id) -> Brand` (raises
     `BrandValidationError` on duplicate name with `from`).
   - `get(id) -> Brand | None`.
   - `list(status: BrandStatus | None = None) -> list[Brand]`.
   - `update(id, **fields) -> Brand`.
   - `set_status(id, status) -> Brand`.
   - `assign_vendor(brand_id, vendor_id) -> None` (idempotent on conflict).
   - `unassign_vendor(brand_id, vendor_id) -> None`.
   - `list_vendor_ids(brand_id) -> list[int]`.
   - `list_brand_ids_for_vendor(vendor_id) -> list[int]`.
   - `count_active_pos(brand_id) -> int` (used by deactivate guard).
7. Extend `backend/src/repository.py` (the PO/line-item repository) to read/write `brand_id` and to expose
   `brand: Brand` on the PO read model where the PDF generators need it. Use
   a single join query, do not N+1.

### Routers + permissions

8. New `backend/src/routers/brands.py` mounted at `/api/v1/brands`:
   - `GET /` — ADMIN + SM. Optional `?status=ACTIVE|INACTIVE`.
   - `GET /{id}` — ADMIN + SM.
   - `POST /` — ADMIN. Body: `BrandCreate` Pydantic model.
   - `PATCH /{id}` — ADMIN. Body: `BrandUpdate` (all optional).
   - `POST /{id}/deactivate` — ADMIN. 409 if `count_active_pos > 0` with
     message "Brand has N active POs; close them before deactivating".
   - `POST /{id}/reactivate` — ADMIN.
   - `GET /{id}/vendors` — ADMIN + SM. Returns vendor list.
   - `POST /{id}/vendors` — ADMIN. Body: `{vendor_id: int}`. 404 on unknown
     vendor.
   - `DELETE /{id}/vendors/{vendor_id}` — ADMIN. 409 if any active PO on
     this brand uses this vendor.
9. Permission helpers in the router (no separate permissions module on
   backend; keep guards inline matching the existing pattern):
   - `require_admin` for write endpoints.
   - `require_admin_or_sm` for read endpoints.

### PO wiring

10. `POSchema` (Pydantic create / update bodies) gains `brand_id: int`
    required on create. On edit, `brand_id` is immutable (rejected with 422
    if changed; matches the existing field-immutability pattern).
11. PO create endpoint validates that the chosen vendor is linked to the
    chosen brand via `brand_vendors`. 422 on mismatch with message "Vendor
    is not assigned to brand <name>".
12. PO read DTOs (`POResponse`, `POListItem`) gain `brand_id` and
    `brand_name`. The PO detail DTO additionally exposes the full Brand
    block (`legal_name`, `address`, `country`, `tax_id`) so the PDF
    generators have everything in one fetch.

### PDF generators

13. `backend/src/services/packing_list_pdf.py`:
    - Replace the hardcoded buyer constants with `po.brand.legal_name`,
      `po.brand.address`, `po.brand.country` rendered in the
      Buyer / Consignee block.
14. `backend/src/services/commercial_invoice_pdf.py`:
    - Replace the hardcoded buyer constants with the same plus
      `po.brand.tax_id` (rendered as "Tax ID: {tax_id}" only when
      non-empty).

### Activity events

15. Add to `backend/src/domain/activity.py`:
    - `ActivityEvent.BRAND_CREATED`, `BRAND_UPDATED`, `BRAND_DEACTIVATED`,
      `BRAND_REACTIVATED`, `BRAND_VENDOR_ASSIGNED`, `BRAND_VENDOR_UNASSIGNED`.
    - `EVENT_METADATA` entries: all six map to `(NotificationCategory.LIVE,
      TargetRole.ADMIN)`. Follows the iter 107 pattern for system-level
      events.
    - `EntityType.BRAND = "BRAND"`.
16. Each brand router endpoint emits the matching event via the existing
    `ActivityRepoDep` injection pattern. Vendor assignment / unassignment
    events carry `entity_type=BRAND`, `entity_id=brand_id`, with
    `metadata={"vendor_id": <id>}`.

### Seed

17. Update `backend/src/seed.py` (the existing seed module):
    - Create two brands: "Acme Brands" (US) and "Beacon Goods" (UK).
    - Split existing seeded vendors across the two via `brand_vendors`.
    - Assign each seeded PO to the appropriate brand.

## Tests

### Existing test impact

- `backend/tests/test_purchase_orders.py`: every PO-create test will fail
  without `brand_id` in the request body. Update the shared
  `_make_po_payload` helper (or equivalent) to take `brand_id` with a
  default that points to a fixture-seeded brand. About 30+ assertions to
  audit.
- `backend/tests/test_packing_list_pdf.py`,
  `backend/tests/test_commercial_invoice_pdf.py`: PDF text assertions that
  reference the old hardcoded buyer name will break. Update to match the
  brand's legal_name from the test fixture.
- `backend/tests/conftest.py` (or the equivalent test-DB bootstrap):
  introduce a `default_brand` fixture that creates a Brand row before any
  vendor / PO fixture and a `brand_vendor_link` fixture that assigns the
  test vendors to it. Existing vendor/PO fixtures depend on this.
- `backend/tests/test_seed_data.py` (if present): assert two brands seeded.
- Playwright PO-related specs are unaffected by this iter (frontend
  consumption lands in iter 109). Confirm `make test-browser` is green
  after backend changes — should be a no-op since none of the PO-list /
  PO-detail testids reference brand yet.

### New tests

`backend/tests/test_brands.py`:

- `test_create_brand_admin_succeeds`: POST /api/v1/brands as ADMIN with
  full body, assert 201 and full row shape including `status='ACTIVE'`.
- `test_create_brand_non_admin_403`: SM, VENDOR, FREIGHT_MANAGER,
  QUALITY_LAB, PROCUREMENT_MANAGER each return 403.
- `test_create_brand_rejects_empty_legal_name`: 422.
- `test_create_brand_rejects_unknown_country`: 422.
- `test_create_brand_rejects_duplicate_name`: 409.
- `test_list_brands_admin_and_sm_succeed`: both roles see the list; status
  filter narrows.
- `test_update_brand_admin_succeeds`: PATCH with partial body, assert
  updated_at advances.
- `test_deactivate_brand_with_active_pos_returns_409`: assert error message
  mentions count.
- `test_deactivate_brand_with_no_active_pos_succeeds`.
- `test_reactivate_brand_succeeds`.
- `test_assign_vendor_to_brand_idempotent`: POST twice; second is 200 not
  duplicate-key error.
- `test_unassign_vendor_blocked_when_active_po_uses_pair`: 409.
- `test_default_brand_seeded_on_bootstrap`: assert exactly one Default
  Brand exists at app startup with the expected legal_name placeholder.

`backend/tests/test_po_brand_wiring.py`:

- `test_po_create_requires_brand_id`: 422 on missing.
- `test_po_create_rejects_vendor_not_in_brand`: 422 with message naming
  the brand.
- `test_po_brand_id_immutable_on_edit`: 422 if PATCH changes brand_id.
- `test_po_response_carries_brand_block`: read response includes full
  brand legal_name / address / country / tax_id.

`backend/tests/test_brand_pdfs.py`:

- `test_packing_list_pdf_renders_brand_buyer_block`: extract text from
  generated PDF, assert legal_name + address + country present and the
  old hardcoded buyer string absent.
- `test_commercial_invoice_pdf_renders_brand_buyer_block_with_tax_id`:
  same plus tax_id line. With `tax_id=''`, the line is omitted.

`backend/tests/test_brand_activity_events.py`:

- One assertion per event (CREATED / UPDATED / DEACTIVATED / REACTIVATED /
  VENDOR_ASSIGNED / VENDOR_UNASSIGNED) that the row carries
  `target_role=TargetRole.ADMIN`, `entity_type=EntityType.BRAND`,
  `actor_id=<admin id>`. Mirrors `test_user_activity_events.py` shape.

## Decisions

- **IOR model**: Brand is the importer of record. Brand legal entity goes
  on the CI buyer block; Brand.tax_id is the importer's tax_id. An
  operator-as-IOR singleton is out of scope and added separately if a
  future workflow needs it.
- **Tax ID format**: opaque string, no jurisdiction-specific validation in
  this iter. Reference data for tax-ID formats by country (EIN, VAT, GSTIN,
  ABN, etc.) is a separate iter when format errors start appearing.
- **Default brand placeholder**: `legal_name='Default Brand — please
  update'` makes it visible to ADMIN that the seeded brand needs editing.
  ADMIN can update it via the iter 109 frontend or an iter 108 direct API
  call.
- **Vendor↔Brand m2m**: many-to-many because vendors realistically serve
  multiple brands within an operator. One-to-many (vendor belongs to one
  brand) is rejected.
- **Backend-only iter**: `/brands` admin pages, sidebar nav, and PO
  create-form integration are iter 109. The seed and direct API calls are
  enough to exercise the backend end-to-end; the existing PO flow continues
  to work because the Default Brand absorbs migration.
- **Brand-scoped user access**: out of scope. A separate iter introduces
  `users.brand_id` (or m2m) and the access guard helper analogous to
  `check_vendor_access`.
- **Brand-scoped marketplace accounts**: out of scope. The backlog item
  "FBA Shipment ID, FNSKU, ASIN, fulfilment-centre code" merges with this
  in a follow-up iter once marketplace integration becomes pressing.

## ddd-vocab additions to propose at close

Brand, BrandStatus (ACTIVE/INACTIVE), LegalName, TaxId, BrandVendor (m2m
join), DefaultBrand (migration artifact), BrandImporterOfRecord (model
choice), BRAND_CREATED / BRAND_UPDATED / BRAND_DEACTIVATED /
BRAND_REACTIVATED / BRAND_VENDOR_ASSIGNED / BRAND_VENDOR_UNASSIGNED
(ActivityEvents), EntityType.BRAND.

## Notes

Brand landed as the buyer-principal aggregate with the IOR model: Brand IS the importer of record on customs documents, and `Brand.tax_id` is what appears on the CI Seller-side declaration. Vendor↔Brand is many-to-many because vendors realistically serve multiple brands within a single operator. Default Brand seeding is idempotent inside `init_db`: every existing PO and vendor was backfilled into a single Default brand on first boot, and the bootstrap is safe to re-run. `purchase_orders.brand_id` is left nullable at the DB layer (no migration tool yet) and enforced as required at the Pydantic create body. `brand_id` is immutable on PO update; an attempt to change it returns 422. The PDF generators read the buyer block from `po.brand_legal_name / brand_address / brand_country / brand_tax_id` joined into the PO read model; the legacy `purchase_orders.buyer_name` and `buyer_country` columns are retained as dead fields and will be dropped after iter 109 frontend lands. The PDF endpoints carry a defensive `or po.buyer_name` fallback that should never fire post-backfill but stays as a guard. Two existing tests had to be restructured to seed brands via an admin client (`test_dashboard_summary::test_sm_scopes_to_procurement` and `test_role_guards::test_sm_can_create_po`); these are correct fixture changes, not regressions. Operator-as-IOR, brand-scoped user access, brand-scoped marketplace accounts, and `Vendor.tax_id` / `Shipment.pallet_count` / `Shipment.export_reason` are all out of scope and recorded in `docs/backlog.md`. Test count: 810 → 864 backend (+54), 409 Playwright unchanged.
