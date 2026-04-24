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

- [ ] Append `UserMenu primitive` describe block to `primitives.spec.ts`:
  - At ≥768px: pill visible, click opens menu, Log out button visible.
  - At <768px: meta hidden (avatar + chevron only), click opens menu, Log out button visible.
  Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/UserMenu.svelte` (class `ui-user-menu`):
  - Props: `name: string`, `role: UserRole`, `'data-testid'?: string`.
  - State: `open = $state(false)`.
  - Toggle on button click; renders `<div role="menu">` with Log out button (`data-testid={testid}-logout`).
  - Handles logout via `$lib/auth` `logout()` + `goto('/login')`; catches errors so logout always redirects.
  - Renders `aria-haspopup="menu"` and `aria-expanded={open}` on the pill button.
  - Scoped CSS: `.meta` hidden on mobile via media query; `.menu` positioned absolute top-right; avatar uses `--brand-accent` bg with initials.
  - Dev variant: when `import.meta.env.DEV`, insert a "Switch role" disabled placeholder item in the menu with a TODO comment (full dev store wiring backlog'd, ships as a visible affordance for future implementation).
- [ ] Update `/ui-demo/shell/+page.svelte` to pass a `UserMenu` snippet into `AppShell`:

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

- [ ] Run — expect PASS. Run `make test-browser` — expect **142 passed** (140 + 2 UserMenu tests).
- [ ] Commit: `Add UserMenu primitive with Log out (iter 069 task 23)`.

### Task 24 -- Redirect infrastructure

- [ ] Create `frontend/tests/redirects.spec.ts`:
  - Test: unmapped path returns `null`.
  - Test: mapped path with a `:param` returns the substituted new path.
  Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/redirects.ts`:
  - `REDIRECTS: Record<string, string>` — empty in 4.0.
  - `resolveRedirect(pathname, registry = REDIRECTS): string | null` — matches `:param` placeholders with named-capture regex, substitutes into the target template.
- [ ] Run the spec — expect PASS. Run `make test-browser` — expect **144 passed** (142 + 2).
- [ ] Commit: `Add redirect infrastructure for aggregate-phase retirements (iter 069 task 24)`.

### Task 25 -- `nexus-shell.spec.ts` + sentinel route

- [ ] Create `frontend/src/routes/(nexus)/_smoke/+page.svelte` — uses `AppShell` + `UserMenu`, reads `user` from `$app/state`'s `page.data.user`, passes `role` + `display_name` + `roleLabel` derived from a simple role→label map, renders `<h1>Nexus smoke</h1>` as content.
- [ ] Create `frontend/tests/nexus-shell.spec.ts` with three tests:
  - ADMIN at `/_smoke` sees all 6 sidebar links (Dashboard, Purchase Orders, Invoices, Vendors, Products, Users).
  - VENDOR at `/_smoke` has NO Vendors link (`toHaveCount(0)`).
  - Unauth at `/_smoke` (auth/me returns 401) redirects to `/login`.
- [ ] Run the spec — expect PASS. Run `make test-browser` — expect **147 passed** (144 + 3).
- [ ] Commit: `Add nexus-shell smoke test + sentinel route (iter 069 task 25)`.

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

Pending — filled at iter close.

### PM-delegate decisions

- **UserMenu mobile meta collapse**: mock shows pill without text on mobile; adding `@media (max-width: 767px) { .meta { display: none; } }`. Tested explicitly.
- **Dev role switcher** (Task 22): plan prescribes `import.meta.env.DEV` split. The actual role-store wiring (how a switched role propagates to `$app/state`'s `page.data.user`) is backlog'd for a dedicated dev-tools iteration. Phase 4.0 ships a visible placeholder menu item so the dropdown structure is in place; clicking does nothing yet.
- **Logout failure swallowed**: plan's pattern is `try { await logout(); } catch {} goto('/login');`. If the logout API call fails, the user is still redirected. Accept the plan.
- **`_smoke` route name**: underscore prefix marks it as an internal/test route. SvelteKit does not special-case leading underscores (unlike `_layout.svelte` in some frameworks); this is a convention only. The `(nexus)` layout group still wraps it.