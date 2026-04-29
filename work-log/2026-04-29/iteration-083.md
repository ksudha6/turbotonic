# Iteration 083 — `/po/[id]` finishing pass: metadata grid + invoices + rejection + activity (Phase 4.2 Tier 5)

## Context

Phase 4.2 PO detail rollout has shipped Tier 2 (header + action rail + advance panel + cert banner — iter 077), Tier 3 (line negotiation cards + sticky submit-response bar — iter 081), and Tier 4 (post-acceptance line dialogs + production status timeline — iter 082). Iter 082's close named the only remaining pre-revamp sections on [(nexus)/po/[id]/+page.svelte](frontend/src/routes/(nexus)/po/[id]/+page.svelte) as the invoice table, rejection history, activity timeline, and the metadata grid (Currency / Issued Date / Delivery Date / Total Value / Payment Terms / Marketplace + Buyer + Vendor + Trade Details + Terms & Conditions).

Concrete pre-revamp blocks today:

- Metadata grid at [`+page.svelte:463-551`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L463) — five `<div class="section card">` blocks each owning a hand-rolled `<div class="info-grid">` of `field-label` + `value` spans. Currency / Issued / Delivery / Total / Payment Terms / Marketplace; Buyer; Vendor; Trade Details; Terms & Conditions.
- Rejection History at [`+page.svelte:634-644`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L634) — `<div class="section card">` with hand-rolled `.rejection-record` rows (G-25).
- Invoices sub-list at [`+page.svelte:646-670`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L646) — legacy `<table class="table">` (G-24).
- Activity at [`+page.svelte:672-675`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L672) — legacy [ActivityTimeline](frontend/src/lib/components/ActivityTimeline.svelte) component (G-21).

