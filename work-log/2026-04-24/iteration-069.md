# Iteration 069 -- UserMenu + redirect infrastructure + nexus-shell smoke

## Context

Ninth iteration of Phase 4.0. Iter 068 closed with 25 primitives, 140 Playwright passes, 591 backend passes. This iteration ships the last three foundation pieces (Plan Tasks 23, 24, 25):

- **Task 23** -- `UserMenu` primitive. The user pill shown in TopBar. Plan design: `[avatar][name + role stacked][▾]` pill + dropdown on click containing Log out. Plan Task 22 brainstorm was pre-resolved from mock evidence in iter 068.
- **Task 24** -- `redirects.ts` + spec. A pure-logic module mapping old-route patterns to new-route patterns (`/po/:id` → `/production/:id` etc.). Ships empty registry in Phase 4.0; aggregate phases populate it when retiring old routes.
- **Task 25** -- `nexus-shell.spec.ts` + `(nexus)/_smoke/+page.svelte`. Permanent end-to-end test proving AppShell composes correctly under the `(nexus)` layout with real role-based sidebar filtering and auth-redirect on 401.

After iter 069, Phase 4.0 ships its feature-complete primitive foundation. Iter 070 handles phase-close (axe scan, screenshots, work-log summary).

### Plan deviations from mock evidence

- **UserMenu mobile collapse**: plan shows `[avatar][meta][▾]` always. Mock shows `[avatar][▾]` on mobile (meta hidden). Add `@media (max-width: 767px) { .meta { display: none; } }` to the primitive's style block.
- **Dev role switcher**: plan's `import.meta.env.DEV` split ships as-is. The dev variant appends a "Switch role" submenu that mutates a local dev store; Phase 4.0 ships the store infrastructure BUT does not wire pages to react to it (role consumed from `$app/state`'s `page.data.user` in iter 071+). If the user's Log out action fails, swallow the error and still redirect to `/login` (plan pattern).

### Nexus smoke test

Currently `(nexus)/` has only `+layout.ts` (auth redirect) and `+layout.svelte` (passthrough). Task 25 adds the first content route: `(nexus)/_smoke/+page.svelte`. It's internal — not linked from nav — but Playwright navigates to `/_smoke` (SvelteKit resolves `(nexus)` layout group automatically).

Three test cases:
1. ADMIN at `/_smoke` sees all 6 sidebar items (Dashboard, POs, Invoices, Vendors, Products, Users).
2. VENDOR at `/_smoke` does NOT see the Vendors link.
3. Unauthenticated `GET /_smoke` → `/api/v1/auth/me` returns 401 → layout redirects to `/login`.

This spec protects every future aggregate page that lands under `(nexus)/` — if the shell or role filtering breaks, this fails first.

Ship gates for 069:
- Mock-clarity: UserMenu resolved from mock. Redirect infra and smoke test are pure plumbing; no mock needed.
- Past-flow: 591 backend + 140 Playwright at iter open. Must stay green.
- Future-flow: UserMenu is consumed by AppShell via the `userMenu` snippet; wiring shows in `/ui-demo/shell` and `/_smoke` routes.

## JTBD (Jobs To Be Done)

- As an ADMIN in the revamped shell, when I click the user pill in the top-right, I want a dropdown with a Log out action, so I can end my session without hunting for a settings page.
- As a developer testing role-conditional rendering locally, when I'm on the dev server, I want a "Switch role" submenu inside the UserMenu so I can simulate different roles without logout/login cycles. The switch is stripped from prod builds.
- As an engineer retiring an old route in a future aggregate phase, when I need to redirect `/po/123` → `/production/123`, I want to add one line to `redirects.ts` and have a spec cover the mapping.
- As a future maintainer verifying the `(nexus)` layout still composes, when I run `make test-browser`, I want a permanent smoke test that catches shell regressions before they reach production.

## Tasks

### Task 23 -- `UserMenu` primitive

- [x] Append `UserMenu primitive` describe block to `primitives.spec.ts`:
  - At ≥768px: pill visible, click opens menu, Log out button visible.
  - At <768px: meta hidden (avatar + chevron only), click opens menu, Log out button visible.
  Run — expect FAIL.
