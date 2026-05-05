# Iteration 086 — Phase 4.3 Tier 1: `/invoices` list revamp

## Context

Phase 4.2 PO surface (list + detail + create + edit) closed at iter 085. Phase 4.3 close-out items G-28 (role-coverage matrix audit) and G-29 (99-spec Playwright migration plan) are deferred to backlog. This iter opens Phase 4.3 with the `/invoices` list page.

Phase 4.3 replaces `/invoices` (list) and `/invoice/:id` (detail). The detail page carries mock-clarity gaps (OPEX vs PROCUREMENT branching on create, dispute reason flow, remaining-quantity guard UI, action rail per status); the list does not. This iter ports the list page only, mirroring iter 076 for `/po`.

Pre-revamp state ([frontend/src/routes/invoices/+page.svelte](frontend/src/routes/invoices/+page.svelte), 359 lines): inline `<select class="select filter-select">` × 4 + `<input type="date">` × 2 + `<table class="table">` + inline `.bulk-toolbar` + inline pagination + checkbox rows + Download PDFs button. `StatusPill` from `frontend/src/lib/components/StatusPill.svelte` (last consumer here + `/invoice/:id`). API: `listAllInvoices(params)` returns `PaginatedInvoiceList` of `InvoiceListItemWithContext`. Role guard: `+page.ts` redirects to `/dashboard` for non-`canViewInvoices` roles.

Target state: `(nexus)/invoices/+page.svelte` mounts AppShell + UserMenu + PageHeader, drives new components in `frontend/src/lib/invoice/`: `InvoiceListFilters`, `InvoiceListBulkBar`, `InvoiceListTable`, `InvoiceListPagination`. Vendor filter hidden for VENDOR users. No header CTA — invoices are created from PO detail. `isRevampRoute` extended with `/invoices` exact match; `/invoice/:id` stays pre-revamp until Tier 2.

Out of scope: invoice detail, invoice create form, dispute reason flow, action rails per status. Legacy `StatusPill` and `ActivityTimeline` remain as last-consumers on `/invoice/:id`.

Test state at iter 085 close: 696 backend + 275 Playwright green. svelte-check carries 29 latent type errors deferred to backlog.

## JTBD

For each persona arriving at `/invoices`:

- **Procurement Manager (read-only) / Supply Manager / ADMIN**: I want to scan invoices across vendors filtered by status / PO / vendor / date range, see payment exposure (count + subtotal), and bulk-download PDFs for archival. I click an invoice number to drill into detail or a PO number to drill into the source PO.
- **Vendor**: I want to see only my own invoices (vendor scope already enforced server-side), filter by status / invoice# / PO# / date, and click into detail to act on next steps. The vendor filter is hidden because it's redundant for me.
- **Freight Manager**: I want to see invoices I'm responsible for (OPEX-side workflow per Phase 4.1 dashboard precedent) and bulk-download PDFs for shipment paperwork. Same surface as SM.
- **Quality Lab**: I am redirected by the existing `+page.ts` guard. My role is excluded from `canViewInvoices`. No surface change needed.

The page is a side-by-side replacement of the pre-revamp surface with Phase 4.0 primitives — same data, same actions, AppShell + Sidebar + TopBar inheritance, responsive layout, dashboard-grade loading / empty / error states, testid-driven Playwright contract.

## Tasks

1. **Components** under `frontend/src/lib/invoice/`:
   1. `InvoiceListFilters.svelte` — props: `bind:status`, `bind:invoiceNumber`, `bind:poNumber`, `bind:vendor`, `bind:dateFrom`, `bind:dateTo`, plus `vendors: VendorListItem[]`, `invoiceOptions: string[]`, `poOptions: string[]`, `showVendorFilter: boolean`. Uses `Select` + `DateInput` + `FormField` primitives. testids: `invoice-filter-status`, `invoice-filter-invoice-number`, `invoice-filter-po-number`, `invoice-filter-vendor`, `invoice-filter-date-from`, `invoice-filter-date-to`, `invoice-filter-clear` (visible when any filter active).
   2. `InvoiceListBulkBar.svelte` — props: `selectedCount: number`, `onDownload: () => void`, `onClear: () => void`, `loading: boolean`. testids: `invoice-bulk-bar`, `invoice-bulk-action-download`, `invoice-bulk-clear`. Hidden when `selectedCount === 0`.
   3. `InvoiceListTable.svelte` — props: `rows: InvoiceListItemWithContext[]`, `bind:selectedIds: Set<string>`, `onRowClick: (id: string) => void`. Renders `<table>` (no class — collision with pre-revamp `.table` rule per CLAUDE.md selector policy) at desktop and stacked cards at 390px (mirror PoListTable). Status renders via Phase 4.0 `StatusPill` primitive (not legacy `frontend/src/lib/components/StatusPill.svelte`). testids: `invoice-table`, `invoice-row-{id}`, `invoice-row-checkbox-{id}`, `invoice-table-checkbox-all`.
   4. `InvoiceListPagination.svelte` — clone of `PoListPagination` shape (page-size Select [10/20/50/100/200] + Prev/Next Buttons + `Showing X-Y of N`). testid: `invoice-pagination`, `invoice-pagination-prev`, `invoice-pagination-next`, `invoice-pagination-size`.
