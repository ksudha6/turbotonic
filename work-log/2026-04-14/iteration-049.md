# Iteration 049 -- Design system and component library

## Context

The frontend has ~22 pages but no reusable components: every page reimplements buttons, inputs, tables, modals, and badges with inline CSS, and three separate dialogs duplicate the same overlay markup. This iteration builds a shared component library (Button, Input, Select, DataTable, Modal, Badge, Toast, Tabs, etc.) and adds semantic design tokens to `global.css`. The library is the foundation for iterations 050-055, which apply it to every page.

## JTBD (Jobs To Be Done)

- When building a new page, I want a library of consistent, tested components, so that I don't reimplement buttons, inputs, tables, and modals from scratch each time.
- When updating the visual design, I want a single set of design tokens (colors, typography, spacing), so that changes propagate across the entire app.
- When using a form field, I want built-in label, error state, and helper text, so that every form has consistent validation UX.
- When viewing a data table, I want built-in sort indicators, pagination, empty state, and loading skeleton, so that list pages are uniform.
- When a long-running action completes or fails, I want a toast notification, so that feedback is visible without blocking the page.

## Tasks

### Design tokens (`frontend/src/lib/styles/global.css`)
- [ ] Define semantic color tokens mapped to the existing color scale:
  - `--color-primary`: blue-600
  - `--color-primary-hover`: blue-700
  - `--color-primary-light`: blue-100
  - `--color-secondary`: gray-600
  - `--color-surface`: white
  - `--color-surface-alt`: gray-50
  - `--color-border`: gray-200
  - `--color-border-strong`: gray-300
  - `--color-error`: red-600
  - `--color-error-light`: red-100
  - `--color-warning`: amber-600
  - `--color-warning-light`: amber-100
  - `--color-success`: green-600
  - `--color-success-light`: green-100
  - `--color-text-primary`: gray-900
  - `--color-text-secondary`: gray-600
  - `--color-text-muted`: gray-400
- [ ] Typography scale: add missing sizes and weights
  - `--font-size-xs`: 0.75rem
  - `--font-size-3xl`: 1.875rem
  - `--font-weight-normal`: 400
  - `--font-weight-medium`: 500
  - `--font-weight-semibold`: 600
  - `--font-weight-bold`: 700
  - `--line-height-tight`: 1.25
  - `--line-height-relaxed`: 1.75
- [ ] Spacing: add `--space-0`: 0, `--space-14`: 3.5rem, `--space-20`: 5rem, `--space-24`: 6rem
- [ ] Add named radius tokens: `--radius`: 0.375rem (default, alias for radius-md)
- [ ] Add transition token: `--transition-fast`: 150ms ease, `--transition-normal`: 200ms ease

### Button component (`frontend/src/lib/components/Button.svelte`)
- [ ] Props: `variant` (primary | secondary | ghost | danger), `size` (sm | md | lg), `loading` (boolean), `disabled` (boolean), `type` (button | submit | reset), `href` (optional, renders `<a>` instead)
- [ ] Loading state: show spinner icon, disable click
- [ ] Replaces all `.btn .btn-primary`, `.btn .btn-secondary`, `.btn .btn-danger`, `.btn .btn-success` usage across the app

### Input component (`frontend/src/lib/components/Input.svelte`)
- [ ] Props: `type` (text | number | date | email), `label`, `value` (bindable), `placeholder`, `required`, `disabled`, `error` (string), `helperText` (string), `id`
- [ ] Renders label above input, error message below (red), helper text below (gray)
- [ ] Required indicator: asterisk after label
- [ ] Focus ring consistent with design tokens

### TextArea component (`frontend/src/lib/components/TextArea.svelte`)
- [ ] Same pattern as Input but for multi-line text
- [ ] Props: `label`, `value` (bindable), `rows`, `placeholder`, `required`, `error`, `helperText`

### Select component (`frontend/src/lib/components/Select.svelte`)
- [ ] Props: `label`, `value` (bindable), `options` (array of `{value, label}`), `placeholder` (default first option text), `required`, `disabled`, `error`
- [ ] Renders native `<select>` with consistent styling
- [ ] Required indicator, error state same as Input

### Table component (`frontend/src/lib/components/DataTable.svelte`)
- [ ] Props: `columns` (array of `{key, label, sortable?, align?}`), `rows` (array of objects), `sortBy` (bindable), `sortDir` (bindable), `loading`, `emptyMessage`, `onRowClick`
- [ ] Sortable column headers with up/down arrow indicators
- [ ] Loading state: skeleton rows (8 rows of pulsing gray bars)
- [ ] Empty state: centered message with muted text
- [ ] Slot for custom cell rendering per column
- [ ] Row hover highlight, cursor pointer when onRowClick is provided

### Pagination component (`frontend/src/lib/components/Pagination.svelte`)
- [ ] Props: `page` (bindable), `pageSize` (bindable), `total`, `pageSizeOptions` (default [10, 20, 50])
- [ ] Shows "Showing X-Y of Z", page size selector, Previous/Next buttons, "Page N of M"
- [ ] Disable Previous on page 1, Next on last page

### Card component (`frontend/src/lib/components/Card.svelte`)
- [ ] Slots: `header`, default (body), `footer`
- [ ] Renders the existing `.card` pattern but as a component
- [ ] Optional `padding` prop (default true; false for edge-to-edge table content)