- [x] Create `frontend/src/lib/ui/UserMenu.svelte` (class `ui-user-menu`):
  - Props: `name: string`, `role: UserRole`, `'data-testid'?: string`.
  - State: `open = $state(false)`.
  - Toggle on button click; renders `<div role="menu">` with Log out button (`data-testid={testid}-logout`).
  - Handles logout via `$lib/auth` `logout()` + `goto('/login')`; catches errors so logout always redirects.
  - Renders `aria-haspopup="menu"` and `aria-expanded={open}` on the pill button.
  - Scoped CSS: `.meta` hidden on mobile via media query; `.menu` positioned absolute top-right; avatar uses `--brand-accent` bg with initials.
  - Dev variant: when `import.meta.env.DEV`, insert a "Switch role" disabled placeholder item in the menu with a TODO comment (full dev store wiring backlog'd, ships as a visible affordance for future implementation).
- [x] Update `/ui-demo/shell/+page.svelte` to pass a `UserMenu` snippet into `AppShell`:

```svelte
<script lang="ts">
	import AppShell from '$lib/ui/AppShell.svelte';
	import UserMenu from '$lib/ui/UserMenu.svelte';
</script>

<AppShell
	role="ADMIN"
	roleLabel="Supply Manager"
	breadcrumb="Workspace / Shell Demo"
	data-testid="ui-appshell"
>
	{#snippet sidebarFooter()}...{/snippet}
	{#snippet userMenu()}
		<UserMenu name="Supply Manager" role="ADMIN" data-testid="ui-usermenu" />
	{/snippet}
	<p>Shell demo content.</p>
</AppShell>
```

- [x] Run — expect PASS. Run `make test-browser` — expect **142 passed** (140 + 2 UserMenu tests).
- [x] Commit: `Add UserMenu primitive with Log out (iter 069 task 23)`.

### Task 24 -- Redirect infrastructure

- [x] Create `frontend/tests/redirects.spec.ts`:
  - Test: unmapped path returns `null`.
  - Test: mapped path with a `:param` returns the substituted new path.
  Run — expect FAIL.
- [x] Create `frontend/src/lib/ui/redirects.ts`:
  - `REDIRECTS: Record<string, string>` — empty in 4.0.
  - `resolveRedirect(pathname, registry = REDIRECTS): string | null` — matches `:param` placeholders with named-capture regex, substitutes into the target template.
- [x] Run the spec — expect PASS. Run `make test-browser` — expect **144 passed** (142 + 2).
- [x] Commit: `Add redirect infrastructure for aggregate-phase retirements (iter 069 task 24)`.

### Task 25 -- `nexus-shell.spec.ts` + sentinel route

- [x] Create `frontend/src/routes/(nexus)/_smoke/+page.svelte` — uses `AppShell` + `UserMenu`, reads `user` from `$app/state`'s `page.data.user`, passes `role` + `display_name` + `roleLabel` derived from a simple role→label map, renders `<h1>Nexus smoke</h1>` as content.
- [x] Create `frontend/tests/nexus-shell.spec.ts` with three tests:
  - ADMIN at `/_smoke` sees all 6 sidebar links (Dashboard, Purchase Orders, Invoices, Vendors, Products, Users).
  - VENDOR at `/_smoke` has NO Vendors link (`toHaveCount(0)`).
  - Unauth at `/_smoke` (auth/me returns 401) redirects to `/login`.
- [x] Run the spec — expect PASS. Run `make test-browser` — expect **147 passed** (144 + 3).
- [x] Commit: `Add nexus-shell smoke test + sentinel route (iter 069 task 25)`.

## Existing test impact

- `primitives.spec.ts` grows by 2 (UserMenu desktop + mobile).
- `redirects.spec.ts` is NEW, 2 tests.
- `nexus-shell.spec.ts` is NEW, 3 tests.
- `/ui-demo/shell/+page.svelte` modified to include `UserMenu`; the existing 3 AppShell tests continue to pass because they don't assert on user-pill contents.
- Pre-revamp specs: untouched.

No fixtures, mocks, or helpers need updating.

## Tests

### Permanent tests at iter close
- `primitives.spec.ts`: 31 + 2 = **33 tests**.
- `sidebar-items.spec.ts`: 7 tests (unchanged).
- `redirects.spec.ts`: **2 tests** (new).
- `nexus-shell.spec.ts`: **3 tests** (new).
- Everything else: unchanged.

Expected `make test-browser` count at close: **147 passed** (140 + 7).

### Scratch tests
None.

### Logs
- `logs/playwright-test-browser.log` — close snapshot, expect 147 passed.
- `logs/pytest.log` — expect 591 passed.

## Notes

Iter 069 closed on 2026-04-24. Four commits landed on `ux-changes`:
- Open doc (committed earlier).
- `15785bc` Task 23 UserMenu primitive with Log out + dev-only Switch role placeholder.
- `080a649` Task 24 redirect infrastructure (empty registry, `resolveRedirect` with `:param` substitution).
- `063e690` Task 25 nexus-shell smoke test + `(nexus)/_smoke/+page.svelte` sentinel route.

140 Playwright at open → 142 after Task 23 → 145 after Task 24 → 148 at close. Backend stays 591.

### Decisions

- **UserMenu mobile meta collapse**: `@media (max-width: 767px) { .meta { display: none; } }` per mock. Tested explicitly at 390px and 1440px viewports.
- **Dev role switcher**: ships as a disabled menu item gated behind `import.meta.env.DEV`. Full dev-store wiring (how a role switch propagates to `$app/state`'s `page.data.user`) is backlog'd for a dedicated dev-tools iteration. Phase 4.0 ships structural affordance only.
- **Logout failure handling**: `try { await logout(); } catch {} goto('/login')` — errors swallowed so user always exits. Plan pattern accepted.
- **Sidebar assertion scoping in nexus smoke test**: implementer correctly discovered that the pre-revamp `+layout.svelte` renders its own nav with colliding link names. Scoped all sidebar assertions to `page.getByTestId('ui-appshell-sidebar').getByRole(...)` inside `nexus-shell.spec.ts`. This is the right move — asserts against the NEW shell, not whatever pre-revamp chrome happens to also render.

### Plan deviations (documented)

- Plan Task 25's smoke spec used unscoped `page.getByRole('link', { name: 'Dashboard' })`. That collides with the pre-revamp top nav which still renders when the route path is a non-`(nexus)` one (but actually `/_smoke` IS under `(nexus)`, so only the new shell should render...). The subagent scoped to the shell testid regardless — defensive and correct.

### DDD vocab assessment

No new domain terms. `docs/ddd-vocab.md` unchanged.

### Backlog captured

- **Dev role-switcher wiring**: wire the UserMenu's Switch role item to mutate a local dev store that `$app/state`'s `page.data.user` subscribes to. Requires a `$lib/dev/role-store.ts` + a hook in `+layout.ts`. Not Phase 4.0 scope.
- **Keyboard escape closes UserMenu dropdown**: currently only clicking the pill again closes it. Add `onkeydown` for Escape. Low priority.
- **Outside-click dismisses UserMenu**: currently the dropdown stays open if the user clicks outside. Add a click-outside listener. Minor UX polish.
- **Redirect hook wiring**: `resolveRedirect()` exists but no `hooks.server.ts` or `+layout.ts` consumes it yet. Future aggregate phases install it when retiring a route.
- **Smoke test covers every role**: currently only ADMIN and VENDOR are covered. Add SM, FREIGHT_MANAGER, QUALITY_LAB, PROCUREMENT_MANAGER if appetite for more assertions grows. Low priority — `sidebar-items.spec.ts` already covers the role-matrix logic at the data layer.

### What exists after iter 069

Twenty-six primitives under `frontend/src/lib/ui/`:
- Leaves (iter 063, 7): Button, StatusPill, ProgressBar, Input, Select, DateInput, Toggle.
- Composites (iter 064, 5): FormField, PanelCard, AttributeList, FormCard, KpiCard (with icon slot).
- Display + state (iter 065, 6): Timeline, ActivityFeed, LoadingState, EmptyState, ErrorState, ErrorBoundary.
- Table + headers (iter 066, 3): DataTable, PageHeader, DetailHeader.
- Shell (iter 067-069, 5): Sidebar (sections + footer + roleLabel), TopBar, AppShell, UserMenu, + `sidebar-items.ts`, `redirects.ts`.

New routes:
- `/ui-demo/shell` — AppShell preview with UserMenu + sidebarFooter.
- `/(nexus)/_smoke` — permanent sentinel route exercising the (nexus) layout end-to-end.

Tests:
- `primitives.spec.ts`: 33 tests.
- `sidebar-items.spec.ts`: 7 tests.
- `redirects.spec.ts`: 3 tests.
- `nexus-shell.spec.ts`: 3 tests.
- Plus all pre-revamp specs — total **148 Playwright passes**.

Carried forward: none.