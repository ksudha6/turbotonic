# Iteration 109 — Brand frontend

## Context

Iter 108 landed the Brand backend: `Brand` aggregate, `BrandRepository`, `/api/v1/brands` router with full ADMIN CRUD, six BRAND_* activity events targeting `TargetRole.ADMIN`, schema migration with idempotent Default-Brand backfill, PO `brand_id` required at the Pydantic create body with vendor-belongs-to-brand validation, and PL/CI PDF generators reading the buyer block from `po.brand_*`. 864 backend tests green.

There is no UI surface for any of it. ADMIN currently can manage brands only through direct API calls. The PO create form does not expose a brand selector. The sidebar has no `Brands` nav item. Existing seeded brands (Acme Brands, Beacon Goods) are invisible to operators.

This iter is the frontend half. Mirrors the iter 095 (backend) → iter 100 (frontend) split for user management. Shape mirrors `/users` and `/vendors`: list page with filters and a status-aware action column, dedicated `/new` create route, dedicated `/[id]/edit` route hosting both the attribute form and the vendor-assignment panel. Sidebar adds a BRANDS slot wired ADMIN-only. PO create form gains a `BrandSelect` that cascades the vendor list. PO detail and list responses already carry `brand_id` and `brand_name` from iter 108; surfacing them is read-only and folds in here.

## JTBD

- ADMIN needs `/brands` list with optional `?status=` filter to see all brands and reach create / edit / deactivate / reactivate actions.
- ADMIN needs to create a new brand with name, legal_name, address, country, tax_id via a form. Country uses the existing combobox primitive.
- ADMIN needs to edit attributes of an existing brand and to deactivate / reactivate it. Deactivate is blocked when active POs reference the brand (server returns 409 with named count, surfaced inline).
- ADMIN needs to assign and unassign vendors on a brand from the brand edit page. Unassign is blocked when active POs use the brand+vendor pair (server returns 409, surfaced inline).
- SM creating a PO needs a `BrandSelect` between PO Type and Vendor; the Vendor list filters to vendors assigned to the chosen brand. The cascade matches the existing PO-Type narrows-Vendor-list pattern.
- SM viewing a PO list / detail needs to see which brand the PO belongs to.
- ADMIN's notification feed surfaces the six brand-lifecycle events with friendly labels.

## Tasks

### 1. Types

In `frontend/src/lib/types.ts`:
- `BrandStatus = 'ACTIVE' | 'INACTIVE'`
- `Brand` shape: `id`, `name`, `legal_name`, `address`, `country`, `tax_id`, `status: BrandStatus`, `created_at`, `updated_at`
- `BrandCreate`, `BrandUpdate` (all fields optional except create-required)
- Extend `PurchaseOrder` and `POListItem` types with `brand_id: string` and `brand_name: string`. Detail type carries `brand_legal_name`, `brand_address`, `brand_country`, `brand_tax_id` (already present on the API response since iter 108).

### 2. API client

In `frontend/src/lib/api.ts`, mirror the iter 100 user-management shape:
- `listBrands({ status? }) -> Brand[]`
- `getBrand(id) -> Brand`
- `createBrand(BrandCreate) -> Brand` (surfaces 409 duplicate-name detail inline via local `detailOrThrow`)
- `patchBrand(id, BrandUpdate) -> Brand`
- `deactivateBrand(id) -> Brand` (surfaces 409 active-POs detail)
- `reactivateBrand(id) -> Brand`
- `listBrandVendors(id) -> Vendor[]`
- `assignVendorToBrand(brand_id, vendor_id) -> void` (idempotent; 404 unknown vendor)
- `unassignVendorFromBrand(brand_id, vendor_id) -> void` (409 if active PO uses pair)

All return-on-401 redirect to /login per the existing `requireOk` / `requireOkOrThrow` pattern.

### 3. Permissions

In `frontend/src/lib/permissions.ts`:
- `canManageBrands(role) = is(role, 'ADMIN')`
- `canViewBrands(role) = is(role, 'ADMIN', 'SM')`

### 4. Sidebar item

In `frontend/src/lib/ui/sidebar-items.ts`: add a `BRANDS` slot in the same group as USERS and VENDORS. Visible only when `canManageBrands(role)` is true. Path `/brands`.

### 5. Brand components

New folder `frontend/src/lib/brand/`:

