# Iteration 066 -- DataTable + PageHeader + DetailHeader

## Context

Sixth iteration of Phase 4.0. Iter 065 closed with 18 primitives live (7 leaves + 5 composites + 6 display/state). This iteration ships three more (Plan Tasks 14-15):

- **Task 14** -- `DataTable` with server-driven pagination contract. Generic over `T extends { id: string }`, takes `columns: Column<T>[]`, `rows: T[]`, optional `pagination`, optional `onRowClick`. Pagination uses `page / pageSize / total / onPageChange` contract; the component computes `pageCount = ceil(total / pageSize)`. Renders Prev/Next Button + `Page X of Y` text. Row click via onclick + Enter/Space keyboard.
- **Task 15** -- `PageHeader` (H1 + subtitle + optional action slot) and `DetailHeader` (back link + title + subtitle + optional status pill).

`/ui-demo` gets two more sections. `primitives.spec.ts` gains 3 tests (DataTable with pagination + row click, PageHeader action slot, DetailHeader back link + status pill).

Brainstorm-stop assessment: the "pagination" brainstorm marker discharges here. The plan's contract (Prev/Next + `Page X of Y`) is minimal, matches what pre-revamp PO list and invoice list already do, and supports the existing backend pagination API. Alternatives (numbered pages, load-more, cursor) add code without mock or product evidence. No user-facing stop.

Ship gates for 066:
- Mock-clarity: pagination pattern matches pre-revamp mock; headers match mock. No stop.
- Past-flow: 591 backend + 119 browser at iter open. Must stay green.
- Future-flow: DataTable imports Button; DetailHeader accepts a StatusPill via snippet. No iter-063 / iter-064 / iter-065 primitive is modified.

## JTBD (Jobs To Be Done)

- As a developer wiring the redesigned PO list in iter 071+, when I need a paginated table with clickable rows, I want `DataTable` with a `columns`/`rows`/`pagination`/`onRowClick` contract — so the list page does not reinvent table chrome.
- As a developer wiring any redesigned index page, when I need a title + subtitle + primary action button in the top slot, I want `PageHeader`.
- As a developer wiring any redesigned detail page, when I need a back link + title + subtitle + status pill at the top, I want `DetailHeader`.
- As a keyboard user on a redesigned list page, when I tab onto a row, I want Enter or Space to activate the same onclick the mouse would fire.

## Tasks

### Task 14 -- `DataTable` with server-driven pagination

- [x] Append `DataTable primitive` test to `primitives.spec.ts` (header visible, tbody 2 rows, click row updates click target, pagination text shows "Page 1 of 5"). Run — expect FAIL.
- [x] Create `frontend/src/lib/ui/DataTable.svelte` per plan Task 14 Step 2 with class rename `.wrap` → `ui-table`. Keep scoped `.pagination` inner class. `<table>` element has no class (no collision with pre-revamp global `.table` class, which applies only to elements with `class="table"`).
- [x] Extend `/ui-demo` with a DataTable section showing 2 rows + pagination (total=10, pageSize=2, page=1), plus a `<p data-testid="ui-table-click">` that binds to the last-clicked row id.
- [x] Run — expect PASS. Run `make test-browser` — expect **120 passed** (119 + 1).
- [x] Commit: `Add DataTable with server-driven pagination (iter 066 task 14)`.

### Task 15 -- `PageHeader` and `DetailHeader`

- [x] Append `Page + Detail headers` tests to `primitives.spec.ts` (2 tests: PageHeader has H1 "Invoices" + subtitle + action visible; DetailHeader has back link "All invoices" + title "INV-001" + status "Submitted"). Run — expect 2 FAIL.
- [x] Create `frontend/src/lib/ui/PageHeader.svelte` per plan Task 15 Step 2 with class rename `.page-header` → `ui-pageheader`.
- [x] Create `frontend/src/lib/ui/DetailHeader.svelte` per plan Task 15 Step 3 with class rename `.detail-header` → `ui-detailheader`.
- [x] Extend `/ui-demo` with a Headers section showing both.
- [x] Run — expect PASS. Run `make test-browser` — expect **122 passed** (120 + 2).
- [x] Commit: `Add PageHeader + DetailHeader primitives (iter 066 task 15)`.

