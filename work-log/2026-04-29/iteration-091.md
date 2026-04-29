# Iteration 091 — Phase 4.5 Tier 2: `/products/new` create form revamp

## Context

Following iter 090 (`/products` list under `(nexus)`), this iter ports the matching create form. Today's `/products/new` is 131 lines — slightly smaller than iter 089's `VendorForm` (134 lines). The shape is similar: native `<input class="input">`, `<select class="select">`, `<textarea class="textarea">`, hand-rolled 2-column `.form-grid`, native Cancel `<a>` + Submit `<button>` row.

The legacy page filters vendors by `status: 'ACTIVE'` on the `listVendors` call — only active vendors are eligible to be selected when creating a product. The revamp preserves this constraint.

The 409-conflict error message ("A product with this part number already exists for this vendor.") is part of the form's domain semantics — the backend uses `(vendor_id, part_number)` as a uniqueness constraint per iter 029. The revamp preserves this branch.

## JTBD

As an SM creating a new product, I want the create form to mount under the same `(nexus)` AppShell and use the same Phase 4.0 form primitives I see on `/vendors/new` and `/po/new`, with consistent error surfaces and a sticky-on-mobile footer.

## Tasks

1. New component `frontend/src/lib/product/ProductCreateForm.svelte` — mirrors iter 089's `VendorForm` shape:
   - Phase 4.0 `PanelCard` ("Product Details") + `FormField` + `Input` + `Select` + native `<textarea>` for manufacturing_address.
   - Vendor select shows only ACTIVE vendors (filtered upstream by the page).
   - Validation: vendor_id required, part_number required (trim).
   - Sticky-on-mobile footer with `env(safe-area-inset-bottom)` padding (iter 089 precedent).
   - testids: `product-create-form`, `product-form-vendor`, `product-form-part-number`, `product-form-description`, `product-form-manufacturing-address`, `product-form-error`, `product-form-cancel`, `product-form-submit`.

2. New routes:
   - `(nexus)/products/new/+page.svelte` — AppShell + UserMenu + PageHeader ("Create Product"). Mounts `ProductCreateForm`. On submit POST → redirect to `/products`. On Cancel → `goto('/products')`.
   - `(nexus)/products/new/+page.ts` — same redirect-on-no-permission as legacy.

3. Delete `frontend/src/routes/products/new/+page.svelte` and `+page.ts`.

4. `isRevampRoute` extended with `pathname === '/products/new'` exact match. (Cannot use `/products/` prefix yet because that would catch `/products/[id]/edit` which is iter 092.)

5. Migrate the 2 existing `/products/new` specs in `product.spec.ts` from id selectors (`#vendor_id`, `#part_number`, `#manufacturing_address`) to the new testid namespace.

6. New permanent specs:
   - AppShell mount on `/products/new`.
   - Form blocks submit when vendor unselected.
   - Form blocks submit when part_number empty.
   - 409 error message renders inline.
   - Cancel returns to `/products`.

## Tests

### Existing test impact

- `product.spec.ts:63` (`'product create form renders manufacturing_address field'`) — migrate from `page.locator('#manufacturing_address')` to `getByTestId('product-form-manufacturing-address')`.
- `product.spec.ts:79` (`'product create form submits manufacturing_address'`) — migrate from `page.selectOption('#vendor_id', ...)` and `page.fill('#part_number', ...)` to testids; replace `getByRole('button', { name: 'Create Product' })` with `getByTestId('product-form-submit')` for resilience.
- `product.spec.ts:122` (`'product edit form shows existing manufacturing_address'`) — targets `/products/[id]/edit` (iter 092), unchanged.

### New permanent specs

5 specs as listed in Tasks step 6.

## Notes

Pure structural retrofit. `ProductCreateForm` mirrors iter 089's `VendorForm` exactly — same `PanelCard` + `FormField` + `Input` + `Select` + native `<textarea>` shape, same sticky-on-mobile footer with `env(safe-area-inset-bottom)` padding, same export-type pattern (`ProductCreateFields`).

The legacy 409 detection (`err.message.includes('409')`) carries over verbatim — the backend's uniqueness constraint on `(vendor_id, part_number)` from iter 029 is unchanged. The user-facing copy ("A product with this part number already exists for this vendor.") matches the legacy page so the assertion in `'product create form surfaces 409 conflict inline'` reflects the actual constraint, not a UI choice.

`isRevampRoute` extended with `pathname === '/products/new'` exact match. Cannot widen to `pathname.startsWith('/products/')` yet because that would catch `/products/[id]/edit` (iter 092), which still renders the legacy chrome. The carve-out lifts to a prefix once iter 092 lands.

The 2 existing `/products/new` specs migrated cleanly from `#vendor_id` / `#part_number` / `#manufacturing_address` id selectors to the testid namespace. The legacy `getByRole('button', { name: 'Create Product' })` selector also moved to `getByTestId('product-form-submit')` for resilience — the H1 also reads "Create Product", and a future heading-as-banner change could collide on the role+name lookup.

No DDD vocab additions per CLAUDE.md rule 6.1.

696 backend (no change) + 327 Playwright (322 → 327, +5).
