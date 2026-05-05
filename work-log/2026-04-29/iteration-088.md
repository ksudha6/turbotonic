# Iteration 088 — Phase 4.3 Tier 3: Invoice create flow retrofit

## Context

Phase 4.3 read surfaces closed at iter 086 (`/invoices` list) and iter 087 (`/invoice/[id]` detail). The remaining pre-revamp surface is the create-invoice modal that opens from `(nexus)/po/[id]` when a VENDOR (or ADMIN) presses "Create Invoice" on an ACCEPTED PROCUREMENT PO.

The modal is `frontend/src/lib/components/CreateInvoiceDialog.svelte`: 113 lines, raw `<table class="table">`, native `<input class="qty-input">`, native `<button class="btn btn-secondary">` / `<button class="btn btn-primary">`, no responsive layout, no accessible name on the dialog root, no testids. It is the last component in `frontend/src/lib/components/` — iter 081 (negotiation pieces) and iter 082 (`MilestoneTimeline.svelte`) retired all prior files. Deleting it empties the directory.

OPEX flow does not use this modal. `handleCreateOpexInvoice` calls `createInvoice(poId)` with no line items and navigates directly to `/invoice/{id}`. Only PROCUREMENT POs need per-line quantity entry.

## JTBD

As a vendor invoicing a PROCUREMENT PO, I want to enter quantities per line in a modal that matches the rest of the Phase 4.0 surface — so I see remaining-quantity constraints inline, the Create button is disabled until I enter a valid quantity, and the modal renders correctly on a 390px phone the same way the rest of the PO detail page does.

## Tasks