### Badge component (`frontend/src/lib/components/Badge.svelte`)
- [ ] Props: `variant` (draft | pending | accepted | rejected | revised | submitted | approved | paid | disputed | active | inactive | cert-required | info | warning | error | success), `size` (sm | md)
- [ ] Replaces StatusPill (which only handles status strings) and all inline badge CSS
- [ ] Color mappings from variant to background/text color pairs

### Modal component (`frontend/src/lib/components/Modal.svelte`)
- [ ] Props: `open` (bindable), `title`, `size` (sm | md | lg)
- [ ] Slots: default (body), `footer`
- [ ] Close on Escape key, close on overlay click
- [ ] Focus trap within modal when open
- [ ] Replaces the duplicated overlay/dialog pattern in RejectDialog, DisputeDialog, CreateInvoiceDialog, and the PO list bulk reject modal

### Toast component (`frontend/src/lib/components/Toast.svelte` + `frontend/src/lib/stores/toast.ts`)
- [ ] Toast store: `addToast(message, type, duration?)` where type is success | error | warning | info
- [ ] Auto-dismiss after duration (default 5000ms)
- [ ] Stack multiple toasts vertically (bottom-right)
- [ ] ToastContainer component rendered once in the layout
- [ ] Replaces ad-hoc `bulkMessage` patterns

### Dropdown component (`frontend/src/lib/components/Dropdown.svelte`)
- [ ] Props: `items` (array of `{label, value, icon?, disabled?, danger?}`), `onSelect`
- [ ] Trigger slot (button that opens the menu)
- [ ] Positioned below trigger, closes on click outside or Escape
- [ ] Used for action menus (row actions, status actions)

### Tabs component (`frontend/src/lib/components/Tabs.svelte`)
- [ ] Props: `tabs` (array of `{key, label}`), `activeTab` (bindable)
- [ ] Renders horizontal tab bar with underline indicator on active tab
- [ ] Slot receives active tab key for conditional rendering
- [ ] Used on detail pages (PO detail: Line Items | Invoices | Milestones | Activity)

### Pages with inline styles / ad-hoc patterns to be replaced

| Page | File | What gets replaced |
|------|------|--------------------|
| Dashboard | `routes/dashboard/+page.svelte` | Inline summary cards, feed items, pipeline table, overdue table |
| PO list | `routes/po/+page.svelte` | Inline table, filter bar, pagination, bulk toolbar, reject modal |
| PO detail | `routes/po/[id]/+page.svelte` | Inline info-grid, line items table, actions bar, invoice table |
| PO create | `routes/po/new/+page.svelte` | Uses POForm (which has inline line-item table, form-grid) |
| PO edit | `routes/po/[id]/edit/+page.svelte` | Same as PO create |
| Invoice list | `routes/invoices/+page.svelte` | Inline table, filter bar, pagination, bulk toolbar |
| Invoice detail | `routes/invoice/[id]/+page.svelte` | Inline info-grid, line items table, actions bar |
| Vendor list | `routes/vendors/+page.svelte` | Inline table, filter bar, inline badge CSS |
| Vendor create | `routes/vendors/new/+page.svelte` | Inline form-grid, form-actions |
| Product list | `routes/products/+page.svelte` | Inline table, filter bar, inline badge CSS |
| Product create | `routes/products/new/+page.svelte` | Inline form-grid, form-actions |
| Product edit | `routes/products/[id]/edit/+page.svelte` | Inline form-grid, readonly values |
| Layout | `routes/+layout.svelte` | Inline nav bar (replaced in iter 050) |

Components with duplicated patterns:
| Component | File | What gets replaced |
|-----------|------|--------------------|
| StatusPill | `lib/components/StatusPill.svelte` | Replaced by Badge component |
| RejectDialog | `lib/components/RejectDialog.svelte` | Rebuilt using Modal |
| DisputeDialog | `lib/components/DisputeDialog.svelte` | Rebuilt using Modal |
| CreateInvoiceDialog | `lib/components/CreateInvoiceDialog.svelte` | Rebuilt using Modal + DataTable |
| POForm | `lib/components/POForm.svelte` | Rebuilt using Input, Select, TextArea, Button |
| NotificationBell | `lib/components/NotificationBell.svelte` | Rebuilt using Dropdown |

### Tests (scratch)
- [ ] Screenshot each component in isolation at 1280px (desktop) and 375px (mobile):
  - Button: all variants x all sizes, loading state, disabled state
  - Input: normal, focused, error, disabled, with helper text
  - Select: normal, open, error
  - DataTable: with data, loading skeleton, empty state, sorted column
  - Card: with header/body/footer
  - Badge: all variants
  - Modal: sm, md, lg sizes
  - Toast: all types stacked
  - Dropdown: open state
  - Tabs: active tab indicator
- [ ] Screenshot the global CSS token palette (a test page rendering color swatches, type scale, spacing blocks)
- [ ] Verify existing Playwright permanent tests still pass (functional behavior unchanged)

## Acceptance criteria
- [ ] All 12 components exist in `frontend/src/lib/components/` and render correctly
- [ ] Design tokens in `global.css` include semantic color aliases, full typography scale, and transition tokens
- [ ] No page-level CSS duplicates the patterns these components encapsulate (no more inline `.overlay`, `.dialog`, `.badge-*` definitions in page files)
- [ ] StatusPill is removed; all status rendering uses Badge
- [ ] RejectDialog, DisputeDialog, CreateInvoiceDialog rebuilt using Modal
- [ ] POForm rebuilt using Input, Select, TextArea, Button
- [ ] Toast store exists and ToastContainer is mounted in the layout
- [ ] All existing permanent Playwright tests pass without modification (functional behavior unchanged)
