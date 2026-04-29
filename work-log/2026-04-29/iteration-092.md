# Iteration 092 — Phase 4.5 Tier 3a: `/products/[id]/edit` details + qualifications

## Context

The legacy edit page (`frontend/src/routes/products/[id]/edit/+page.svelte`, 436 lines) bundles three concerns: (1) product details form (vendor + part_number readonly, description + manufacturing_address editable), (2) qualifications panel (list + add + remove), (3) packaging specs panel (list grouped by marketplace + add form + delete). At 436 lines this is the largest pre-revamp page; splitting per the iter discipline:

- **iter 092 (this one)**: page mount under `(nexus)` + details form + qualifications panel.
- **iter 093**: packaging specs panel — the most elaborate section (add form, grouped list, delete confirm).
- **iter 094**: iter 040 cert UI (cert upload flow, expiry alerts, dashboard surfaces).

The packaging block renders inside the new `(nexus)` shell as a temporary holdover with its current legacy markup intact for iter 092. It looks out of place visually but the underlying behavior is unchanged. Iter 093 retires that block.

## JTBD

As an SM editing an existing product, I want the page to mount under the same `(nexus)` AppShell and use Phase 4.0 primitives for the details form and qualifications panel — so the most-used path on this page (description + qualifications) lands on the new design while the packaging specs section gets its own focused iter.

## Tasks

1. New components in `frontend/src/lib/product/`:
   - `ProductEditForm.svelte` — `PanelCard` ("Product Details") with vendor + part_number rendered as readonly `AttributeList` rows, then editable `Input` (description) + native `<textarea>` (manufacturing_address) for SM/ADMIN. View-only roles see the editable fields rendered as `AttributeList` rows too. Sticky-on-mobile footer with Cancel + Save buttons (mirror of `ProductCreateForm`). testids: `product-edit-form`, `product-edit-vendor` (readonly value), `product-edit-part-number` (readonly value), `product-edit-description`, `product-edit-manufacturing-address`, `product-edit-error`, `product-edit-cancel`, `product-edit-save`. View-only roles see a single `product-edit-back` button instead of Cancel + Save.
   - `ProductQualificationsPanel.svelte` — `PanelCard` ("Qualifications"). When empty → `EmptyState` with copy "No qualifications assigned." When populated → list with `StatusPill` (tone blue) showing target_market alongside the qualification name. SM/ADMIN see a Remove button per row + an "Add qualification" `Select` + `Button` row at the bottom; view-only roles see the list only. testids: `product-qualifications-panel`, `product-qualification-row-{qtId}`, `product-qualification-remove-{qtId}`, `product-qualification-add-select`, `product-qualification-add-button`, `product-qualifications-error`.

2. New routes:
   - `(nexus)/products/[id]/edit/+page.svelte` — AppShell + UserMenu + PageHeader ("Edit Product"). Mounts `ProductEditForm` + `ProductQualificationsPanel`. Until iter 093, also renders the existing packaging specs block inline as legacy markup (with all the existing handlers).
   - `(nexus)/products/[id]/edit/+page.ts` — same redirect-on-no-permission as legacy.

3. Delete `frontend/src/routes/products/[id]/edit/+page.svelte` and `+page.ts`. The legacy `routes/products/[id]/` tree retires (only `edit` was in there).

4. `isRevampRoute` widen: replace `pathname === '/products/new'` with `pathname.startsWith('/products/')` prefix. After this iter, the entire `/products/*` namespace is under `(nexus)`.

5. Migrate existing spec `'product edit form shows existing manufacturing_address'` from `page.locator('#manufacturing_address')` to `getByTestId('product-edit-manufacturing-address')`.

6. New permanent specs:
   - AppShell mount on `/products/[id]/edit`.
   - Vendor + Part Number render as readonly values.
   - SM can edit description + manufacturing_address; submit posts and redirects.
   - VENDOR sees readonly fields and a Back button only (no Save).
   - Qualifications panel empty state.
   - Qualifications list shows target_market pill.
   - Add qualification flow: select + Add → row appears; the just-added qual disappears from the dropdown.
   - Remove qualification flow: Remove → row disappears.

## Tests

### Existing test impact

- `product.spec.ts:233` (`'product edit form shows existing manufacturing_address'`) — migrate from `#manufacturing_address` id to testid. Otherwise unchanged.
- No other tests target the edit page.

### New permanent specs

8 specs as listed in Tasks step 6. Mocks: catch-all + auth/me + unread-count + reference-data + vendors + qualification-types + the per-product GET + assign/remove qualification action handlers.

## Notes

Two-component split worked cleanly. `ProductEditForm` handles details (vendor + part_number readonly via hand-rolled markup with explicit testids — `AttributeList` rejects per-row testids, so the readonly fields are spans with their own testids). `ProductQualificationsPanel` wraps `PanelCard` + `EmptyState` for the empty case, list of rows with `StatusPill tone="blue"` showing target_market, plus an SM-only Add row with `Select` + `Button`.

The packaging specs section stays as legacy markup inline on the new (nexus) page. The styling is inherited from `global.css` (`.input`, `.select`, `.btn-primary`, `.status-pill`, etc.) plus a few inlined rules in the page's `<style>` so it renders correctly inside the AppShell where some of the legacy global rules don't apply uniformly. This is the only surface in the codebase right now where new and legacy markup share a page; iter 093 retires it.

`isRevampRoute` widened to `pathname.startsWith('/products/')`. After this iter, the entire `/products/*` namespace renders under the new shell — no more partial-revamp carve-outs in the layout. The only remaining pre-revamp routes are `/shipments/*`, `/login`, `/register`, `/setup`.

The `+page.ts` redirect logic carries over verbatim: only `canManageProducts` roles (SM/ADMIN) can land. View-only roles (VENDOR/PM/QL) get redirected to `/products` if they can view, else `/dashboard`. The view-only branch in `ProductEditForm` (Back button only, readonly text spans) is therefore dead code on this page right now; keeping it scaffolds a future iter that would relax the redirect to allow read-only viewing of the edit page (currently not on the backlog).

The qualifications add-flow test initially failed because I mocked the wrong endpoint shape (`.../qualifications/qt-fda` instead of `.../qualifications` with the type id in the body). Caught quickly via Playwright's clear locator-not-found error pointing back to the row testid. Verified via `frontend/src/lib/api.ts:434` — `assignQualification` POSTs to `/api/v1/products/{id}/qualifications` with `{ qualification_type_id: ... }` body.

Existing `'product edit form shows existing manufacturing_address'` spec migrated cleanly from `#manufacturing_address` to `getByTestId('product-edit-manufacturing-address')`.

No DDD vocab additions per CLAUDE.md rule 6.1.

696 backend (no change) + 335 Playwright (327 → 335, +8).
