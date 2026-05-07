# Iteration 113 — VendorParty (multi-entity vendor)

## Context

`Vendor` is a flat row with one address, one country, and one `account_details`. Real trade
regularly involves multiple distinct legal or physical parties under a single vendor relationship:

- **Manufacturer**: the factory that made the goods. Country of origin for customs. Appears on
  the PL per-line manufacturer block (added in iter 106 as free-text columns on `products`).
- **Seller**: the entity that invoices the buyer, signs contracts, and receives payment. Name and
  address go on the CI Seller block; `tax_id` (added to `Vendor` in iter 110) belongs here.
- **Shipper / Consignor**: the party physically tendering the shipment at the port. Goes in the PL
  Shipper block and on the Bill of Lading pickup origin.
- **Remit-to / Billing**: the banking destination for vendor invoice settlement. May be a
  factoring house, trading subsidiary, or treasury entity distinct from the seller.

Common real-world patterns this model currently cannot handle:

- A factory in China (manufacturer + physical shipper) with a Hong Kong trading company as the
  contracting seller and a Singapore holding company as the remit-to.
- An Indian mill (manufacturer) whose US subsidiary is the invoicing seller.
- A freight forwarder consolidating from multiple manufacturers under one vendor record.

Iter 106 placed `manufacturer_name`, `manufacturer_address`, `manufacturer_country` as free-text
columns on `products`. Iter 110 placed `tax_id` on the `Vendor` row as a default seller tax ID.
This iteration migrates both into a structured `VendorParty` model so that each role can carry its
own identity, address, country, and tax/banking data.

Iter 108's `BrandImporterOfRecord` decision is the symmetric buyer-side model. VendorParty is the
symmetric seller-side model.

## JTBD

- ADMIN needs to define the parties that play each role under a vendor relationship so that
  generated PL/CI documents correctly name the manufacturer, shipper, and seller as distinct
  legal entities when they differ.
- SM creating or editing a PO needs to select which seller party and remit-to party apply for
  that order when the vendor has more than one option.
- SM booking a shipment needs to select which shipper party applies when the vendor has more than
  one.
- The auto-generated Packing List must render the shipper block from the correct party (shipment
  override, else vendor default, else legacy flat-vendor address).
- The auto-generated Packing List must render each line's manufacturer block from a structured
  MANUFACTURER VendorParty when one exists, falling back to the iter-106 free-text columns, then
  to the vendor block.
- The auto-generated Commercial Invoice must render the seller block and tax ID from a structured
  SELLER VendorParty when one exists, falling back to iter-110 `Vendor.tax_id`.
- Existing vendors, POs, shipments, and products continue to work after migration. For every
  existing vendor, migration creates one VendorParty with role SELLER carrying the current
  `address + country + tax_id` and sets it as the vendor's default for all three roles. For every
  product with non-empty iter-106 manufacturer columns, migration creates a MANUFACTURER
  VendorParty under that product's vendor.

## Tasks

### Domain + schema

1. New domain module `backend/src/domain/vendor_party.py`:
   - `VendorPartyRole(StrEnum)`: `MANUFACTURER`, `SELLER`, `SHIPPER`, `REMIT_TO`.
   - `VendorParty` dataclass (UUID primary key, string fields):
     `id: str`, `vendor_id: str`, `role: VendorPartyRole`, `legal_name: str`,
     `address: str`, `country: str`, `tax_id: str` (opaque; used for SELLER and MANUFACTURER),
     `banking_details: str` (nullable-equivalent empty string; mandatory non-empty for REMIT_TO
     at the service layer, not the domain; domain accepts any string to avoid over-constraining),
     `created_at: datetime`, `updated_at: datetime`.
   - `VendorParty.create(...)`: validates `legal_name`, `address` non-empty/whitespace-only
     (raise `VendorPartyValidationError`); validates `country` against `VALID_COUNTRIES` (raise
     `VendorPartyValidationError`); chains exceptions with `from`.
   - `VendorParty.update(legal_name?, address?, country?, tax_id?, banking_details?)`: same
     field-level validations, advances `updated_at`.
   - `VendorPartyValidationError(ValueError)`: domain-level validation failure.

