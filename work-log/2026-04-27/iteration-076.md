# Iteration 076 — `/po` list revamp (Phase 4.2 Tier 1)

## Context

Phase 4.2 Tier 1 of the mock-clarity inventory ([tools/phase-4-research/phase-4.2-mock-clarity-inventory.md](tools/phase-4-research/phase-4.2-mock-clarity-inventory.md), gaps G-01..G-06) has resolved decisions for the `/po` list surface. Reusable components landed in [frontend/src/lib/po/](frontend/src/lib/po/) ahead of this iter via the visual-mock work at [/ui-demo/po-list](frontend/src/routes/ui-demo/po-list/+page.svelte): `PoListFilters`, `PoListBulkBar`, `PoStatusPills`, `PoListTable`, `PoListPagination`. The current pre-revamp page lives at [frontend/src/routes/po/+page.svelte](frontend/src/routes/po/+page.svelte) and uses inline `<select>` / `<table>` / `<button class="btn">` markup; that file is the target of this iter.

Backend already accepts the `marketplace` query param ([backend/src/routers/purchase_order.py:224](backend/src/routers/purchase_order.py#L224)). No new endpoint shape is required.

## JTBD

When I open `/po` as SM/ADMIN, I want a responsive list (table at desktop, stacked cards at 390px) with marketplace filter, status pills that surface the Partial overlay on ACCEPTED POs, role-aware bulk actions, and the dashboard-grade empty/loading/error states, so I can find and act on POs without falling back to the pre-revamp layout. As VENDOR I want the vendor filter hidden (since Vendor-Scoped Access pins the result set). As PROCUREMENT_MANAGER or FREIGHT_MANAGER I want no selection column and no New PO button (read-only).

## Tasks

1. Frontend: replace the body of [/po/+page.svelte](frontend/src/routes/po/+page.svelte) with the Phase 4.2 components. Keep all existing data-fetching, debounce, URL-sync, and bulk-transition logic; swap only the markup + filter/bulk/table/pagination shells.
2. Frontend: add `marketplace` to the URL-sync state and pass it through `listPOs`. Marketplaces come from the four-enum constant in `PoListFilters` (no reference-data fetch yet).
3. Frontend: derive `canBulk` and `canCreatePO` from `role` to drive the selection column visibility and the `PageHeader` action slot. Re-use existing `canCreatePO` from [frontend/src/lib/permissions.ts](frontend/src/lib/permissions.ts); add `canBulkPO` if it does not already exist (covers ADMIN/SM/VENDOR true; PROCUREMENT_MANAGER + FREIGHT_MANAGER false).
4. Frontend: route the existing reject-comment modal through `PoListBulkBar`'s `onAction('reject')` callback. The modal stays in the page (do not push it into the bar).
5. Frontend: replace inline loading / empty markup with `LoadingState`, `EmptyState`, `ErrorState` primitives. On filter-refetch keep prior rows visible with a `LoadingState` overlay (per G-06 #3). Empty-after-filter shows no CTA; empty-because-none-exist shows the "New PO" CTA only when `canCreatePO`.
6. Frontend: route the existing cross-page "Select all 200 matching" link through `PoListBulkBar`'s `onPromoteCrossPage` callback.
7. Frontend: ensure the page renders inside the `(nexus)` shell. The current `/po` route lives outside `(nexus)`; move it under `frontend/src/routes/(nexus)/po/+page.svelte` so it inherits the AppShell + Sidebar + TopBar (matches the dashboard precedent set in iters 071-075). Remove the file at the old path.
8. Frontend: update [frontend/src/routes/+layout.svelte](frontend/src/routes/+layout.svelte) `isRevampRoute` derivation to include `/po` (and `/po/`), so the pre-revamp top nav hides on the new list.
9. Frontend: delete the old `StatusPill` import wrapper from [frontend/src/lib/components/StatusPill.svelte](frontend/src/lib/components/StatusPill.svelte) only if no other route still imports it; otherwise leave it for a later cleanup iter.
10. DDD vocab: assess whether "Marketplace" needs a fresh entry (likely already present); update [docs/ddd-vocab.md](docs/ddd-vocab.md) only if a new term emerged.

## Tests

### Existing test impact

- [frontend/tests/po-list.spec.ts](frontend/tests/po-list.spec.ts) (373 LOC) — many assertions target pre-revamp class names (`.btn`, `.btn-primary`, `.filter-bar`, `.bulk-toolbar`, `.selection-count`) and inline `<select>` test ids. Most will break after the markup swap. Expected impact: roughly 20-30 of the file's tests need fixture/selector updates. Re-target assertions to:
  - `data-testid="po-filter-status"` etc. on `PoListFilters` selects (component will expose stable test ids).
  - `data-testid="po-bulk-bar"` and per-action ids `data-testid="po-bulk-action-{action}"` on `PoListBulkBar`.
  - `data-testid="po-table"` and `data-testid="po-row-{id}"` on `PoListTable`.
  - `data-testid="po-pagination"` on `PoListPagination`.
- Mocks for `/api/v1/po` and `/api/v1/vendors` and `/api/v1/reference-data` stay valid; payload shape is unchanged.
- [frontend/tests/po-lifecycle.spec.ts](frontend/tests/po-lifecycle.spec.ts), [frontend/tests/po-negotiation.spec.ts](frontend/tests/po-negotiation.spec.ts), [frontend/tests/po-negotiation-events.spec.ts](frontend/tests/po-negotiation-events.spec.ts) — these primarily exercise detail and edit pages. They navigate from `/po` once at the top; the row click selector may need an update from `tr` to `[data-testid^="po-row-"]`. Otherwise unchanged.
- Backend pytest suite — no changes (marketplace param already supported).

### Permanent — frontend

1. `po-list.spec.ts::filter bar exposes marketplace filter` — assert the `data-testid="po-filter-marketplace"` select renders all four enum values (AMAZON_US, AMAZON_EU, WALMART_US, EBAY_US) plus "All", and that selecting one round-trips through the URL `?marketplace=AMAZON_US`.
2. `po-list.spec.ts::vendor filter hidden for VENDOR role` — mock `/auth/me` with a VENDOR user, assert `data-testid="po-filter-vendor"` is absent and the other four filters render.
3. `po-list.spec.ts::PROCUREMENT_MANAGER sees no selection column and no New PO button` — mock `/auth/me` with PM role; assert no checkbox column on `PoListTable` and no `data-testid="po-page-header-action"` button.
4. `po-list.spec.ts::FREIGHT_MANAGER sees no selection column` — same as #3 but for FM.
5. `po-list.spec.ts::Partial pill renders for ACCEPTED with has_removed_line` — seed the mock with a PO whose `status='ACCEPTED'` and `has_removed_line=true`; assert the row contains both the green "Accepted" pill and a secondary "Partial" pill (`data-testid="po-status-partial"`).
6. `po-list.spec.ts::mobile reflow at 390px stacks rows as cards` — set viewport to 390x844 before navigation; assert `data-testid="po-row-{id}"` has class `po-row-card` and that the milestone column / row content reflows.
7. `po-list.spec.ts::empty-after-filter does not show New PO CTA` — apply a filter that returns zero rows; assert the empty-state primitive renders without a CTA button. Then clear filters with the table empty-because-none-exist mock and assert the CTA is present (only when role can create).
8. `po-list.spec.ts::filter-refetch keeps prior rows visible with loading overlay` — intercept the second `/api/v1/po` call to delay; during the wait assert prior `tr` rows are still in the DOM and a `data-testid="po-list-loading"` overlay is visible.

### Scratch

None. The eight permanent tests cover decision verification end-to-end.

## Notes

(populated at close)
