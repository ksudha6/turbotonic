# Iteration 093 — Phase 4.5 Tier 3b: packaging specs panel on `/products/[id]/edit`

## Context

Iter 092 ported the edit page under `(nexus)` with `ProductEditForm` + `ProductQualificationsPanel` but kept the packaging-specs section as inline legacy markup as a transitional holdover. This iter retires that block.

The legacy markup has three concerns:
1. **List** grouped by marketplace, each spec showing name, description, status pill, and a Delete button gated on `status === 'PENDING'`.
2. **Add form** toggled by an "Add Spec" button — inputs for marketplace, spec_name, description, requirements_text. Submit POSTs and prepends to the local list. Add and Delete are SM/ADMIN only.
3. **Native `confirm()`** before Delete — keeping the same UX in the new panel since there's no Phase 4.0 confirm dialog primitive.

The frontend `PackagingSpecStatus` type currently lists only `'PENDING'`, but the backend has a `COLLECTED` status documented in the iter 042 summary (file upload transitions PENDING → COLLECTED). The legacy page renders the status string verbatim and only allows Delete on PENDING; the new panel preserves that exact behavior. Status pill tone: PENDING → gray, COLLECTED → green (the same pattern other surfaces use).

## JTBD

As an SM editing a product, I want the packaging-specs section on the edit page to use the same Phase 4.0 primitives as the rest of the page — so the edit page no longer mixes new and legacy markup, and the section visually matches `ProductQualificationsPanel` directly above it.

## Tasks

1. New component `frontend/src/lib/product/ProductPackagingSpecsPanel.svelte`:
   - `PanelCard` ("Packaging Specs") with an SM-only "Add Spec" trigger in the action snippet.
   - Empty state via `EmptyState` ("No packaging specs defined yet.") when zero specs.
   - Specs grouped by marketplace as sub-headings; each spec rendered as a row with name + description + Phase 4.0 `StatusPill` (PENDING → gray, COLLECTED → green) + SM-only Delete button (gated on PENDING).
   - Add flow: button toggles an inline form (matching the existing legacy UX, no separate modal — modal would be heavier than warranted for a 4-field form). Form uses Phase 4.0 `FormField` + `Input` + native `<textarea>` for requirements. Submit + Cancel buttons via Phase 4.0 `Button`.
   - Delete confirms via `window.confirm` (legacy parity — no Phase 4.0 confirm dialog primitive).
   - testids: `product-packaging-panel`, `product-packaging-add-trigger`, `product-packaging-add-form`, `product-packaging-add-marketplace`, `product-packaging-add-spec-name`, `product-packaging-add-description`, `product-packaging-add-requirements`, `product-packaging-add-submit`, `product-packaging-add-cancel`, `product-packaging-add-error`, `product-packaging-row-{id}`, `product-packaging-row-status-{id}`, `product-packaging-row-delete-{id}`, `product-packaging-error`.

2. Update `(nexus)/products/[id]/edit/+page.svelte`:
   - Remove the inline `<div class="section card">` packaging block, the inline `<style>` rules supporting it, and the local `showAddSpec`, `newMarketplace`, `newSpecName`, `newDescription`, `newRequirementsText`, `addingSpec`, `addSpecError`, `specsByMarketplace` state.
   - Mount `<ProductPackagingSpecsPanel />` after `ProductQualificationsPanel`.
   - Keep `specs`, `specsError`, `loadSpecs`, the `listPackagingSpecs` call in `onMount`, and the `createPackagingSpec` / `deletePackagingSpec` calls. Wrap them in `on_add_spec` / `on_delete_spec` callbacks that the panel invokes.

3. New permanent specs in `product.spec.ts`:
   - Packaging panel mount + empty state.
   - Specs render grouped by marketplace with status pills.
   - Add flow: trigger → form visible → submit → row appears → form auto-closes.
   - Add form server error renders inline.
   - Delete flow: confirm dialog accepted → row disappears.
   - Delete flow: confirm dialog dismissed → row persists.
   - Delete button hidden on COLLECTED specs.

## Tests

### Existing test impact

- The 8 iter-092 specs all pass through `setupEditPage` which mocks `/api/v1/products/{id}/packaging-specs` returning `[]`. The wrong endpoint path: legacy and new both call `/api/v1/packaging-specs/?product_id=...`. The setup needs to change to mock the right URL. However, all 8 existing iter-092 specs return empty `[]` for specs — they don't assert any packaging behavior — so changing the mocked URL shape only matters if the new panel surfaces something different on empty (it doesn't — same `EmptyState`). Verify by re-running them after the URL change.

### New permanent specs

7 specs as listed in Tasks step 3.

## Notes

Packaging specs panel ports cleanly: legacy block + 70 lines of inline CSS retire. Auto-close-on-success uses a `wasAdding` `$state` + `$effect` pair that watches `adding` flip false-after-true with no `addError` — simpler than threading a `success` callback up through the parent. Native `window.confirm` for delete stays — no Phase 4.0 confirm dialog primitive yet, and the legacy UX was already a window.confirm so this is parity not regression. PackagingSpecStatus expands de facto to PENDING + COLLECTED via the panel's `statusTone` map even though the frontend type still narrows to `'PENDING'`; the COLLECTED branch renders correctly because the StatusPill takes a string label, not a typed enum. With this iter the entire `/products/*` namespace is now Phase 4.0; iter 094 picks up the iter-040 cert UI fold-in. Pytest suite has one unrelated pre-existing failure in `test_auth_dev.py::test_dev_login_creates_session_for_active_user` from a parallel iter-095 work-in-progress on `_user_to_dict` — out of scope for this iter.