2. Schema additions in `backend/src/schema.py`:
   ```sql
   CREATE TABLE vendor_parties (
       id          TEXT PRIMARY KEY,
       vendor_id   TEXT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
       role        TEXT NOT NULL,
       legal_name  TEXT NOT NULL DEFAULT '',
       address     TEXT NOT NULL DEFAULT '',
       country     TEXT NOT NULL DEFAULT '',
       tax_id      TEXT NOT NULL DEFAULT '',
       banking_details TEXT NOT NULL DEFAULT '',
       created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );
   CREATE INDEX vendor_parties_vendor_id ON vendor_parties (vendor_id);
   CREATE INDEX vendor_parties_vendor_role ON vendor_parties (vendor_id, role);
   ```

3. New nullable FK columns on `vendors`:
   ```sql
   ALTER TABLE vendors ADD COLUMN default_seller_party_id    TEXT REFERENCES vendor_parties(id);
   ALTER TABLE vendors ADD COLUMN default_shipper_party_id   TEXT REFERENCES vendor_parties(id);
   ALTER TABLE vendors ADD COLUMN default_remit_to_party_id  TEXT REFERENCES vendor_parties(id);
   ```
   (Nullable; no NOT NULL constraint. When all three point at the same VendorParty the vendor is
   single-entity.)

4. New nullable FK on `products`:
   ```sql
   ALTER TABLE products ADD COLUMN manufacturer_party_id TEXT REFERENCES vendor_parties(id);
   ```
   The iter-106 free-text columns (`manufacturer_name`, `manufacturer_address`,
   `manufacturer_country`) remain on the table and are READ-ONLY from this iteration forward.
   They will be dropped in a follow-up iteration once all existing products have been backfilled
   and the free-text write paths have been removed from the frontend.

5. New nullable FKs on `shipments`:
   ```sql
   ALTER TABLE shipments ADD COLUMN shipper_party_id TEXT REFERENCES vendor_parties(id);
   ```

6. New nullable FKs on `purchase_orders`:
   ```sql
   ALTER TABLE purchase_orders ADD COLUMN seller_party_id   TEXT REFERENCES vendor_parties(id);
   ALTER TABLE purchase_orders ADD COLUMN remit_to_party_id TEXT REFERENCES vendor_parties(id);
   ```