`ActivityTimeline` is also referenced by [invoice/[id]/+page.svelte:7](frontend/src/routes/invoice/[id]/+page.svelte#L7), so the file is not deleted in this iter; only its PO consumer migrates.

G-22 (PO document attachment) is greenfield (no existing surface; needs a new `canManagePOAttachments` helper, file-picker affordance, and `entity_type='PO'` wiring) and is descoped to its own iter so this Tier 5 stays a finishing pass over surfaces that already render content.

After this iter the entire `(nexus)/po/[id]` page consumes Phase 4.0 primitives end-to-end and Phase 4.2 PO surfaces (list + detail) reach feature parity with the legacy shape.

## JTBD

When I am viewing a PO at any status, I want the trade metadata (currency, terms, ports, countries, vendor, buyer) rendered in the same `PanelCard` + `AttributeList` rhythm used elsewhere in the revamp so my eye does not retrain on a hand-rolled grid for one section.

When I am viewing a PO with prior invoices, I want the invoice sub-list to use the same `DataTable` primitive as the `/invoices` list so click-through, status pills, and column alignment match my expectations from the rest of the app — and I want to see the remaining-quantity total as a section subtitle so I know the cap before I open the create-invoice dialog.

When I am viewing a Rejected or Revised PO, I want past rejection comments rendered inside a `PanelCard` panel (not a hand-rolled card-in-card with bespoke spacing) so the visual weight matches the iter 077 cert-warnings banner and other advisory panels.

When I am viewing the activity feed for a PO, I want it to use the same `ActivityFeed` primitive as the dashboard's recent-activity panel with category-driven dots (LIVE/ACTION_REQUIRED/DELAYED) and a "Show more" affordance so two activity-feed patterns no longer coexist in the app.

## Tasks

1. Frontend: new `frontend/src/lib/po/PoMetadataPanels.svelte` rendering the four metadata `PanelCard`s currently inlined at [`+page.svelte:463-551`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L463).
   - Trade Summary panel: rows for Currency, Issued Date, Delivery Date, Total Value, Payment Terms, Marketplace (Marketplace row only when `po.marketplace` is set).
   - Buyer panel: Name, Country.
   - Vendor panel: Name, Country.
   - Trade Details panel: Incoterm, Port of Loading, Port of Discharge, Country of Origin, Country of Destination.
   - Terms & Conditions panel: a single body paragraph (not an AttributeList — it's free text).
   - Each panel uses the [PanelCard](frontend/src/lib/ui/PanelCard.svelte) + [AttributeList](frontend/src/lib/ui/AttributeList.svelte) primitives. AttributeList rows are `{ label, value }` pairs; the date and currency formatting helpers already live in the page (`formatDate`, `formatValue`) — pass them in as a `format` prop or pre-format strings before constructing the rows array.
   - Props: `po: PurchaseOrder`, `resolve: (kind, code) => string`, `formatDate: (s) => string`, `formatValue: (n, code) => string`. The component imports nothing role-aware; visibility is the same for every viewer.
   - testid: `po-metadata-trade-summary`, `po-metadata-buyer`, `po-metadata-vendor`, `po-metadata-trade-details`, `po-metadata-terms`.
2. Frontend: new `frontend/src/lib/po/PoRejectionHistoryPanel.svelte` replacing the rejection-history block at [`+page.svelte:634-644`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L634).
   - Wraps a `PanelCard` titled "Rejection History".
   - Renders each record as a styled `<article>` (latest-first, matches current order) with `record.comment` and `formatDate(record.rejected_at)`. No new primitive — the records are simple value objects, not Activity Log Entries, and folding them into ActivityFeed would mix Rejection Record value-object data with event-stream entries (G-25 decision).
   - Component receives `records: { comment: string; rejected_at: string }[]` + `formatDate` helper. Caller-side hides the panel entirely when `records.length === 0` (no internal empty state — matches existing behavior).
   - testid: `po-rejection-history-panel`, `po-rejection-record-{index}` per row.
3. Frontend: new `frontend/src/lib/po/PoInvoicesPanel.svelte` replacing the invoices block at [`+page.svelte:646-670`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L646).
   - Wraps a [PanelCard](frontend/src/lib/ui/PanelCard.svelte) titled "Invoices" with a subtitle showing the remaining-quantity total: `"{remainingTotal} unit{s} remaining to invoice"` for PROCUREMENT POs that still have remaining quantity; OPEX POs get a different subtitle (`"OPEX — single invoice"` when `invoices.length === 0`, no subtitle when an invoice exists). The remaining total is derived from `remainingMap` already on the page — sum of `remaining` across rows for PROCUREMENT.
   - Body hand-rolls a `<table>` matching the DataTable CSS rhythm (gray-50 thead, gray-100 row borders) because DataTable's cell `render` is `string | number` and the Status column needs to render the [StatusPill](frontend/src/lib/components/StatusPill.svelte) component. Same precedent as `PoListTable` from iter 076. Columns: Invoice # (link to `/invoice/{id}`), Status (StatusPill component), Subtotal (formatValue), Created (formatDate). Pagination omitted; the sub-list is small.
   - Caller-side hides the panel when `invoices.length === 0` AND there is nothing to invoice (matches current pre-revamp behavior of hiding the section when no invoices exist). For OPEX with `remaining_total > 0`, the Invoices panel is hidden entirely; the Create Invoice CTA stays in `PoActionRail` (G-24 decision: no duplicate CTA in sub-list).
   - Props: `invoices: InvoiceListItem[]`, `po: PurchaseOrder`, `remainingMap: Map<string, RemainingLine>`, `formatDate`, `formatValue`.
   - testid: `po-invoices-panel`, `po-invoices-row-{invoice_id}`.
4. Frontend: new `frontend/src/lib/po/PoActivityPanel.svelte` replacing the legacy `<ActivityTimeline />` usage at [`+page.svelte:673-675`](frontend/src/routes/(nexus)/po/[id]/+page.svelte#L673).
   - Wraps a [PanelCard](frontend/src/lib/ui/PanelCard.svelte) titled "Activity" containing the [ActivityFeed](frontend/src/lib/ui/ActivityFeed.svelte) primitive.
   - Maps `ActivityLogEntry[]` to `ActivityFeed` `{ id, primary, secondary, tone }` entries:
     - `primary`: `EVENT_LABELS[entry.event] ?? entry.event` (label dictionary moves into a new shared `frontend/src/lib/po/event-labels.ts` so future panels reuse it).
     - `secondary`: `entry.detail ? \`${formatTimestamp(entry.created_at)} · ${entry.detail}\` : formatTimestamp(entry.created_at)`.
     - `tone`: `LIVE → 'blue'`, `ACTION_REQUIRED → 'orange'`, `DELAYED → 'red'`, default `'gray'`. Mapping lives next to the panel — same shape as dashboard's category-to-tone helper.
   - "Show more" affordance: client-side pagination over a single fetch. Initial render shows 10 rows; clicking the [Button](frontend/src/lib/ui/Button.svelte) (variant ghost) labelled "Show more" reveals the next 10. Hide button when all rows visible. No backend changes — `fetchActivityForEntity` already returns the full list.
   - Empty state: when entries.length === 0, render an [EmptyState](frontend/src/lib/ui/EmptyState.svelte) with title "No activity yet."
   - testid: `po-activity-panel`, `po-activity-show-more-btn`.
   - Component does its own `onMount` fetch via `fetchActivityForEntity('PO', po.id)` so the page does not have to thread activity state. Loading state: render [LoadingState](frontend/src/lib/ui/LoadingState.svelte) inside the panel until first response.
5. Frontend: new `frontend/src/lib/po/event-labels.ts` exporting `EVENT_LABELS: Record<string, string>` and `categoryToTone(category: string): 'green' | 'blue' | 'orange' | 'red' | 'gray'`. Source of truth for both the new `PoActivityPanel` and any future PO event surface (e.g. notification routing). Copy the existing dictionary out of [ActivityTimeline.svelte](frontend/src/lib/components/ActivityTimeline.svelte) verbatim — same 18 events. Legacy `ActivityTimeline.svelte` keeps its inline copy until invoice detail revamps and retires the component.
6. Frontend: integrate the four new panels at [(nexus)/po/[id]/+page.svelte](frontend/src/routes/(nexus)/po/[id]/+page.svelte):
   - Replace lines 463-551 (five `<div class="section card">` metadata blocks) with `<PoMetadataPanels {po} {resolve} {formatDate} {formatValue} />`.
   - Replace lines 634-644 (rejection history block) with `{#if po.rejection_history.length > 0}<PoRejectionHistoryPanel records={po.rejection_history} {formatDate} />{/if}`.
   - Replace lines 646-670 (invoices block) with the existing show-condition expanded to also gate OPEX (single panel call). Pass `invoices`, `po`, `remainingMap`, `formatDate`, `formatValue`.
   - Replace lines 672-675 (activity section) with `<PoActivityPanel poId={po.id} />`.
   - Remove the now-unused `<style>` rules: `.section.card`, `.info-grid`, `.info-item`, `.field-label`, `.value`, `.rejection-record`, `.rejection-comment`, `.rejection-date`, `.terms-text`. The page CSS shrinks by ~80 lines.
   - Drop the `import StatusPill from '$lib/components/StatusPill.svelte'` line if no other consumer remains on the page (the new `PoInvoicesPanel` imports it directly).
   - Drop the `import ActivityTimeline from '$lib/components/ActivityTimeline.svelte'` line.
7. Frontend: new `/ui-demo/po-finishing` mock route hosting toggleable matrix:
   - PO status toggle: PENDING / ACCEPTED / REJECTED / REVISED.
   - Rejection-history toggle: 0 records / 1 record / 3 records.
   - Invoices toggle: 0 invoices / 1 invoice / 3 invoices (PROCUREMENT) / OPEX-with-1-invoice.
   - Activity toggle: empty / 5 entries / 25 entries (verify Show more reveals).
   - Auth-free, pure visual. Pattern matches `/ui-demo/po-accepted` from iter 082.
   - Mock data lives in the route file; no shared fixtures.
8. Scope-fence: this iter does NOT add G-22 (PO document attachment) — that ships as iter 084 with its own brainstorm of permission/upload UX and the new `canManagePOAttachments` helper. This iter does NOT touch the legacy [ActivityTimeline.svelte](frontend/src/lib/components/ActivityTimeline.svelte) — the invoice detail page still consumes it; the file retires when invoice detail revamps. This iter does NOT replace the legacy `StatusPill` from [frontend/src/lib/components/StatusPill.svelte](frontend/src/lib/components/StatusPill.svelte) with the Phase 4.0 [StatusPill](frontend/src/lib/ui/StatusPill.svelte) primitive — invoice rows still consume the legacy file's status-to-class mapping; that swap is its own cleanup pass. This iter does NOT extend ActivityFeed to support per-row icons or the iter-058 event-icon glyphs — those are advisory and the dashboard does without them.
9. Scope-fence: backend untouched. No new endpoints; no schema changes. The existing `/api/v1/activity/?entity_type=PO&entity_id={id}` already returns the full per-entity event list (no limit), which is fine for client-side "Show more". If a PO accumulates >100 events in production we revisit with backend pagination.

## Tests

### Existing test impact

- Frontend: 7 specs in [po-detail.spec.ts](frontend/tests/po-detail.spec.ts) (iters 077, 082) target metadata cells via testids on action-rail, advance-panel, cert-banner, line tables, milestone timeline, and add-line dialog — none of those surfaces change here. Expected impact: 0 specs.
- Frontend: any pre-revamp specs that asserted `.rejection-record`, `.info-grid`, `.section.card h2` (class/tag selectors) on the PO detail page break. Audit `po-lifecycle.spec.ts` and `po-rejection.spec.ts` (if it exists) for those queries. Expected impact: 0-3 specs migrated to testid (`po-rejection-history-panel`, `po-metadata-*`).
- Frontend: 1 spec in `notification-bell.spec.ts` may touch the PO detail activity timeline via class selectors — confirm by grepping for `entry-label` / `timeline-entry` against the file. If found, migrate to `po-activity-panel` + `ui-feed` role queries. Expected impact: 0-1 specs.
- Backend: zero. No backend changes.

### Permanent — backend

None. This iter is frontend-only.

### Permanent — frontend

1. `primitives.spec.ts::AttributeList renders label-value rows in source order` — already covered by iter 080 if present; if not, add a 2-row render assertion against `data-testid="po-metadata-trade-summary"` (skip if iter 080 covers it).
2. `po-detail.spec.ts::metadata trade summary panel renders six rows when marketplace set` — mock PO with marketplace=AMZ, assert `getByTestId('po-metadata-trade-summary')` shows Currency, Issued Date, Delivery Date, Total Value, Payment Terms, Marketplace labels via role/label queries on the AttributeList.
3. `po-detail.spec.ts::metadata trade summary hides marketplace row when null` — mock PO with marketplace=null, assert Marketplace label is not present inside the panel.
4. `po-detail.spec.ts::buyer panel renders name and country with resolved label` — mock PO with buyer_country='US', assert "United States" appears inside `po-metadata-buyer`.
5. `po-detail.spec.ts::trade details panel renders five rows` — assert all five labels present.
6. `po-detail.spec.ts::terms panel renders free-text body` — mock PO with `terms_and_conditions="Net 30 from invoice"`, assert text appears inside `po-metadata-terms`.
7. `po-detail.spec.ts::rejection history panel hides when no records` — mock PO with empty `rejection_history`, assert `po-rejection-history-panel` is not visible.
8. `po-detail.spec.ts::rejection history panel renders records latest-first` — mock PO with two records (older + newer), assert `po-rejection-record-0` contains the newer comment.
9. `po-detail.spec.ts::invoices panel hides when no invoices and not OPEX` — mock PROCUREMENT PO with zero invoices, assert `po-invoices-panel` not visible.
10. `po-detail.spec.ts::invoices panel shows remaining subtitle for procurement` — mock PROCUREMENT PO with 1 invoice + remainingMap totalling 50 units, assert subtitle text "50 units remaining to invoice" inside the panel header.
11. `po-detail.spec.ts::invoices panel renders datatable rows` — mock 2 invoices, assert two `po-invoices-row-{id}` rows rendered with correct invoice numbers and statuses.
12. `po-detail.spec.ts::activity panel shows loading state then entries` — mock `/api/v1/activity/?entity_type=PO&entity_id=...` to return 3 entries, assert LoadingState role=status replaced by feed with 3 rows.
13. `po-detail.spec.ts::activity panel renders empty state when no entries` — mock empty array, assert EmptyState title "No activity yet." renders.
14. `po-detail.spec.ts::activity show-more reveals next batch` — mock 25 entries, assert initial 10 rows visible + Show more button present, click button, assert 20 rows visible.
15. `po-detail.spec.ts::activity show-more hides when all rows visible` — mock 8 entries (less than initial 10), assert Show more button is not visible.
16. `po-detail.spec.ts::activity row primary uses event label dictionary` — mock entry with event='PO_LINE_MODIFIED', assert primary text reads "Line modified".
17. `po-detail.spec.ts::activity row tone reflects category` — mock entries with categories LIVE / ACTION_REQUIRED / DELAYED, assert dot classes include `blue`, `orange`, `red` respectively (queried via the `ui-feed` `<span class="dot ...">` markup, scoped inside `po-activity-panel`).

Total new Playwright specs: 16 (15 po-detail + 1 conditional primitives if not already covered). Running total: 223 (iter 082) + 16 = 239.

### Scratch — frontend

None. The mock route at `/ui-demo/po-finishing` is the visual verification surface (manual screenshot pass at desktop 1440 + mobile 390 before the iter closes).

## Backlog opened

- **G-22 PO document attachment (iter 084)** — `canManagePOAttachments` helper, `entity_type='PO'` upload wiring, Documents `PanelCard` between Activity and Rejection History, file picker Button + DataTable of files. Scope decisions deferred to its own brainstorm.
- **Legacy ActivityTimeline retirement** — pending invoice detail revamp. Until then [frontend/src/lib/components/ActivityTimeline.svelte](frontend/src/lib/components/ActivityTimeline.svelte) and [frontend/src/lib/components/StatusPill.svelte](frontend/src/lib/components/StatusPill.svelte) retain one consumer each.
- **Backend per-entity activity pagination** — current `/api/v1/activity/?entity_type=PO&entity_id={id}` returns the full list. Client-side "Show more" is fine until a single PO accumulates >100 events; revisit then.

## Notes

DataTable does not support snippet cells (its `render` returns `string | number`), so `PoInvoicesPanel` hand-rolls a `<table>` matching DataTable's CSS rhythm rather than extending the primitive. Same precedent as `PoListTable` from iter 076. Promoting snippet support out of the two consumers into the shared primitive stays on the backlog.

`event-labels.ts` is a fresh module rather than a refactor of the dictionary buried inside `ActivityTimeline.svelte`. The legacy file keeps its own copy until invoice detail revamps and retires the component. Two copies for one iter is preferable to a partial refactor that leaves the legacy timeline reaching across module boundaries.

`PoActivityPanel` accepts an optional `mockEntries` prop that bypasses `onMount` fetch. The prod page never sets it; the `/ui-demo/po-finishing` mock route uses it to demo the panel offline without `window.fetch` interception. This is the cleanest way to keep the component self-fetching in production while still mockable in the demo gallery.

Tone mapping `LIVE → blue, ACTION_REQUIRED → orange, DELAYED → red` lives in `categoryToTone` next to `EVENT_LABELS` rather than inside `PoActivityPanel`. Future PO event surfaces (notification routing, dashboard category filters) can import the same helper.

Rejection History stays a hand-rolled `<article>` list inside `PanelCard` rather than reusing `ActivityFeed`. Folding it would mix Rejection Record value objects with Activity Log Entry events — the inventory's G-25 decision called this out and the implementation honors it.

Per-row icon glyphs from the legacy `ActivityTimeline` (pencil/check/x/shield-check etc.) did not carry over. `ActivityFeed` is dot+text only by design; the icons were advisory and the dashboard ships without them. The migrated negotiation-events spec was rewritten to assert via `EVENT_LABELS` text, which is the contract that actually matters.

The four pre-revamp specs that targeted `.timeline-entry` / `.entry-label` / `.timeline-dot` class selectors migrated as scope expansion (per CLAUDE.md selector policy: when a new component lands, the consumer's specs migrate with it). `activity-timeline.spec.ts` and `po-negotiation-events.spec.ts` now query through `po-activity-feed` testid + ActivityFeed role/class structure.