- `BrandListFilters.svelte` — Phase 4.0 `Select` for status (ACTIVE / INACTIVE / clear), Clear button. Mirror of `frontend/src/lib/vendor/VendorListFilters.svelte`.
- `BrandListTable.svelte` — responsive desktop `<table data-testid="brand-table-desktop">` + mobile `<ul data-testid="brand-table-mobile">` cards. Columns: Name, Legal Name, Country, Status (Phase 4.0 `StatusPill` ACTIVE→green / INACTIVE→gray), Tax ID (truncated to 12 chars + ellipsis), Actions (Edit always; Deactivate on ACTIVE; Reactivate on INACTIVE). Per-row `data-testid="brand-row-{id}"`.
- `BrandForm.svelte` — single component used by both `/brands/new` and `/brands/[id]/edit`. Props: `mode: 'create' | 'edit'`, `initial?: Brand`, `submitting: boolean`, `error: string | null`, `onSubmit(BrandCreate | BrandUpdate)`, `onCancel()`. Phase 4.0 `PanelCard` + `FormField` + `Input` + `Select` (country combobox sourced from `listReferenceData()`) + sticky-on-mobile footer. Validates: name + legal_name + address + country non-empty / non-whitespace; tax_id allowed empty. On `mode="edit"`, name field is disabled (immutable post-create); other fields editable.
- `BrandVendorAssignmentPanel.svelte` — `PanelCard` titled "Vendors" on the brand edit page. Lists currently-assigned vendors (rows with name + country + Remove button). Footer Add row: combobox `Select` of all ACTIVE vendors NOT yet assigned + Add button. 409 unassign and 404 add errors render inline.

### 6. Routes

- `frontend/src/routes/(nexus)/brands/+page.ts` — load guard via `canViewBrands(user.role)` else redirect to /dashboard.
- `frontend/src/routes/(nexus)/brands/+page.svelte` — page header with "New brand" CTA gated by `canManageBrands`, `BrandListFilters`, `BrandListTable`. Empty / loading / error states using the standard `EmptyState` / `LoadingState` / `ErrorState` primitives. Refetch on filter change via `$effect`.
- `frontend/src/routes/(nexus)/brands/new/+page.ts` — load guard via `canManageBrands`. Redirects non-ADMIN to /brands.
- `frontend/src/routes/(nexus)/brands/new/+page.svelte` — `BrandForm mode="create"`. On submit, `createBrand` then `goto('/brands/{id}/edit')` so the user can immediately assign vendors (no list view in between).
- `frontend/src/routes/(nexus)/brands/[id]/edit/+page.ts` — load guard via `canManageBrands`.
- `frontend/src/routes/(nexus)/brands/[id]/edit/+page.svelte` — `BrandForm mode="edit"` followed by `BrandVendorAssignmentPanel`. Status-action row above the form: Deactivate button when ACTIVE, Reactivate button when INACTIVE; both behind `UserActionConfirm`-style modal copy. 409 paths render inline.

### 7. PO create form integration

In `frontend/src/lib/po/PoForm.svelte` (the iter 085 unified create/edit form):
- Add `brand_id: string` to the form state and validation set.
- Insert a `BrandSelect` field between PO Type and Vendor. Source: `listBrands({ status: 'ACTIVE' })` lazy-fetched on mount.
- On brand change, reset `vendor_id` and refetch the vendor list scoped to the brand: `listBrandVendors(brand_id).then(filter to ACTIVE)`. Existing PO-type narrows-vendor-type filter still applies on top.
- On `mode="edit-draft"` and `mode="edit-revise"`, the BrandSelect renders disabled with the existing `brand_id` selected (matches PO Type immutability pattern). Submit body always carries `brand_id`.
- If `brand_id` is unset, the Vendor select is disabled with hint copy "Select a brand first".

### 8. PO list + detail surfacing

- `frontend/src/lib/po/PoListTable.svelte`: add a "Brand" column on desktop (between Vendor and Marketplace); show `po.brand_name` truncated to 18 chars. Mobile cards: prepend `Brand: {brand_name}` line under the PO number.
- `frontend/src/routes/(nexus)/po/[id]/+page.svelte`: in the existing `PoMetadataPanels` (or a new `PoBrandPanel`), surface the brand block as a small read-only `AttributeList` row group: Brand Name, Legal Name, Country, Tax ID. Position above the legacy Buyer block. Tax ID row hidden when empty.

### 9. Activity feed labels

In `frontend/src/lib/event-labels.ts`: add labels for the six BRAND_* events:
- `BRAND_CREATED` → "Brand created"
- `BRAND_UPDATED` → "Brand updated"
- `BRAND_DEACTIVATED` → "Brand deactivated"
- `BRAND_REACTIVATED` → "Brand reactivated"
- `BRAND_VENDOR_ASSIGNED` → "Vendor assigned to brand"
- `BRAND_VENDOR_UNASSIGNED` → "Vendor removed from brand"

`categoryToTone` mapping unchanged (LIVE → green per existing convention).

## Tests

### Existing test impact

- `frontend/tests/po-create.spec.ts`: every create flow now needs a brand selection step. Audit for hardcoded form-fill sequences and add a `selectBrand()` helper to the shared fixture file. Estimate ~15 spec assertions to update.
- `frontend/tests/po-detail.spec.ts`: response fixtures need `brand_id`, `brand_name`, `brand_legal_name`, `brand_address`, `brand_country`, `brand_tax_id`. Use `makePO()` factory.
- `frontend/tests/po-list.spec.ts`: response fixtures need `brand_id`, `brand_name`. New "Brand" column adds an extra `<td>` per row; row-count assertions unchanged.
- `frontend/tests/role-rendering.spec.ts`: BRANDS sidebar visibility — add ADMIN-only assertion; non-ADMIN absence.
- Conftest / shared fixtures: `makeBrand()` factory, `setupBrandsList()` helper that route-mocks the brands API surface for any spec that needs it.

