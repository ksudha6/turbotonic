# Iteration 067 -- sidebar-items.ts + Sidebar primitive + per-role brainstorm

## Context

Seventh iteration of Phase 4.0. Iter 066 closed with 21 primitives live, 122 Playwright passes, 591 backend passes. This iteration ships the shell navigation foundation: a typed per-role `sidebar-items.ts` module and a `Sidebar` primitive that consumes it (Plan Tasks 16-17). Task 18 is a **mandatory brainstorm stop** — the plan instructs me to pause between Task 17 and Task 18 and ask the user about per-role item sets before finalizing.

The conservative mirror for Task 16 derives sidebar items from the existing `$lib/permissions.ts` helpers (`canViewPOs`, `canViewInvoices`, `canManageVendors`, `canViewProducts`) plus a Dashboard row every role gets. Today's `+layout.svelte` produces the same set via a role switch; we are centralizing the logic, not adding new capability.

Conservative-mirror outcome per role:
- **ADMIN**: Dashboard, Purchase Orders, Invoices, Vendors, Products (inherits all via `is()` short-circuit from iter 061)
- **SM**: Dashboard, Purchase Orders, Invoices, Vendors, Products
- **VENDOR**: Dashboard, Purchase Orders, Invoices
- **FREIGHT_MANAGER**: Dashboard, Purchase Orders
- **QUALITY_LAB**: Dashboard, Products
- **PROCUREMENT_MANAGER**: Dashboard only (no `canView*` guard returns true)

