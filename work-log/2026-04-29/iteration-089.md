# Iteration 089 — Phase 4.4 Tier 1: `/vendors` + `/vendors/new` revamp

## Context

Phase 4.4 starts with the vendor surface, the smallest of the four remaining pre-revamp routes (vendors, products, shipments, auth).

Pre-revamp state:
- `/vendors` (`frontend/src/routes/vendors/+page.svelte`, 162 lines): inline `<select class="select">` filters, raw `<table class="table">`, native `.btn-danger`/`.btn-success` action buttons, hand-rolled `.badge` pills. Permission: SM only (per `canManageVendors`).
- `/vendors/new` (`frontend/src/routes/vendors/new/+page.svelte`, 134 lines): native `<input class="input">`, `<select class="select">`, `<textarea class="textarea">`, hand-rolled `.form-grid`. No textarea primitive in Phase 4.0 (same gap iter 087 hit with `InvoiceDisputeModal`).

Existing `frontend/tests/vendor.spec.ts` has 9 tests; 8 target vendor markup with brittle selectors (`page.fill('#name', ...)`, `page.locator('tbody')`, `page.waitForSelector('table')`). One unrelated test (`'PO form prefills buyer fields with defaults'`) already uses testids and is left alone. The 8 vendor-specific tests migrate to the new testid namespace.

## JTBD

As a Supply Manager managing the vendor master list, I want the vendor list and create-vendor form to mount under the same `(nexus)` AppShell + Sidebar + TopBar I see on `/po` and `/invoices`, with consistent Phase 4.0 primitives — so the vendor surface stops being the only management page that still renders the legacy chrome.

## Tasks