2. **Route move:**
   1. Create `frontend/src/routes/(nexus)/invoices/+page.svelte` mounting AppShell + UserMenu + PageHeader (title "Invoices", no action snippet) + the four new components.
   2. Move `frontend/src/routes/invoices/+page.ts` to `frontend/src/routes/(nexus)/invoices/+page.ts` unchanged.
   3. Delete `frontend/src/routes/invoices/+page.svelte` and the now-empty source `+page.ts`.
3. **Layout:** extend `isRevampRoute` in `frontend/src/routes/+layout.svelte` with an exact `/invoices` match (the slash-less detail route `/invoice/:id` stays pre-revamp).
4. **Behavior parity:**
   1. `onMount` fetches vendor list + a wide invoice list (page_size 9999) for `poOptions` / `invoiceOptions` derivation, then triggers `fetchInvoices()` with current filters (mirror current behavior).
   2. Filter changes reset `page = 1` and clear `selectedIds`. Pagination via `bind:page`/`bind:pageSize` triggers refetch.
   3. `LoadingState` overlay preserves prior rows on filter-refetch (per iter 076's G-06 #3 precedent).
   4. Empty-after-filter: `EmptyState` "No matching invoices" / "Try adjusting filters." (no CTA).
   5. Empty-no-filter: `EmptyState` "No invoices yet" / "Invoices appear here once a vendor creates them from a PO." (no CTA — invoices created from PO detail, not list).
   6. Error: `ErrorState` "Failed to load invoices" + Retry calls `fetchInvoices()`.

## Tests

### Existing test impact

- **`frontend/tests/invoice-list.spec.ts`** — 5 list tests selectors-migrated to new testid contract (`tbody tr` → `getByTestId('invoice-row-*')`, `.bulk-toolbar` → `getByTestId('invoice-bulk-bar')`, `tbody input[type="checkbox"]` → `getByTestId('invoice-row-checkbox-*')`, `.filter-bar select` → `getByTestId('invoice-filter-status')`, `tbody a[href=...]` → `getByTestId('invoice-row-{id}')` with `getByRole('link')` inside row, `getByRole('button', { name: 'Download PDFs' })` → `getByTestId('invoice-bulk-action-download')`). The 1 detail-page test (`Download PDF on /invoice/inv-1`) is left untouched — `/invoice/:id` stays pre-revamp this iter.
- **`frontend/tests/dev-login.spec.ts`** — uses `/invoices` for the redirect-after-login flow. Verify still works after move (the URL is unchanged from the user's perspective; `(nexus)` is a layout group, not a URL segment).
- **`frontend/tests/role-rendering.spec.ts`** — has invoice-related role assertions. Verify pass after the route is at `(nexus)/invoices`.
- **`frontend/tests/auth-flow.spec.ts`** — has `/invoices` redirect coverage. Verify pass.
- **`frontend/tests/notification-bell.spec.ts`** — has `/invoices` page-load coverage. Verify pass.
- No backend test impact.

### New tests (`frontend/tests/invoice-list.spec.ts`)

Mounted under the existing file with the new testid contract:

1. **AppShell mounts** — `getByTestId('ui-appshell-sidebar')` visible at `/invoices`.
2. **Loading state initial** — `getByTestId('invoice-list-loading')` visible while first fetch resolves.
3. **Empty no-filter** — `EmptyState` "No invoices yet" copy when API returns 0 items and no filter.
4. **Empty with filter** — `EmptyState` "No matching invoices" copy when status filter applied + 0 items.
5. **Error + retry** — API returns 500; `ErrorState` visible; clicking Retry triggers a second fetch.
6. **Bulk bar appears on selection** — toggle one row checkbox, `invoice-bulk-bar` becomes visible with count "1 selected".
7. **Bulk download triggers POST** — bulk PDF endpoint receives the selected IDs.
8. **Bulk clear** — clicking `invoice-bulk-clear` empties the selection and hides the bar.
9. **Vendor filter hidden for VENDOR** — auth me returns role VENDOR, `invoice-filter-vendor` is not in the DOM.
10. **Pagination disable states** — Prev disabled when `page === 1`, Next disabled when `page === totalPages`.

## Notes

Phase 4.3 Tier 1 lands the first Phase 4.3 surface mirroring iter 076's `/po` list precedent: route move under `(nexus)/invoices/`, four new components in `frontend/src/lib/invoice/` (`InvoiceListFilters` / `InvoiceListBulkBar` / `InvoiceListTable` / `InvoiceListPagination`), Phase 4.0 primitive consumption end-to-end (`AppShell` + `UserMenu` + `PageHeader` + `Select` + `DateInput` + `Button` + `StatusPill` + `LoadingState` + `EmptyState` + `ErrorState`). The legacy `frontend/src/lib/components/StatusPill.svelte` stays untouched — last-consumer is `/invoice/:id` until Phase 4.3 Tier 2 ports the detail page.

Two divergences from iter 076's precedent worth flagging. First, no header CTA: invoices are created from PO detail (the existing flow), not from the list, so `PageHeader` has no `action` snippet (vs `/po` which renders New PO when `canCreatePO`). Second, the bulk bar's only action is Download PDFs — no per-status branching like the PO list's submit/accept/reject/resubmit Valid Actions matrix — so `InvoiceListBulkBar` is much simpler (3 props vs 9 on `PoListBulkBar`) and renders without any Valid Actions intersection logic. Both are inherent to the invoice list's narrower mutation surface, not omissions.

Test surface: 13 specs in `invoice-list.spec.ts` (5 migrated from pre-revamp + 7 new + 1 unchanged detail-page test that verifies Download PDF is still on `/invoice/:id`). Strict-mode collision between desktop `<tr>` and mobile `<div>` rows (both carry the same `invoice-row-{id}` testid for the responsive layout pattern from `PoListTable`) was resolved by adding `data-testid="invoice-table-desktop"` to the `<table>` and `data-testid="invoice-table-mobile"` to the mobile region; specs scope row queries through the parent testid (`page.getByTestId('invoice-table-desktop').getByTestId('invoice-row-...')`). This is a cleaner pattern than `PoListTable`'s precedent (which forces consumer specs to use `tbody tr[data-testid=...]` tag-prefixed selectors that violate the new selector policy from CLAUDE.md). The error-state test had an initial false-pass because `onMount`'s page-size-9999 prefill call swallowed the first 500 — fixed by failing call #2 (the real fetch) instead of call #1 (the prefill).

Vendor filter visibility: `showVendorFilter = role !== 'VENDOR'` mirrors the `/po` list pattern — VENDOR users see only their own invoices via server-side scoping (iter 032), so a vendor dropdown is redundant. Other roles see the full vendor list. The role-conditional surface is a single inline check at the page level rather than a declarative matrix; G-28 deferred per backlog.

Pre-iter audit verified the 29 carried svelte-check errors (test fixture `vendor_id: null` literal narrowings + `(nexus)/po/[id]/+page.svelte:330,432` `$state(null)` narrowings + dashboard / shipments / products page narrowings + 4 `Buffer` not-found errors in `po-documents.spec.ts`) are unchanged after this iter — none new, all routed to the type-hardening backlog item. The new invoice-list.spec.ts uses an explicit `User` import from `$lib/types` and parameter-types `mockUser(page: Page, user: User)` so it does NOT inherit the `typeof SM_USER` literal-narrowing pattern that bites the PO test suite; this is intentional and the pattern G-29's `buildPOFixture` will adopt.

`isRevampRoute` extended with `page.url.pathname === '/invoices'` exact match in [frontend/src/routes/+layout.svelte](frontend/src/routes/+layout.svelte). The detail route `/invoice/:id` (no trailing s) intentionally stays pre-revamp — Phase 4.3 Tier 2 picks it up.

No new domain terms emerged — Invoice / InvoiceStatus / OPEXInvoice / OverInvoicingGuard are pre-existing vocabulary. Structural retrofit only.