Task 18 surfaces the brainstorm question: does this matrix need changes before locking it in? Particularly: should FREIGHT_MANAGER see Shipments (today's `/shipments/[id]` detail exists), should ADMIN see a Users placeholder, should PROCUREMENT_MANAGER get more than Dashboard?

Ship gates for 067:
- Mock-clarity: the Lovable mock shows a 4-role sidebar that does not match our 6-role enum. The conservative mirror is our best starting point. Task 18 brainstorm is where the mock / real roles are reconciled with the user — **explicit stop**.
- Past-flow: 591 backend + 122 browser at iter open. Must stay green.
- Future-flow: Sidebar consumes `sidebar-items.ts` via `$derived`. No iter 063-066 primitive is modified.

## JTBD (Jobs To Be Done)

- As a developer wiring the AppShell in iter 068, when I need a sidebar for the current user's role, I want to render `<Sidebar role={user.role} />` and have the correct item set appear without re-inventing the role → items map.
- As an ADMIN using the redesigned portal, when I open the sidebar, I want every aggregate page I can reach (Dashboard, POs, Invoices, Vendors, Products) one click away.
- As a VENDOR, when I open the sidebar, I want Dashboard + Purchase Orders + Invoices — no exposure to Vendors or Products management.
- As a keyboard user with a screen reader, when I navigate the sidebar, I want the current page marked with `aria-current="page"` on the active link.

## Tasks

### Task 16 -- `sidebar-items.ts` (conservative mirror)

- [ ] Create `frontend/tests/sidebar-items.spec.ts` with four role-matrix tests (ADMIN, VENDOR, QUALITY_LAB, FREIGHT_MANAGER). Run — expect FAIL (module does not exist).
- [ ] Create `frontend/src/lib/ui/sidebar-items.ts` with `SidebarItem` type (`href`, `label`, `match: (pathname) => boolean`) and `sidebarItemsFor(role: UserRole): SidebarItem[]`. Derive the per-role list from `$lib/permissions` helpers plus a universal Dashboard row. `match` for POs matches `/po*` or `/production*`; Invoices matches `/invoice*` / `/invoices*`; Vendors `/vendors*`; Products `/products*`.
- [ ] Run the spec — expect PASS.
- [ ] Commit: `Add sidebar-items.ts derived from permissions.ts (iter 067 task 16)`.

### Task 17 -- `Sidebar` primitive

- [ ] Append `Sidebar primitive` tests to `primitives.spec.ts` (2 tests: renders Dashboard + POs links for ADMIN; each link has a valid href). Use the plan's deviation where the aria-current test is replaced with an `href` regex check, because `/ui-demo` is not `/dashboard`.
- [ ] Create `frontend/src/lib/ui/Sidebar.svelte` per plan Task 17 Step 2 with class rename `.sidebar` → `ui-sidebar` (outermost). Uses `$app/state` `page.url.pathname` for active matching.
- [ ] Extend `/ui-demo` with a Sidebar preview section using `role="ADMIN"`.
- [ ] Run — expect PASS. Run `make test-browser` — expect **124 passed** (122 + 2).
- [ ] Commit: `Add Sidebar primitive wired to permissions (iter 067 task 17)`.

### Task 18 -- BRAINSTORM STOP

- [ ] **Pause execution.** Surface the per-role sidebar brainstorm to the user. Question (plan-prescribed):
  > Phase 4.0 needs a decision on per-role sidebar items. Task 16 implemented a mirror of today's layout. Confirm or extend:
  > - ADMIN: Dashboard, POs, Invoices, Vendors, Products
  > - SM: same as ADMIN
  > - VENDOR: Dashboard, POs, Invoices
  > - FREIGHT_MANAGER: Dashboard, POs (should Shipments be added?)
  > - QUALITY_LAB: Dashboard, Products
  > - PROCUREMENT_MANAGER: Dashboard only (no permissions wired)
  >
  > OK to proceed with this mapping, or change any row?
- [ ] On user response:
  - If confirm: no code change; close iter 067 with a note that the mapping is locked.
  - If edits: update `sidebar-items.ts` and `sidebar-items.spec.ts`, re-run, commit `Lock per-role sidebar items after brainstorm (iter 067 task 18)`.

## Existing test impact

Pre-iteration audit:
- `frontend/tests/primitives.spec.ts` — extended by 2 new Sidebar tests. 22 existing tests untouched.
- `frontend/tests/sidebar-items.spec.ts` — NEW, 4 unit-style tests for the role matrix.
- No pre-revamp spec touches `$lib/ui/` or the yet-unbuilt `sidebar-items.ts`.
- `/ui-demo` grows from 13 sections to 14 (Sidebar preview).
- `$lib/permissions.ts` is read-only in this iter (no edits). If the brainstorm surfaces a new permission gate (e.g. for PROCUREMENT_MANAGER), that goes on the backlog for a future iter — permissions module changes must be their own small iteration.

No fixtures, mocks, or helpers need updating.

## Tests

### Permanent tests added this iteration
- `frontend/tests/sidebar-items.spec.ts`: 4 new tests covering ADMIN, VENDOR, QUALITY_LAB, FREIGHT_MANAGER role matrices.
- `frontend/tests/primitives.spec.ts` extended with 2 Sidebar tests (**24 tests total**).

Expected `make test-browser` count at close: **128 passed** (122 + 4 role-matrix + 2 Sidebar).

### Scratch tests
None.

### Logs
- `logs/playwright-test-browser.log` — close snapshot, expect 128 passed.
- `logs/pytest.log` — expect 591 passed both open and close.

## Notes

Iter 067 closed on 2026-04-24. Four commits landed on `ux-changes`:
- `4a3394f` Open iter doc.
- `44e5085` Task 16 `sidebar-items.ts` (initial mirror derived from `permissions.ts`) + spec.
- `98ad244` Task 17 `Sidebar` primitive consuming `sidebar-items`.
- `1c47336` Task 18 post-brainstorm: `sidebar-items.ts` rewritten as explicit `Record<UserRole, SidebarItem[]>`, decoupled from `permissions.ts`; spec expanded.

122 Playwright at open → 126 after Task 16 → 128 after Task 17 → 130 at close. Backend stays 591.

### Brainstorm resolution (Task 18)

User confirmed and extended:
- **FREIGHT_MANAGER gains Invoices** in the sidebar. OpEx-only scoping is a page-level concern — backlog'd for iter 071+ aggregate pages.
- **ADMIN gains Users** in the sidebar, pointing to `/users`. Route doesn't exist yet (404); will be built in a future iteration. Memory backlog already tracks the Users management page.
- **SM PO list filtered to procurement-only** — backlog'd (page-level filter, not sidebar).
- **FREIGHT_MANAGER PO list filtered to OpEx-only** — backlog'd (page-level filter).
- **Shipments** not added (no dedicated list/detail page in the revamp yet).

### Design decision

Sidebar visibility decoupled from `permissions.ts` capability helpers. The `canView*` helpers gate page-level access (backend + route guards). Sidebar is a separate nav-visibility concern — the new explicit `Record<UserRole, SidebarItem[]>` map makes every role's items auditable in one place. Adding FREIGHT_MANAGER to `canViewInvoices` would have leaked backend access before we're ready; explicit mapping avoids that.

TypeScript `Record<UserRole, SidebarItem[]>` guarantees exhaustiveness: if a new role is added to `UserRole` and not to the map, the compiler errors.

### DDD vocab assessment

No new domain terms. `docs/ddd-vocab.md` unchanged.

### Backlog captured

- **FREIGHT_MANAGER OpEx-invoice access.** Backend invoice list endpoint currently does not filter by vendor type. Need a vendor-type-scoped filter for FREIGHT_MANAGER reads, plus update `canViewInvoices` in `permissions.ts` to include FREIGHT_MANAGER. Iter 071+ when redesigning `/invoices`.
- **FREIGHT_MANAGER OpEx-PO filter on PO list.** Same pattern.
- **SM PO list filtered to procurement-only.** Even though SM has `canViewPOs`, the list UI should default-filter to PROCUREMENT type.
- **Users management page `/users`.** ADMIN-only CRUD for users. Nav link already shipped in iter 067; page 404s until built.
- **Sidebar primitive test weak-guard.** Task 17 test `each sidebar link has a valid href` used `links.all()` which returns `[]` when the locator finds nothing, so the assertion trivially passed in the failing-first run. Strengthen with an `expect(locator).not.toHaveCount(0)` precondition, or rely on the first test (which did FAIL correctly) as the primary guard. Minor.

### What exists after iter 067

Twenty-two primitives under `frontend/src/lib/ui/`:
- Leaves (iter 063, 7): Button, StatusPill, ProgressBar, Input, Select, DateInput, Toggle.
- Composites (iter 064, 5): FormField, PanelCard, AttributeList, FormCard, KpiCard.
- Display + state (iter 065, 6): Timeline, ActivityFeed, LoadingState, EmptyState, ErrorState, ErrorBoundary.
- Table + headers (iter 066, 3): DataTable, PageHeader, DetailHeader.
- Shell (iter 067, 1): Sidebar.

Plus `sidebar-items.ts` module exporting explicit role → items map.

`primitives.spec.ts`: 24 tests. `sidebar-items.spec.ts`: 6 tests. `/ui-demo`: 14 sections.

Carried forward: none.