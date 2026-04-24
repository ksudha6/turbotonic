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

Pending — filled at iteration close after the brainstorm resolves.

### PM-delegate decisions (autonomous mode)

- **Conservative mirror for Task 16.** Plan explicitly says: implement the conservative version that mirrors today's layout; Task 18 revisits. No judgment call — follow plan.
- **Sidebar's aria-current test swap.** Plan swaps the aria-current test for an href-regex test because `/ui-demo` is not `/dashboard` so nothing matches. Accepting the plan's swap.
- **Brainstorm question sent verbatim.** The plan wrote the exact question to ask. I send it without paraphrase so the user sees the same phrasing the plan expected.