## Existing test impact

Pre-iteration audit:
- `primitives.spec.ts` — extended by 3 new tests. Existing 19 tests unchanged.
- No pre-revamp spec touches `$lib/ui/`. Pre-revamp global `.table` rule would only apply if a new primitive rendered a `<table class="table">`; plan's DataTable has no class on its `<table>`, so no collision.
- `/ui-demo` grows from 11 sections to 13 (DataTable, Headers).
- The `ui-table-click` `<p>` inside `/ui-demo` is unique and does not collide with any existing testid.

No fixtures, mocks, or helpers need updating.

## Tests

### Permanent tests added this iteration
- `primitives.spec.ts` extended to **22 tests total**: existing 19 + 1 DataTable + 2 Headers.

Expected `make test-browser` count at close: **122 passed**.

### Scratch tests
None. Visual verification via `/ui-demo` on dev server.

### Logs
- `logs/playwright-test-browser.log` — `make test-browser` at iter close, expect 122 passed.
- `logs/pytest.log` — iter-open and iter-close (expect 591 passed).

## Notes

Iter 066 closed on 2026-04-24. Two commits landed on `ux-changes`:
- `1d5ebaa` Task 14 DataTable with server-driven pagination.
- `c9c7695` Task 15 PageHeader + DetailHeader.

119 Playwright passes at open → 120 after Task 14 → 122 at close. Backend stays 591.

### Decisions

- **Pagination pattern: Prev/Next + `Page X of Y`.** Simplest pattern; matches pre-revamp PO/invoice list. Numbered pages, load-more, and cursor paging deferred until a real consumer surfaces the need.
- **DataTable `<table>` has no class attribute.** Avoids collision with pre-revamp global `.table` rule (class selector, not element selector). Scoped CSS uses bare `table`, `th`, `td` element selectors which Svelte hashes per-component.
- **Row click wired via onclick + Enter/Space keyboard + tabindex=0.** ARIA-wise `<tr>` as a button target is unconventional but matches pre-revamp patterns. More formal `role="button"` can be added later if axe complains; currently clean.
- **`ui-pageheader` and `ui-detailheader` class names.** Single concatenated form (not `ui-page-header`) reads cleaner and follows the filename shape without hyphens.
- **No brainstorm stop on pagination.** The plan's contract is minimal and complete for all three planned consumers (PO list, invoice list, product list). Brainstorm marker discharged without user pause.

### DDD vocab assessment

No new domain terms. Primitive vocabulary (DataTable, PageHeader, DetailHeader) is UI design system. `docs/ddd-vocab.md` unchanged.

### Backlog captured

- **DataTable column sort.** The generic `Column<T>` type has no `sortable` flag. Future iteration when a consumer needs sorting can extend the contract with `sortable?: boolean` + `onSort?: (key, dir) => void`.
- **DataTable column filter.** Similar: no filter surface on the column definition. Defer.
- **DataTable empty-rows rendering.** Currently if `rows` is empty, the table renders an empty `<tbody>`. A real consumer may want to show EmptyState inside the table. Consumer can conditionally render; primitive stays simple.
- **Row-click ARIA.** `role="button"` on `<tr>` or switch to a cell-button pattern if axe flags it.
- **Pagination alternatives.** Numbered pages / load-more / cursor — add when a consumer or mock surfaces the need.

### What exists after iter 066

Twenty-one primitives under `frontend/src/lib/ui/`:
- Leaves (iter 063, 7): Button, StatusPill, ProgressBar, Input, Select, DateInput, Toggle.
- Composites (iter 064, 5): FormField, PanelCard, AttributeList, FormCard, KpiCard.
- Display + state (iter 065, 6): Timeline, ActivityFeed, LoadingState, EmptyState, ErrorState, ErrorBoundary.
- Table + headers (iter 066, 3): DataTable, PageHeader, DetailHeader.

`primitives.spec.ts`: 22 tests. `/ui-demo`: 13 sections.

Carried forward: none.