1. New components in `frontend/src/lib/vendor/`:
   - `VendorListFilters.svelte` — Status select (All / Active / Inactive) + Vendor Type select (All Types / Procurement / OpEx / Freight / Misc) + Clear button. Mobile-collapsing panel via `Filters` toggle (mirror of `PoListFilters`).
   - `VendorListTable.svelte` — Phase 4.0 `StatusPill` (ACTIVE → green, INACTIVE → gray), Deactivate / Reactivate Buttons per row. Responsive: desktop `<table>` (testid `vendor-table-desktop`) with rows; mobile `<ul>` of cards (testid `vendor-table-mobile`). Row testid `vendor-row-{id}`. Action callback `onAction(id, 'deactivate' | 'reactivate')`.
   - `VendorForm.svelte` — Phase 4.0 `PanelCard` + `FormField` + `Input` + `Select` + native `<textarea>` (no Phase 4.0 textarea primitive yet, same as iter 087). Cancel + Submit Buttons in a sticky-on-mobile footer (mirror of `PoForm`'s G-12 #4). testids: `vendor-form`, `vendor-form-name`, `vendor-form-country`, `vendor-form-vendor-type`, `vendor-form-address`, `vendor-form-account-details`, `vendor-form-error`, `vendor-form-cancel`, `vendor-form-submit`.

2. New routes:
   - `frontend/src/routes/(nexus)/vendors/+page.svelte` — AppShell + UserMenu + PageHeader (title "Vendors", action snippet rendering a `Button` linking to `/vendors/new` for SM/ADMIN — testid `vendor-page-header-action`). Mounts `VendorListFilters` + `VendorListTable`. Filter narrowing via `$effect` (mirror of iter 086 `(nexus)/invoices`). LoadingState / EmptyState / ErrorState in the standard arrangement.
   - `frontend/src/routes/(nexus)/vendors/+page.ts` — same redirect-on-no-permission logic as legacy.
   - `frontend/src/routes/(nexus)/vendors/new/+page.svelte` — AppShell + UserMenu + PageHeader (title "Create Vendor"). Mounts `VendorForm`. On submit: POST → redirect to `/vendors`. On Cancel: `goto('/vendors')`.
   - `frontend/src/routes/(nexus)/vendors/new/+page.ts` — same redirect-on-no-permission logic as legacy.

3. Delete legacy routes:
   - `frontend/src/routes/vendors/+page.svelte`
   - `frontend/src/routes/vendors/+page.ts`
   - `frontend/src/routes/vendors/new/+page.svelte`
   - `frontend/src/routes/vendors/new/+page.ts`
   - The whole `frontend/src/routes/vendors/` tree retires after this iter.

4. `frontend/src/routes/+layout.svelte` — extend `isRevampRoute` with `pathname === '/vendors'` exact match + `pathname.startsWith('/vendors/')` prefix match.

5. Migrate existing `frontend/tests/vendor.spec.ts` specs from class/tag/id selectors to the testid namespace:
   - `vendor list loads and displays vendors` → use `getByTestId('vendor-table-desktop')` and `vendor-row-{id}` rows.
   - `create vendor form submits and redirects` → use `vendor-form-name` / `vendor-form-country` / `vendor-form-submit`.
   - `deactivate vendor updates status badge` → use `vendor-row-action-{id}` + StatusPill testid.
   - `reactivate vendor updates status badge` → same.
   - `vendor list shows UUID column` → migrate to use `vendor-row-id-{id}` testid.
   - `vendor create form renders country as select dropdown` → assert `vendor-form-country` is a `combobox` role (Phase 4.0 Select wraps native `<select>`).
   - `vendor create form shows country options from reference data` → assert option count via the country select.
   - `vendor create form renders address and account_details fields` → use field testids.
   - `vendor create form submits address and account_details` → use field testids.

6. New permanent specs in `vendor.spec.ts`:
   - AppShell mount on `/vendors` and `/vendors/new`.
   - Vendor list filter narrowing (status filter narrows rows).
   - Vendor list error + retry path.
   - Vendor list empty-state copy when filter has no matches.
   - VENDOR-role redirect from `/vendors` (already covered by role-rendering.spec.ts — confirm no regression).
   - Mobile (390px) renders cards (testid `vendor-table-mobile`).

## Tests

### Existing test impact

- `frontend/tests/vendor.spec.ts` — 8 of 9 specs migrate to the new testid surface. The unrelated `'PO form prefills buyer fields with defaults'` spec in the same file is left as-is (it tests `/po/new`, not vendors, and already uses testids).
- `frontend/tests/role-rendering.spec.ts:355` (`'VENDOR visiting /vendors redirects to /dashboard'`) — uses `goto('/vendors')` + URL assertion only, no vendor markup. Continues passing under the new route.
- `frontend/tests/auth-flow.spec.ts` and others that pass through `/vendors` as a deep link — no markup assertions. Continue passing.
- No other tests target vendor markup. Confirmed via grep.

### New permanent specs

Listed in Tasks step 6 above. Mocks: catch-all + `auth/me` + `unread-count` + `vendors` (with status/vendor_type query handling) + `reference-data` + the per-test action handlers.

## Notes

Pure structural retrofit. Vendor surface ports cleanly because the backend already speaks codes (`status`, `vendor_type`) the new `Select` primitive can bind directly — no DTO reshaping required. The new `frontend/src/lib/vendor/` directory parallels `frontend/src/lib/po/`, `frontend/src/lib/invoice/`, and `frontend/src/lib/ui/`; the four-namespace layout (`po/` / `invoice/` / `vendor/` / shared `ui/`) is the natural outcome of Phase 4.x.

`VendorListTable` mirrors iter 086's `InvoiceListTable` for the desktop-table / mobile-cards split — same testid namespace shape (`vendor-table-desktop` / `vendor-table-mobile` parents, shared `vendor-row-{id}` row testids). At 390px the desktop table is `display:none` but still exists in the DOM, so tests scope row lookups via the visible parent (`getByTestId('vendor-table-mobile').getByTestId('vendor-row-...')`) per the iter 086 precedent.

`VendorForm` does not use `FormCard` for the same reason iter 085's `PoForm` doesn't: `FormCard`'s single-title constraint either duplicates the page H1 or skips the visible heading entirely, and its non-sticky footer breaks the mobile-sticky requirement. Instead the form uses individual `PanelCard`s for each section group + a custom sticky-on-mobile footer with `env(safe-area-inset-bottom)` padding. Address + Account Details remain native `<textarea>` because Phase 4.0 has no textarea primitive (same gap iter 087's `InvoiceDisputeModal` and the legacy form hit). Adding one is a backlog candidate once a third consumer arrives.

The `'PO form prefills buyer fields with defaults'` spec at the bottom of `vendor.spec.ts` was historically misplaced — it tests `/po/new` and already used testid selectors. Left it intact during the migration. It would more naturally live in `po-form.spec.ts`; that move is a separate cleanup PR not blocking iter 089.

Existing iter-validated routes (`role-rendering.spec.ts:355` — VENDOR redirect from `/vendors`) continue to pass through the new `(nexus)` route since the redirect happens at the load-function layer in `+page.ts` before any markup renders, and the redirect target (`/dashboard`) is unchanged.

`isRevampRoute` extended with both `pathname === '/vendors'` exact match (list) and `pathname.startsWith('/vendors/')` prefix (anything under `/vendors/`, currently just `/new`). Same shape as the iter 077 PO carve-out + iter 086 invoice list + iter 087 invoice detail.

No DDD vocab additions per CLAUDE.md rule 6.1 — pure UI structural retrofit; the underlying Vendor / VendorStatus / VendorType domain remains unchanged.

696 backend (no change) + 315 Playwright (308 → 315, +7).
