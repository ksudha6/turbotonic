# Iteration 097 — Phase 4.6 Tier 1: `/shipments/[id]` shell port + line items panel

## Context

`/shipments/[id]` is the last legacy aggregate-detail page. Every other detail surface (`/po/[id]`, `/invoice/[id]`, `/products/[id]/edit`) has been ported under the `(nexus)` AppShell layout group and rebuilt on Phase 4.0 primitives. The shipments page still renders against the pre-revamp tree: no AppShell, no Sidebar, no TopBar, raw `<table>` + inline `<input>` cells, hand-rolled `.status-badge` colors keyed on `status-{lower}` class, save state communicated by a transient `<span class="save-ok">`.

Current page at [frontend/src/routes/shipments/[id]/+page.svelte](frontend/src/routes/shipments/[id]/+page.svelte) is 313 lines and exercises a small surface:
- `getShipment(id)` on mount → renders header + meta card + line items table.
- Inline-edit drafts indexed by `part_number` for `net_weight` / `gross_weight` / `package_count` / `dimensions` / `country_of_origin`. Edit gated on `status === 'DRAFT' || status === 'DOCUMENTS_PENDING'` (iter 044).
- `updateShipmentLineItems(id, {line_items})` Save → re-init drafts, transient "Saved" pill (3s setTimeout).
- `downloadPackingListPdf(id, shipment_number)` and `downloadCommercialInvoicePdf(id, shipment_number)` browser-download buttons.

Backend surface beyond what the current page consumes (per iter 046 / iter 074) is **out of scope here** and lives in iter 098 (A2 — docs panel + readiness + mark-ready) and a follow-up iter (booking + mark-shipped). This iter is the structural shell port plus a clean line items panel extraction. No new functionality.

There is no `/shipments` list page, no Sidebar entry, no deep link from PO detail today. The page is reachable by direct URL only; iter 097 preserves that — adding navigation surface is a separate concern.

There is no existing Playwright spec for the shipments page (`frontend/tests/shipment*.spec.ts` does not exist), so the iter creates the file from scratch and selects on testid from day one. No test migration.

The pattern to follow is the [`/products/[id]/edit`](frontend/src/routes/(nexus)/products/[id]/edit/+page.svelte) shape (iter 092 → 094): page-level state + onMount fetch, Phase 4.0 `DetailHeader` + `StatusPill` for the header, panels rendered as components from a new `frontend/src/lib/shipment/` directory. Header download buttons mirror the existing pattern but use Phase 4.0 `Button variant="secondary"`. Status pill tone covers all five `ShipmentStatus` values (`DRAFT`/`DOCUMENTS_PENDING`/`READY_TO_SHIP`/`BOOKED`/`SHIPPED` since iter 074) so the mapping is correct on first port even though only `DRAFT`/`DOCUMENTS_PENDING`/`READY_TO_SHIP` are reachable from the current edit-only flow.

## JTBD

As any role with read access to a shipment, I want the page to look and behave like the rest of the revamped app (sidebar, topbar, breadcrumbs, consistent cards and pills) so I do not lose the global nav and identity context every time I follow a shipment link.

As an SM/FM editing per-line weights, package counts, dimensions, and country of origin, I want a panel-based form with the same primitive vocabulary (`FormField` + `Input`, save bar, success pill via `StatusPill`) that I already use on `/products/[id]/edit` and `/po/[id]/edit`, so a single muscle memory covers every detail page.

As an SM viewing a finalized shipment (READY_TO_SHIP and beyond), I want read-only line item rows in the same table layout I'd see while editing, so I can confirm the values without a layout shift between edit and read modes.

## Tasks