### New tests

`frontend/tests/brand-list.spec.ts`:
- page mount under (nexus); page header + "New brand" CTA visible for ADMIN
- non-ADMIN: list visible for SM, redirect for VENDOR / others per `canViewBrands`
- list renders rows; mobile cards at <768px
- status filter narrows; clear restores
- empty state when filtered to no rows
- error + retry state
- click row Edit navigates to /brands/{id}/edit

`frontend/tests/brand-create.spec.ts`:
- form mounts; all fields rendered; country combobox populates from reference data
- submit with empty legal_name / address / country → inline validation error, no POST
- submit with valid body → POST fired with full body, navigate to /brands/{id}/edit
- 409 duplicate name → inline error with server detail
- Cancel returns to /brands

`frontend/tests/brand-edit.spec.ts`:
- form mounts with existing values; name disabled (immutable post-create); other fields editable
- save updates → PATCH fired, success state
- deactivate ACTIVE → modal confirm → status flips, action row rerenders Reactivate
- deactivate with active-POs 409 → inline error with server count message
- reactivate INACTIVE → status flips
- vendor-assignment panel: lists current vendors; Remove triggers DELETE, row disappears
- vendor-assignment Remove with active-POs 409 → inline error
- Add vendor: combobox of unassigned vendors, Add triggers POST, row appears
- VENDOR / non-ADMIN redirected to /brands or /dashboard

`frontend/tests/po-create-with-brand.spec.ts`:
- BrandSelect renders between PO Type and Vendor on create flow
- Vendor select disabled with hint until brand chosen
- Selecting brand A then brand B clears the vendor selection and refetches
- Vendor list filters to vendors assigned to the chosen brand
- Submit POST body carries brand_id
- Edit-draft mode: BrandSelect disabled, brand_id present in submit body unchanged
- Edit-revise mode: same

`frontend/tests/po-detail.spec.ts` additions:
- Brand block panel renders on PO detail; legal_name + address + country + tax_id present
- tax_id row hidden when empty

`frontend/tests/role-rendering.spec.ts` additions:
- ADMIN sees BRANDS sidebar item; SM does not (per `canManageBrands`); VENDOR / FREIGHT_MANAGER / QUALITY_LAB / PROCUREMENT_MANAGER never see it

## Decisions

- **Single edit page hosts both attribute form and vendor assignment.** Mirrors `/products/[id]/edit` rather than splitting into separate read / edit / vendors routes.
- **Status changes via buttons on both the list table action column and the edit page.** List Deactivate / Reactivate is fast for the common case; edit-page version exists because that page already loads the brand.
- **`createBrand` redirects to `/brands/{id}/edit`** rather than `/brands` so the user can immediately assign vendors. A brand with no vendors is dead weight.
- **BrandSelect on PO create is required from day one** — no graceful degradation if `listBrands` fails. If brands cannot load the form blocks with an error state.
- **Vendor cascade resets on brand change.** Switching brand mid-form clears the vendor selection. No confirm dialog.
- **PO list shows a Brand column on desktop only.** Mobile cards already truncate aggressively; one extra `Brand:` line is enough.
- **PO detail brand block sits above the legacy Buyer block.** Both visible. Legacy `buyer_name` + `buyer_country` are dead fields and will be dropped after this iter; keeping them visible during the transition makes a stale-data audit trivial.
- **`canViewBrands` includes SM** so SM creating a PO can navigate to the brand list to see context. SM cannot create / edit / deactivate.
- **Default Brand has no special UI handling.** Its placeholder `legal_name="Default Brand — please update"` is the prompt to ADMIN.

## Out of scope (subsequent iters)

- Brand-scoped marketplace accounts (FBA seller IDs, FNSKU, ASIN, fulfilment-centre code) — separate marketplace-integration iter.
- Brand-scoped user access (Brand A's ops manager sees only Brand A's POs / invoices / shipments) — iter 111.
- `Vendor.tax_id`, `Shipment.pallet_count`, `Shipment.export_reason` — iter 110.
- Dropping the legacy `purchase_orders.buyer_name` and `purchase_orders.buyer_country` columns — pending the schema-mutation tool. Iter 108 PDF fallback `or po.buyer_name` stays defensive until then.
- `BrandRepository.list_brand_vendors` N+1 refactor to a single JOIN — small backend cleanup iter.
- Cert / packaging / shipment requirement matrices scoped per brand — separate iter when first needed.
- Activity feed UI extension to show metadata payloads on BRAND_VENDOR_ASSIGNED / UNASSIGNED rows (vendor name) — not blocking.

## Notes

(Filled at iteration close.)