1. Create `frontend/src/lib/invoice/InvoiceCreateModal.svelte` using Phase 4.0 primitives:
   - Props: `lines: RemainingLine[]`, `onConfirm(lineItems: InvoiceLineItemCreate[])`, `onCancel()`.
   - Internal state: `quantities: Record<string, string>` keyed by part_number (strings because Phase 4.0 `Input` is string-only — same precedent as `PoForm.LineFormState` from iter 085 and `PoAddLineDialog` from iter 082).
   - Default quantity per row = `String(line.remaining)` so the common case (invoice everything remaining) is one click.
   - Lines with `remaining === 0` render as disabled rows.
   - Validation: at least one row has parsed qty > 0; per-row qty > remaining is clamped at submit (not user-blocked) — same UX as the legacy modal's `max` attribute.
   - Footer: Phase 4.0 `Button` secondary (Cancel) + primary (Create), Create disabled when `allZero`.
   - Layout: desktop (`>=768px`) renders a `<table>` with columns Part Number / Description / Ordered / Invoiced / Remaining / Invoice Qty; mobile renders one card per line with the qty Input full-width.
   - Root: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` on a `crypto.randomUUID()`-keyed `<h2>` (iter 080 convention for titled containers).
   - testids: `invoice-create-modal`, `invoice-create-row-{part_number}`, `invoice-create-qty-input-{part_number}`, `invoice-create-cancel`, `invoice-create-confirm`.

2. Wire on `(nexus)/po/[id]/+page.svelte`:
   - Replace the `import CreateInvoiceDialog from '$lib/components/CreateInvoiceDialog.svelte'` line with `import InvoiceCreateModal from '$lib/invoice/InvoiceCreateModal.svelte'`.
   - Replace the `<CreateInvoiceDialog ... />` block. Props unchanged (lines / onConfirm / onCancel).

3. Delete `frontend/src/lib/components/CreateInvoiceDialog.svelte`.

4. New permanent specs in `frontend/tests/invoice-create.spec.ts`:
   - VENDOR on ACCEPTED PROCUREMENT PO clicks Create Invoice → modal mounts with `invoice-create-modal` testid + visible Phase 4.0 styling.
   - Modal renders one row per remaining line with Invoice Qty input pre-filled to the remaining amount.
   - Lines with `remaining === 0` render but the qty input is disabled.
   - Setting all quantities to 0 disables the Create button.
   - Cancel closes the modal without firing the API.
   - Create posts only non-zero rows and navigates to `/invoice/{id}`.
   - At 390px viewport, rows render as cards (testid `invoice-create-row-{partNumber}` resolves uniquely; mobile card layout asserted by checking the qty input is rendered full-width).
   - Modal root has `role="dialog"` + `aria-modal="true"` + `aria-labelledby` resolving to the visible `<h2>` "Create Invoice".

## Tests

### Existing test impact

- `frontend/tests/role-rendering.spec.ts:340` and `:377`: assert the action rail Create Invoice button is visible. They never click the button — no dialog markup assertion. Continue passing unchanged.
- `frontend/tests/po-detail.spec.ts:291,310`: assert `po-action-create-invoice` testid presence/absence on the action rail. No dialog assertions. Continue passing unchanged.
- No existing test targets the `CreateInvoiceDialog`'s `.dialog` / `.qty-input` / `.btn-primary` markup. Confirmed via grep — the legacy class selectors banned by the new selector policy never made it into a test file. Net: zero existing-test fixups required.

### New permanent specs (`frontend/tests/invoice-create.spec.ts`)

- 8 specs as listed under Tasks step 4. Mocks: `mockUser('VENDOR')`, `getRemainingQuantities` returning two PROCUREMENT lines (PN-001 remaining 5, PN-002 remaining 0), `createInvoice` returning `{ id: 'inv-new-1', ... }`, `goto` capture verifying `/invoice/inv-new-1`. testid-only selectors per the Phase 4.x policy.

## Notes

Pure structural retrofit. The new `InvoiceCreateModal` mirrors iter 087's `InvoiceDisputeModal` pattern (Phase 4.0 `Button` + native input, `crypto.randomUUID()`-keyed `aria-labelledby`) but adds a responsive desktop-table / mobile-cards split because the create surface needs more columns. Both layouts share the same `invoice-create-row-{partNumber}` and `invoice-create-qty-input-{partNumber}` testids — Playwright strict-mode collisions resolved via parent-scoped lookups (`getByTestId('invoice-create-table').getByTestId(...)` for desktop, `getByTestId('invoice-create-cards').getByTestId(...)` for mobile), the same precedent iter 086 set with `invoice-table-desktop` / `invoice-table-mobile`.

Quantity state lives in a `Record<string, string>` keyed by `part_number` so the Phase 4.0 `Input` primitive (string-only `bind:value`, same shape as `PoForm.LineFormState` in iter 085) two-way binds without an integer-shaped wrapper. Submit re-parses to int and clamps at `Math.min(parsed, line.remaining)` — the legacy modal relied on the native `max` attribute alone, which disagrees across browsers when the user types a value and presses Enter. Clamp at submit is more deterministic; one new spec asserts that an entered "99" comes through to the API as the remaining 7.

The 390px sticky-bottom test had to click "Create Invoice" through the action rail's overflow menu, not the inline rail — `PoActionRail` puts secondary primaries (Create Invoice is secondary on ACCEPTED PROCUREMENT, after Post Milestone) into the overflow at sticky-bottom. The `po-detail-page-rail-mobile` wrapper testid (added in iter 077) is the right scope to find the visible rail at 390px; using `.first()` on `po-action-rail` picks the inline rail which is `display:none` at <768px and fails the click.

`frontend/src/lib/components/CreateInvoiceDialog.svelte` deleted. `frontend/src/lib/components/` still contains `NotificationBell.svelte` (consumed by Phase 4.0 `TopBar`) and `RejectDialog.svelte` (used in pre-revamp `po-list.spec.ts` / `vendor.spec.ts` / `product.spec.ts` test fixtures). The directory does not retire this iter; that's a Phase 4 close-out task once the remaining pre-revamp tests get migrated.

OPEX flow unchanged. `handleCreateOpexInvoice` still calls `createInvoice(poId)` with no line items and skips the modal entirely — `(nexus)/po/[id]/+page.svelte` branches before opening the dialog when `po.po_type === 'OPEX'`. The new modal is PROCUREMENT-only by design.

No DDD vocab additions per CLAUDE.md rule 6.1 — this is pure UI structural retrofit; the underlying domain model (`RemainingLine`, `InvoiceLineItemCreate`, `Invoice`) is unchanged.

696 backend (no change) + 308 Playwright (300 → 308, +8).