1. **Move route under (nexus)**:
   - New file [frontend/src/routes/(nexus)/shipments/[id]/+page.svelte](frontend/src/routes/(nexus)/shipments/[id]/+page.svelte). Mounts under the existing `(nexus)/+layout.svelte` (AppShell + Sidebar + TopBar + ErrorBoundary).
   - Delete [frontend/src/routes/shipments/[id]/+page.svelte](frontend/src/routes/shipments/[id]/+page.svelte) (legacy tree).
   - Page-level scaffold matches `/products/[id]/edit` rhythm: `<svelte:head>`, `<AppShell>` with `userMenu` snippet, `PageHeader` replaced by the new `ShipmentDetailHeader`, `LoadingState` while loading, error fallback, panel column when loaded.
   - Permissions: any authenticated user reaches the page (the backend `get_shipment` already handles vendor scoping). `canEdit` is local-only — `is(role, 'SM', 'FREIGHT_MANAGER')` AND `status === 'DRAFT' || status === 'DOCUMENTS_PENDING'`. Backend remains the source of truth for transition rules; this gate is purely UI.

2. **`ShipmentDetailHeader` component** [frontend/src/lib/shipment/ShipmentDetailHeader.svelte](frontend/src/lib/shipment/ShipmentDetailHeader.svelte):
   - Wrap Phase 4.0 [`DetailHeader`](frontend/src/lib/ui/DetailHeader.svelte) with `backHref="/po"` (no shipments list yet) and `backLabel="Purchase Orders"` for now. Title = `shipment.shipment_number`. Subtitle = `${marketplace} · Created {formatDate(created_at)}`.
   - `statusPill` snippet renders [`StatusPill`](frontend/src/lib/ui/StatusPill.svelte) keyed on `STATUS_TONE` (Readonly<Record<ShipmentStatus, Tone>>): DRAFT→gray, DOCUMENTS_PENDING→orange, READY_TO_SHIP→blue, BOOKED→blue, SHIPPED→green.
   - `actionRail` snippet (mirrors [`InvoiceDetailHeader`](frontend/src/lib/invoice/InvoiceDetailHeader.svelte)) carrying two `<Button variant="secondary">` for the two PDF downloads. Disabled while downloading. testids: `shipment-download-packing-list`, `shipment-download-commercial-invoice`.
   - Inline at desktop ≥768px, sticky-bottom on `<768px` (mirror PoActionRail / InvoiceActionRail mobile pattern; verify against actual `InvoiceDetailHeader` CSS — that one only inlines, does not stick. If sticky is needed it lives in the page CSS, not the component).
   - testid root: `shipment-detail-header`. Status pill testid: `shipment-detail-status`.