7. Migration block inside `init_db` (runs idempotently using `WHERE NOT EXISTS` guards):
   - For every existing `Vendor` row: insert one `vendor_parties` row with `role='SELLER'`,
     `legal_name = vendor.name`, `address = vendor.address`, `country = vendor.country`,
     `tax_id = vendor.tax_id`. Set `vendors.default_seller_party_id`,
     `vendors.default_shipper_party_id`, and `vendors.default_remit_to_party_id` all to that
     party's id (single-entity collapse). Idempotency guard: skip if
     `default_seller_party_id IS NOT NULL`.
   - For every `Product` where `manufacturer_name != ''` AND `manufacturer_party_id IS NULL`:
     look up the product's vendor, insert one `vendor_parties` row with `role='MANUFACTURER'`,
     `legal_name = manufacturer_name`, `address = manufacturer_address`,
     `country = manufacturer_country` (use the vendor's country if empty), `tax_id = ''`.
     Set `products.manufacturer_party_id` to that party's id.

### Domain updates

8. `backend/src/domain/vendor.py`: add `default_seller_party_id: str | None = None`,
   `default_shipper_party_id: str | None = None`, `default_remit_to_party_id: str | None = None`
   to `Vendor.__init__`. Add `Vendor.set_default_party(role: VendorPartyRole, party_id: str | None)`
   method that updates the appropriate field and advances `updated_at`.

9. `backend/src/domain/product.py`: add `manufacturer_party_id: str | None = None` to
   `Product.__init__` and `Product.create(...)`. The three iter-106 free-text fields remain on
   the domain object (read-only path) but `Product.update(...)` stops accepting
   `manufacturer_name`, `manufacturer_address`, `manufacturer_country` as writable inputs in
   this iteration; attempts to write them via the PATCH endpoint return a 422 with message
   "manufacturer fields are read-only; use manufacturer_party_id". Add
   `Product.set_manufacturer_party(party_id: str | None)` method.

10. `backend/src/domain/shipment.py`: add `shipper_party_id: str | None = None` to
    `Shipment.__init__`. Add `Shipment.set_shipper_party(party_id: str | None)` method.

### Repository

11. New `backend/src/vendor_party_repository.py`:
    - `create(vendor_id, role, legal_name, address, country, tax_id, banking_details) -> VendorParty`
      (validates via `VendorParty.create`; raises `VendorPartyValidationError` with `from`).
    - `get(id) -> VendorParty | None`.
    - `list_by_vendor(vendor_id) -> list[VendorParty]`.
    - `list_by_vendor_and_role(vendor_id, role) -> list[VendorParty]`.
    - `update(id, **fields) -> VendorParty`.
    - `delete(id) -> None` (raises `VendorPartyInUseError` if any FK on vendors, products, or
      shipments / purchase_orders still references this party).

12. Extend `backend/src/vendor_repository.py`: thread `default_seller_party_id`,
    `default_shipper_party_id`, `default_remit_to_party_id` through INSERT, UPDATE, and
    `_row_to_vendor`. Add `set_default_party(vendor_id, role, party_id | None) -> Vendor`.

13. Extend `backend/src/repository.py` (PO repository) and shipment repository to:
    - Read / write `purchase_orders.seller_party_id` and `purchase_orders.remit_to_party_id`.
    - Read / write `shipments.shipper_party_id`.
    - Join `vendor_parties` into the PO/shipment read model so that PDF generators receive
      the resolved party objects (single fetch, no N+1). The read model carries:
      - `po.seller_party: VendorParty | None`
      - `po.remit_to_party: VendorParty | None`
      - `shipment.shipper_party: VendorParty | None`
      - `vendor.default_seller_party: VendorParty | None`
      - `vendor.default_shipper_party: VendorParty | None`
      - `vendor.default_remit_to_party: VendorParty | None`
    - Extend the product read model for per-line manufacturer resolution:
      `product.manufacturer_party: VendorParty | None` (joined when fetching products for PL).

### Routers + permissions

14. New `backend/src/routers/vendor_parties.py` mounted under
    `/api/v1/vendors/{vendor_id}/parties`:
    - `GET /` (ADMIN + SM) — returns all parties for the vendor, grouped by role.
    - `GET /{party_id}` (ADMIN + SM).
    - `POST /` (ADMIN) — body: `VendorPartyCreate` Pydantic model (role, legal_name, address,
      country, tax_id?, banking_details?). 422 on validation failure. 404 on unknown vendor_id.
    - `PATCH /{party_id}` (ADMIN) — body: `VendorPartyUpdate` (all optional). 404 on unknown id.
    - `DELETE /{party_id}` (ADMIN) — 409 with message "VendorParty is referenced by
      {N} active records" if `VendorPartyInUseError` is raised.

15. Extend `PATCH /api/v1/vendors/{vendor_id}` to accept `default_seller_party_id`,
    `default_shipper_party_id`, `default_remit_to_party_id` (all optional strings or null).
    Validate: if a non-null party_id is provided, the party must exist and `party.vendor_id`
    must equal `vendor_id`; 422 on mismatch. Validate: the party's role must match the semantic
    of the default being set (SELLER party for `default_seller_party_id`, etc.); 422 on mismatch.

16. Extend `PATCH /api/v1/po/{po_id}` to accept `seller_party_id` and `remit_to_party_id`
    (nullable). Validate: party must exist and belong to the PO's vendor; role must match
    (SELLER / REMIT_TO); 422 on mismatch. `seller_party_id` is mutable on PO update (unlike
    `brand_id`).

17. Extend `PATCH /api/v1/shipments/{id}` (or a new sub-endpoint) to accept `shipper_party_id`
    (nullable). Validate: party must exist and belong to the shipment's vendor; role must be
    SHIPPER; 422 on mismatch. Allowed in DRAFT and DOCUMENTS_PENDING statuses only.

### PDF rendering

18. `backend/src/services/packing_list_pdf.py`:
    - Shipper block: reads from `shipment.shipper_party` (if set), else
      `vendor.default_shipper_party` (if set), else falls back to legacy `vendor.address +
      vendor.country` (current behavior). No fallback is removed in this iteration.
    - Per-line manufacturer block: reads from `product.manufacturer_party` (if set), else falls
      back to the existing `manufacturer_lookup` dict (iter-106 free-text columns), else falls
      back to the vendor block. Extend `generate_packing_list_pdf` signature to accept an optional
      `party_lookup: dict[str, VendorParty]` (maps part_number to MANUFACTURER VendorParty). The
      existing `manufacturer_lookup: dict[str, dict[str, str]]` parameter is retained for the
      free-text fallback path.

19. `backend/src/services/commercial_invoice_pdf.py`:
    - Seller block: reads from `po.seller_party` (if set), else `vendor.default_seller_party`
      (if set), else falls back to legacy `vendor.name + vendor.address + vendor.country`.
    - Tax ID line: reads `seller_party.tax_id` (if seller party is set), else `vendor.tax_id`
      (iter-110 default), else omit the line (current behavior).
    - Banking / remit-to block (where rendered): reads from `po.remit_to_party` else
      `vendor.default_remit_to_party`; rendered as a labeled block only when non-empty.

20. `backend/src/routers/shipment.py`: extend the PDF-generation call sites to resolve and pass
    the new party objects into the PDF generators.

### Activity events

21. Add to `backend/src/domain/activity.py`:
    - `ActivityEvent.VENDOR_PARTY_ADDED`, `VENDOR_PARTY_UPDATED`, `VENDOR_PARTY_REMOVED`.
    - `EVENT_METADATA` entries: all three map to `(NotificationCategory.LIVE, TargetRole.SM)`.
      Vendor-party lifecycle is operations-visible (SM manages parties) rather than system-admin
      (unlike BRAND_* events which route to ADMIN).
    - `EntityType.VENDOR_PARTY = "VENDOR_PARTY"`.
22. Each vendor-party router endpoint emits the matching event via the existing
    `ActivityRepoDep` injection pattern. Events carry `entity_type=VENDOR_PARTY`,
    `entity_id=party_id`, `metadata={"vendor_id": <vendor_id>, "role": <role>}`.

### Frontend

23. New `frontend/src/lib/types.ts` additions:
    - `VendorPartyRole` const enum: `MANUFACTURER | SELLER | SHIPPER | REMIT_TO`.
    - `VendorParty` interface: `id, vendor_id, role, legal_name, address, country, tax_id,
      banking_details, created_at, updated_at`.
    - Update `Vendor` interface: add `default_seller_party_id`, `default_shipper_party_id`,
      `default_remit_to_party_id` (all `string | null`).
    - Update `PurchaseOrder` interface: add `seller_party_id`, `remit_to_party_id`
      (both `string | null`).
    - Update `Shipment` interface: add `shipper_party_id` (`string | null`).

24. New `frontend/src/lib/api/vendorParties.ts`: thin fetch wrappers for list, get, create,
    update, delete matching the pattern in `api/vendors.ts`.

25. New component `frontend/src/lib/components/VendorPartiesPanel.svelte`:
    - Lists existing parties grouped by role (each role as a collapsible or labeled section).
    - Each party row shows legal_name, country, role pill, and Edit / Remove buttons (ADMIN only).
    - A "Default for {role}" radio or button per row sets the vendor's default for that role
      (calls PATCH `/api/v1/vendors/{id}` with the appropriate `default_*_party_id`).
    - An "Add party" button per role (ADMIN only) opens an inline or modal form:
      `VendorPartyForm.svelte` (legal_name, address, country dropdown, tax_id, banking_details,
      role pre-filled).
    - `VendorPartiesPanel` takes an `ariaLabel` prop forwarded to `aria-label` on the root
      element (list container pattern per the primitive accessible-name convention).

26. Integrate `VendorPartiesPanel` into `frontend/src/routes/(nexus)/vendors/[id]/edit/+page.svelte`
    (or a new sub-route `/vendors/[id]/parties` if the edit page becomes too wide). The panel
    appears below the existing vendor fields. Non-ADMIN users see the panel read-only.

27. Extend the PO create/edit form (`/po/new`, `/po/[id]/edit`) with optional `seller_party_id`
    and `remit_to_party_id` dropdowns, populated from the selected vendor's party list filtered
    by role. These are optional; when blank the backend uses vendor defaults. Use `getByLabel`
    selectors in tests (label text: "Seller party" and "Remit-to party").

28. Extend the shipment detail panel (`/shipments/[id]`) with an optional `shipper_party_id`
    dropdown (label: "Shipper party"), populated from the PO's vendor's SHIPPER parties.
    Enabled in DRAFT and DOCUMENTS_PENDING. Read-only in later statuses. Use `getByLabel`
    selector in tests.

### Seed

29. Update `backend/src/seed.py`:
    - For each seeded vendor, create at least a SELLER VendorParty (backfill idempotency handles
      this automatically if the vendor is already seeded before this iter, but seed should
      explicitly create realistic multi-party data for at least one vendor).
    - For one seeded vendor (e.g., the China factory vendor), create distinct MANUFACTURER,
      SELLER, and SHIPPER parties: factory address in China for MANUFACTURER and SHIPPER; HK
      trading entity for SELLER.
    - Assign the HK SELLER party as `default_seller_party_id` for that vendor.

## Tests

### Existing test impact

- `backend/tests/test_api_vendor.py`: vendor responses now include `default_seller_party_id`,
  `default_shipper_party_id`, `default_remit_to_party_id` (all null for freshly created vendors
  in tests). Add these fields to the make-vendor factory helper and exact-shape assertions.
- `backend/tests/test_api_product.py`: product responses now include `manufacturer_party_id`
  (null for freshly created products). Add to response shape assertions.
- `backend/tests/test_api_shipment.py`: shipment responses now include `shipper_party_id`
  (null). Add to response shape assertions.
- `backend/tests/test_brand_pdfs.py`: `generate_packing_list_pdf` now accepts a `party_lookup`
  parameter. Existing test call sites pass `party_lookup=None` (default); no logic change.
  `generate_commercial_invoice_pdf` seller-block resolution now checks for `po.seller_party`
  first. Existing test fixture creates no seller party so falls through to legacy path; behavior
  unchanged. Confirm tests still pass.
- `backend/tests/conftest.py`: no structural changes required; no new mandatory fixtures for
  the existing test suite. Any new tests that need a seeded VendorParty use a local fixture
  helper.
- Playwright tests: the vendor edit page gains a new `VendorPartiesPanel` section. Existing
  Playwright tests for the vendor edit page (if any target the form fields by label) are not
  affected because the new panel is appended below existing fields. Confirm `make test-browser`
  passes after frontend changes land.

### New tests

`backend/tests/test_vendor_party_domain.py`:
- `test_vendor_party_create_valid`: full happy-path; assert all fields round-trip.
- `test_vendor_party_create_rejects_empty_legal_name`: `VendorPartyValidationError` raised.
- `test_vendor_party_create_rejects_empty_address`: same.
- `test_vendor_party_create_rejects_unknown_country`: same.
- `test_vendor_party_update_advances_updated_at`: assert `updated_at` strictly later.
- `test_vendor_party_update_rejects_invalid_country`: `VendorPartyValidationError` raised.

`backend/tests/test_vendor_party_repository.py`:
- `test_create_and_get_round_trip`: insert + fetch; assert dict has exactly the expected keys.
- `test_list_by_vendor_returns_all_roles`: create three parties across two roles; list returns
  all three; list_by_role returns only the matching subset.
- `test_delete_unlinked_party_succeeds`.
- `test_delete_party_referenced_as_vendor_default_raises_in_use_error`: set
  `vendor.default_seller_party_id` then attempt delete; assert `VendorPartyInUseError`.
- `test_delete_party_referenced_by_product_raises_in_use_error`.
- `test_delete_party_referenced_by_shipment_raises_in_use_error`.
- `test_set_default_party_updates_vendor_row`.
- `test_migration_backfill_creates_seller_party_for_existing_vendor`: run `init_db` against a
  pre-migration vendor row (no `default_seller_party_id`); assert a SELLER party exists and the
  three default columns point at it.
- `test_migration_backfill_creates_manufacturer_party_for_product_with_free_text`: pre-migration
  product row has non-empty `manufacturer_name`; assert MANUFACTURER party created and
  `products.manufacturer_party_id` set.

`backend/tests/test_api_vendor_parties.py`:
- `test_create_vendor_party_admin_succeeds`: POST to `/api/v1/vendors/{id}/parties`; 201;
  assert response shape has exactly the expected keys.
- `test_create_vendor_party_non_admin_403`: SM, VENDOR, FREIGHT_MANAGER each return 403.
- `test_create_vendor_party_rejects_invalid_country`: 422.
- `test_create_vendor_party_rejects_empty_legal_name`: 422.
- `test_list_vendor_parties_sm_succeeds`: SM can list; grouped-by-role shape.
- `test_patch_vendor_party_updates_fields`: PATCH; assert updated_at advances.
- `test_delete_unlinked_vendor_party_succeeds`: 204.
- `test_delete_referenced_vendor_party_returns_409`: link party as vendor default; delete; 409
  with message mentioning "referenced".
- `test_patch_vendor_sets_default_seller_party_id`: PATCH vendor with valid SELLER party_id;
  200; response carries new default_seller_party_id.
- `test_patch_vendor_rejects_wrong_role_for_default`: provide a MANUFACTURER party_id as
  `default_seller_party_id`; 422 with message mentioning role mismatch.
- `test_patch_vendor_rejects_party_from_other_vendor`: 422.

`backend/tests/test_vendor_party_pdf_rendering.py`:
- `test_packing_list_renders_shipper_from_shipment_party`: create a SHIPPER party, set
  `shipment.shipper_party_id`; generate PL; assert party's `legal_name` appears in PDF text;
  assert the vendor's flat address does not appear in the shipper block.
- `test_packing_list_falls_back_to_vendor_default_shipper`: no per-shipment override; vendor has
  `default_shipper_party_id` set; assert default party's `legal_name` appears.
- `test_packing_list_falls_back_to_flat_vendor_when_no_shipper_party`: neither per-shipment nor
  vendor default; assert the legacy vendor.address path is used.
- `test_packing_list_renders_manufacturer_party_per_line`: create a MANUFACTURER party; set
  `product.manufacturer_party_id`; assert party's `legal_name` appears in the per-line
  manufacturer block.
- `test_packing_list_falls_back_to_free_text_manufacturer`: `manufacturer_party_id` is None;
  product has non-empty `manufacturer_name`; assert free-text name appears.
- `test_commercial_invoice_renders_seller_party`: create SELLER party on vendor; set
  `po.seller_party_id`; generate CI; assert party's `legal_name` + `tax_id` appear in seller
  block.
- `test_commercial_invoice_falls_back_to_vendor_default_seller`: no PO override; vendor has
  `default_seller_party_id`; assert that party's data appears.
- `test_commercial_invoice_falls_back_to_vendor_tax_id_when_no_seller_party`: neither PO nor
  vendor default; assert iter-110 `vendor.tax_id` appears.
- `test_commercial_invoice_omits_tax_id_line_when_all_empty`: all three tax_id sources empty;
  assert no "Tax ID" line in CI text.

`backend/tests/test_vendor_party_activity_events.py`:
- `test_party_added_event_emitted`: assert row with `VENDOR_PARTY_ADDED`, `target_role=SM`,
  `entity_type=VENDOR_PARTY`, `actor_id=admin_id`.
- `test_party_updated_event_emitted`: same for UPDATED.
- `test_party_removed_event_emitted`: same for REMOVED.

`frontend/tests/vendor-parties.spec.ts` (Playwright, permanent):
- `test_vendor_parties_panel_lists_parties_grouped_by_role`: navigate to
  `/vendors/{id}/edit` as ADMIN; mock `/api/v1/vendors/{id}/parties` returning two parties
  (SELLER + SHIPPER); assert `getByRole('region', { name: 'Seller' })` contains the SELLER
  party's `legal_name`; assert `getByRole('region', { name: 'Shipper' })` contains the SHIPPER
  party's `legal_name`.
- `test_vendor_parties_panel_add_party_opens_form`: click "Add party" button in the Seller
  section; assert a form with `getByLabel('Legal name')`, `getByLabel('Address')`,
  `getByLabel('Country')` appears.
- `test_vendor_parties_panel_non_admin_sees_no_add_button`: mock session as SM; assert no
  "Add party" button visible.
- `test_po_form_shows_seller_party_dropdown_when_vendor_selected`: `/po/new`; select a vendor
  that has SELLER parties; assert `getByLabel('Seller party')` combobox is visible.
- `test_shipment_detail_shows_shipper_party_dropdown_in_draft`: `/shipments/{id}` in DRAFT;
  assert `getByLabel('Shipper party')` combobox is visible.
- `test_shipment_detail_shipper_party_readonly_after_booked`: mock status BOOKED; assert
  `getByLabel('Shipper party')` is not present or disabled.

## Decisions

- **Migration and fallback strategy**: the iter-106 free-text manufacturer columns
  (`manufacturer_name`, `manufacturer_address`, `manufacturer_country`) are retained as
  READ-ONLY after migration. The backfill creates a MANUFACTURER VendorParty for every product
  that has non-empty free-text, but the columns are not dropped here. The PDF rendering falls
  through the chain (party FK first, then free-text dict, then vendor block), so no existing
  shipment PDF changes unless a party is explicitly assigned. Dropping the columns in this
  iteration would require coordinating a schema DROP with a frontend write-path removal and
  testing all PL generators under the new path simultaneously; that risk is not justified. A
  follow-up iteration drops the columns after the write paths are confirmed removed.

- **Single-entity collapse in migration**: every existing Vendor gets one SELLER VendorParty
  with all three `default_*_party_id` columns pointing at it. This means a single-entity vendor
  has one party playing all roles. ADMIN can later add distinct SHIPPER or REMIT_TO parties and
  set those defaults. This preserves backward compatibility with no behavioral change for
  existing single-entity vendors.

- **SELLER party is the canonical source of vendor tax_id from this iteration forward**: the
  `vendor.tax_id` column (iter 110) remains on the `vendors` table for the CI fallback path.
  New vendors should have a SELLER party with `tax_id` set. The old column is not dropped here
  for the same reason as manufacturer: drop it once the write paths are confirmed migrated.

- **Role-scoped default pointers on Vendor instead of implicit "one party per role" constraint**:
  a vendor can have multiple SELLER parties (e.g., different entities for different product
  lines) and a `default_seller_party_id` pointer picks the operative default for new POs. This
  is more flexible than enforcing one party per role and matches how Brand uses the default-id
  backfill approach.

- **Vendor-party delete protection**: `VendorPartyInUseError` blocks deletion when any FK
  points at the party. ADMIN must clear the reference (set the FK to null or reassign) before
  deleting. This avoids cascading nulls silently corrupting rendered PDFs.

- **PO `seller_party_id` is mutable on update**: unlike `brand_id` (immutable once set), the
  seller party can be corrected after PO creation because it is an operational detail, not a
  procurement-scope constraint. The `brand_id` immutability rule reflects that brand determines
  vendor eligibility; seller party does not.

- **Activity events route to SM (not ADMIN)**: vendor-party operations are procurement
  workflow actions, not system administration actions. BRAND_* events route to ADMIN because
  brands are operator-level config. VENDOR_PARTY_* events route to SM because party selection
  appears during PO and shipment creation.

## Out of scope

- Dropping `manufacturer_name / manufacturer_address / manufacturer_country` columns from
  `products`. Deferred to the follow-up iteration once write paths are confirmed removed.
- Dropping `vendor.tax_id` and `vendor.account_details` columns. Deferred until SELLER party
  is the confirmed sole write path.
- Per-party banking-details rendering on the CI. The `banking_details` field is stored and
  exposed in this iteration but the CI PDF renders a placeholder only; full banking block layout
  is a follow-up.
- Jurisdiction-specific `tax_id` format validation (EIN / VAT / GSTIN / ABN). Opaque string
  in this iter, consistent with iter 108 and iter 110 decisions.
- MANUFACTURER party on a PO or line-item level override (e.g., a single PO uses a different
  factory than the product default). Product-level manufacturer party covers 95% of cases;
  line-level override is a follow-up.
- VendorParty status (ACTIVE / INACTIVE). All parties are implicitly active; lifecycle
  management (mark a party stale when a vendor restructures) is a follow-up.

## Notes

(Filled at iteration close.)