3. **`ShipmentLineItemsPanel` component** [frontend/src/lib/shipment/ShipmentLineItemsPanel.svelte](frontend/src/lib/shipment/ShipmentLineItemsPanel.svelte):
   - `PanelCard` titled "Line items" with action snippet for the edit-mode Save button + transient saved-state pill.
   - Props: `lineItems: ShipmentLineItem[]`, `canEdit: boolean`, `saving: boolean`, `error: string`, `success: boolean`, `on_save: (drafts: ShipmentLineItemUpdate[]) => Promise<void>`.
   - Internal `drafts: Record<string, ShipmentLineItemUpdate>` `$state` indexed by `part_number`, re-initialized by `$effect` whenever the input `lineItems` array reference changes (parent reassigns after a successful save; `wasSaving` `$effect` pattern from iter 093).
   - Desktop ≥768px renders a `<table>` (reuse the iter 083 `PoInvoicesPanel` precedent — `DataTable` cannot host editable inputs; hand-rolled table with explicit columns is the established pattern). Columns: Part Number, Description, Qty, UoM, Net Weight, Gross Weight, Pkg Count, Dimensions, Country of Origin.
   - Mobile <768px renders cards stacked, one per line item, same fields — match the line items pattern from [`PoLineAcceptedTable`](frontend/src/lib/po/PoLineAcceptedTable.svelte).
   - When `canEdit && draft`: render Phase 4.0 [`Input`](frontend/src/lib/ui/Input.svelte) for net_weight (text), gross_weight (text), package_count (`type="number" min="0"`), dimensions (text), country_of_origin (text) bound to `drafts[part_number].<field>`. `ariaLabel` per input describing field + part_number for screen-reader disambiguation across many rows.
   - Read mode: plain `<span>` per cell, "—" fallback for nullish.
   - Save button: Phase 4.0 [`Button`](frontend/src/lib/ui/Button.svelte) `variant="primary"`, disabled when `saving`. Label flips "Save" / "Saving…".
   - Success state: a [`StatusPill`](frontend/src/lib/ui/StatusPill.svelte) `tone="green" label="Saved"` rendered in the panel action area for 3s after save (parent toggles `success`, the panel reacts by rendering the pill while `success === true`).
   - Error: inline `<p class="error">` below the action area, testid `shipment-line-items-error`.
   - Native client-side: trim string fields before submit, route empty strings to `null`, parse `package_count` to Number when present, leave `null` when blank. Mirror current [+page.svelte:62-69](frontend/src/routes/shipments/[id]/+page.svelte#L62-L69) exactly.
   - testids: `shipment-line-items-panel`, `shipment-line-items-save`, `shipment-line-items-saved-pill`, `shipment-line-items-error`, `shipment-line-item-row-{part_number}`, `shipment-line-item-net-weight-{part_number}`, `shipment-line-item-gross-weight-{part_number}`, `shipment-line-item-package-count-{part_number}`, `shipment-line-item-dimensions-{part_number}`, `shipment-line-item-country-{part_number}`.

4. **`ShipmentMetaPanel` component** [frontend/src/lib/shipment/ShipmentMetaPanel.svelte](frontend/src/lib/shipment/ShipmentMetaPanel.svelte):
   - Compact `PanelCard` rendering Marketplace / Created / Updated as a single [`AttributeList`](frontend/src/lib/ui/AttributeList.svelte) with three rows. Mirror [`PoMetadataPanels`](frontend/src/lib/po/PoMetadataPanels.svelte) conventions (date formatter via `toLocaleDateString` with `{year, month: 'short', day: 'numeric'}`).
   - Title "Shipment". Out-of-scope candidates for iter 098 (po_id link, status timeline) deliberately not included here.
   - testid root: `shipment-meta-panel`.

5. **Page wiring** [frontend/src/routes/(nexus)/shipments/[id]/+page.svelte](frontend/src/routes/(nexus)/shipments/[id]/+page.svelte):
   - State: `shipment: Shipment | null`, `loading`, `error`, `saving`, `saveError`, `saveSuccess`, `downloading`, `downloadingCi`.
   - `onMount` calls `getShipment(shipmentId)`. On failure surface via `LoadingState` swap (loading → error panel pattern from `/products/[id]/edit`).
   - `handleSave(drafts)`: calls `updateShipmentLineItems(shipment.id, {line_items: drafts})`, replaces `shipment` with response, sets `saveSuccess = true`, `setTimeout(..., 3000)` to unset (mirror current behavior).
   - `handleDownloadPacking()` / `handleDownloadCi()` matching current handlers.
   - Page layout: header → meta panel → line items panel. Vertical gap `var(--space-4)` matching products edit page.
   - Role label dictionary lifted from `/products/[id]/edit` (same `ROLE_LABEL` shape) — eligible for hoisting to `$lib` later, not in scope.

6. **No backend changes**. No domain changes. No DTO changes.

## Tests

### Existing test impact

- **Zero existing shipment specs** — no migration required.
- The `(nexus)` shell already runs through `nexus-shell.spec.ts`; that suite does not enumerate routes, so adding `/shipments/[id]` does not break it.
- No `(nexus)/+layout.ts` redirect changes — the bare authed-user policy already covers the new route.
- The legacy delete (Task 1) removes `frontend/src/routes/shipments/[id]/+page.svelte`. Confirm via `Grep` that no other code imports from that path. Today only the file itself uses its imports; the API client + types are imported from `$lib/api` and `$lib/types` and are unaffected.

### New permanent specs

7 specs in a new file `frontend/tests/shipment-detail.spec.ts`. Auth + base mocks via the same `beforeEach` shape as `product.spec.ts` — mock `/api/v1/me`, `/api/v1/shipments/{id}` GET; per-spec extras for PATCH and PDFs.

1. **Page mounts under (nexus) shell**: navigate to `/shipments/{id}`, assert `getByTestId('app-shell')` (or whatever the existing AppShell root testid is — confirm during implementation), `shipment-detail-header`, `shipment-meta-panel`, `shipment-line-items-panel` all visible. Asserts the new shell + panel set wired up.
2. **Status pill renders correct tone**: three rows, one per status (`DRAFT`/`READY_TO_SHIP`/`SHIPPED`), assert pill text + `data-tone` attribute (StatusPill exposes tone via class or attribute — verify in implementation; if not exposed, add).
3. **DRAFT shipment shows editable line item inputs**: assert `getByTestId('shipment-line-item-net-weight-{part}')` is an `<input>` for SM role on a DRAFT shipment.
4. **READY_TO_SHIP shipment shows read-only spans**: same row, no inputs, the cell renders the persisted value (or "—").
5. **Save round-trip**: edit two fields, click Save, assert PATCH body shape (`line_items` array with trimmed-or-null fields per the current contract), assert "Saved" pill renders briefly.
6. **Save error shows inline message**: PATCH 500, assert `shipment-line-items-error` text contains the server message.
7. **Download buttons trigger fetch** (lightweight): click `shipment-download-packing-list`, assert the test mock saw the GET to `/api/v1/shipments/{id}/packing-list`. Same for CI. Skip actual blob plumbing — it works in the legacy page and isn't being changed.

### Out of scope (call out, do not implement)

- iter 046 frontend (Documents panel, Add Requirement, Readiness panel, Mark Ready button) → follow-up iter (A2). Iter 098 number is taken by the parallel credential-reset / reissue-invite security iter, so A2 lands at iter 099 or later.
- iter 074 frontend (Booking card, Book button, Mark Shipped button, BOOKED/SHIPPED action rail entries) → follow-up iter after A2.
- `/shipments` list page, sidebar slot, deep links from PO detail.
- Activity panel for shipments (mirror of `PoActivityPanel`).
- `canViewShipments` / `canManageShipments` permission helpers — defer to iter 099 when role behavior diverges from "any authed user reaches detail."

## Notes

Shell port + line items panel landed in one Sonnet pass on the iter-093 / iter-094 panel rhythm: parent fetches, panels render with prop callbacks, save state owned by the page (3s pill timer), `wasSaving` `$effect` resets drafts inside the panel after the parent reassigns `lineItems`. `canEditShipment(role, status)` added to `permissions.ts` as a two-arg helper alongside `canViewPOAttachments` rather than inline — the `(role, status)` shape recurs and the helper compresses both gates into one call site. `package_count` rendered as a raw `<input type="number">` styled with `.ui-input` rather than the `Input` primitive: `Input` accepts `string` only and the legacy save contract treats `package_count` as `number | null`. Mobile cards expose mirrored testids with a `-mobile` suffix so a future iter that runs specs at mobile widths has handles without revisiting the panel. PDF download specs verified via a per-route hit counter polled with `expect.poll()` rather than blob inspection. `route.fallback()` (not `route.continue()`) was needed inside per-spec PATCH overrides so they chain to the GET handler set up by `setupShipmentDetail`. Backend untouched. With this iter the only remaining pre-revamp routes are `/login` / `/register` / `/setup` — the auth-page revamp couples with the iter 096 invite-token migration and is its own iter. Docs / readiness / mark-ready (A2) and booking / mark-shipped (iter 074 frontend) follow as separate iters; iter 098 is occupied by the parallel credential-reset security iter, so A2 lands at iter 099 or later.
