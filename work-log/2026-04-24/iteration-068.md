# Iteration 068 -- TopBar + AppShell + mock-aligned chrome retrofits

## Context

Eighth iteration of Phase 4.0. Iter 067 closed with 22 primitives + `sidebar-items.ts`, 130 Playwright passes, 591 backend passes. User obtained mobile + tablet + desktop screenshots of the Lovable mock (`https://turbotonic.lovable.app`). All three remaining Phase 4.0 brainstorms resolved from mock evidence:

1. **Mobile drawer**: off-canvas from left (~70% viewport), dark overlay on remaining ~30%, tap overlay to dismiss. Plan Task 20 Option A.
2. **UserMenu**: pill shows `[avatar] [humanized role] [▾]` on desktop, collapses to `[avatar] [▾]` on mobile. Plan Task 22 dev/prod split via `import.meta.env.DEV`.
3. **TopBar search**: live on ≥768px, hidden on mobile. For Phase 4.0 ships **hidden everywhere** (not disabled). Live-search backend is a backlog item.

User confirmed scope: Option B (mock chrome + our real routes). That means retrofitting three earlier primitives to match mock chrome structure before building TopBar + AppShell.

Scope: Plan Tasks 19-21 plus three prerequisite retrofits.

### Prerequisite retrofits (iter 068 prep)

- **`sidebar-items.ts`** — current shape `Array<SidebarItem>`. Mock groups items into sections (`WORKSPACE` / future `ACCOUNT`). New shape: `Array<{ label: string; items: SidebarItem[] }>`. Backward-compatible update to consumers.
- **`Sidebar.svelte`** — render section headers, accept optional `footer` snippet, accept optional `roleLabel` prop for humanized role display (falls back to role code). Keep existing brand block.
- **`KpiCard.svelte`** — add optional `icon` snippet slot, rendered top-right of the card chrome.

### Main tasks (Plan 19-21)

- **Task 19 `TopBar`** — responsive: `[☰] [breadcrumb] [search] [🔔] [UserMenu pill]` at ≥768px, `[☰] [spacer] [🔔] [UserMenu pill]` at <768px. Search hidden via CSS media query for Phase 4.0.
- **Task 21 `AppShell`** — composes Sidebar + TopBar + ErrorBoundary-wrapped `<main>`. Mobile: sidebar becomes an off-canvas drawer with overlay.
- Task 20 brainstorm resolved pre-dispatch (see above).

Ship gates for 068:
- Mock-clarity: all three brainstorms resolved from mock screenshots. No pause.
- Past-flow: 591 backend + 130 browser at iter open. Must stay green.
- Future-flow: retrofits to Sidebar / sidebar-items / KpiCard must not break iter 067 Sidebar test, iter 067 sidebar-items spec, or iter 064 KpiCard test.

## JTBD (Jobs To Be Done)

- As a developer wiring the redesigned dashboard in iter 071+, when I drop a Sidebar into AppShell, I want it to show a humanized role label ("Supply Manager") rather than the bare role code ("SM"), and support section headers + a footer slot, so the revamped shell matches the Lovable visual language.
- As an ADMIN using the portal on my phone, when I want to navigate, I want to tap a hamburger icon in the top bar and see the sidebar slide in from the left, with a dimmed overlay I can tap to dismiss.
- As a developer on any redesigned page, when I want to show a stat card with an icon, I want to pass an `icon` snippet to KpiCard and have it render top-right.
- As a keyboard user, when I open the mobile drawer, I want focus to move to the sidebar so Tab navigates through items. When I close it, focus returns to the hamburger button.
- As a developer wiring `<TopBar>` into the shell, I want the search input to not render at all on mobile so there is no UX confusion about disabled inputs.

## Tasks

### Task 19-prep-A -- `sidebar-items.ts` returns sections

- [ ] Append failing-first test to `sidebar-items.spec.ts` asserting the new shape: `sidebarItemsFor('ADMIN')[0]` has `label: 'Workspace'` and `items: SidebarItem[]`. Run — expect FAIL.
- [ ] Rewrite `sidebar-items.ts`:
  - New types: `SidebarSection = { label: string; items: SidebarItem[] }`.
  - `sidebarItemsFor(role: UserRole): SidebarSection[]` returns a single-section array `[{ label: 'Workspace', items: [...] }]` for every role.
  - The inner item list is unchanged per role.
- [ ] Update existing tests to assert the flattened item labels via `.flatMap((s) => s.items)`.
- [ ] Run `sidebar-items.spec.ts` — all pass.
- [ ] Commit: `Group sidebar-items into sections (iter 068 prep A)`.

### Task 19-prep-B -- `Sidebar.svelte` renders sections + footer slot + roleLabel

- [ ] Update `primitives.spec.ts` Sidebar tests to remain passing (no test change needed; the new shape of the consumer's `items` is internal).
- [ ] Add a new test: `Sidebar renders section header "WORKSPACE"`. Run — expect FAIL before rewrite.
- [ ] Add a new test: `Sidebar renders footer snippet when provided`.
- [ ] Add a new test: `Sidebar shows humanized role label when provided`.
- [ ] Rewrite `Sidebar.svelte`:
  - Accept `roleLabel?: string` prop (default: role code in brand block, as before).
  - Iterate `sections` from `sidebarItemsFor(role)` and render each section's header (small uppercase gray) + items under it.
  - Accept `footer?: Snippet` prop and render at bottom of aside.
- [ ] Update `/ui-demo` Sidebar section to pass `roleLabel="Supply Manager"` and a small footer snippet (e.g. "Demo workspace").
- [ ] Run `make test-browser` — expect **133 passed** (130 + 3 new Sidebar tests).
- [ ] Commit: `Retrofit Sidebar with sections + footer + roleLabel (iter 068 prep B)`.

### Task 19-prep-C -- `KpiCard.svelte` icon slot

- [ ] Add a new test: `KpiCard renders icon slot when provided` — assert testid `ui-kpi-icon` visible. Run — expect FAIL.
- [ ] Update `KpiCard.svelte` to accept optional `icon?: Snippet` and render inside a `.icon` slot top-right using grid layout.
- [ ] Update `/ui-demo` KpiCard demo to pass an icon snippet (e.g. inline SVG or emoji).
- [ ] Run `make test-browser` — expect **134 passed**.
- [ ] Commit: `Add icon slot to KpiCard (iter 068 prep C)`.

### Task 19 -- `TopBar` primitive

- [ ] Verify `frontend/src/lib/components/NotificationBell.svelte` renders `data-testid="notification-bell-button"` on the button element. If missing, add it (one-line additive change).
- [ ] Append `TopBar primitive` test to `primitives.spec.ts`:
  - At ≥768px viewport: breadcrumb visible, search visible, bell visible, user pill slot visible.
  - At 390px viewport: breadcrumb hidden, search hidden, bell visible, user pill slot visible.
  Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/TopBar.svelte` (class `ui-topbar`):
  - Props: `breadcrumb?: string`, `userMenu?: Snippet`, `onToggleSidebar?: () => void`, `data-testid`.
  - Renders hamburger button only when `onToggleSidebar` is set.
  - Embeds the pre-revamp `NotificationBell` (import path `$lib/components/NotificationBell.svelte`).
  - Scoped CSS: `.breadcrumb`, `.search` both have `display: none` at `max-width: 767px`; visible at `min-width: 768px`.
  - Search input: NOT rendered at all in Phase 4.0 (not even disabled). The media-query hide pattern is scaffold-only. Use a TODO comment.
- [ ] Extend `/ui-demo` with a TopBar section at ≥768px showing the full bar.
- [ ] Run — expect PASS. Run `make test-browser` — expect **135 passed** (134 + 1 new responsive test counts as 1; may add a second for the mobile-viewport assertion).
- [ ] Commit: `Add TopBar primitive embedding NotificationBell (iter 068 task 19)`.

Actually: because Playwright viewport is per-test, the two responsive assertions become two tests (desktop + mobile). Adjust count to **136 passed** (134 + 2).

### Task 20 -- BRAINSTORM STOP (pre-resolved)

- [x] Resolution: off-canvas drawer from left, dark overlay, tap-overlay-to-dismiss. Matches mock 390px drawer-open screenshot. No user pause required; mock evidence sufficient.

### Task 21 -- `AppShell` composition

- [ ] Create `frontend/src/routes/ui-demo/shell/+page.svelte` as a separate test route (AppShell wraps children; we don't wrap `/ui-demo` itself because it would affect existing primitive tests).
- [ ] Append AppShell tests to `primitives.spec.ts`:
  - Desktop: sidebar + topbar + main all visible.
  - Mobile 390px: sidebar hidden by default; tap toggle reveals it; tap overlay dismisses.
  Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/AppShell.svelte`:
  - Class `ui-appshell`.
  - Composes Sidebar, TopBar, ErrorBoundary around main content.
  - State: `sidebarOpen = $state(false)`.
  - Props: `role`, `roleLabel`, `breadcrumb`, `userMenu`, `sidebarFooter`, `children`, `data-testid`.
  - Desktop (≥769px): two-column grid, sidebar visible; `sidebarOpen` ignored.
  - Mobile (≤768px): sidebar absolutely positioned, `translateX(-100%)` by default, `translateX(0)` when `sidebarOpen`. Overlay element rendered when `sidebarOpen`, full-viewport dim, clicking it toggles off.
- [ ] Run — expect PASS. Run `make test-browser` — expect **138 passed** (136 + 2 AppShell tests).
- [ ] Commit: `Add AppShell with off-canvas mobile drawer (iter 068 task 21)`.

## Existing test impact

- Existing `sidebar-items.spec.ts` (6 tests): must be updated to use `.flatMap((s) => s.items)` because the function's return shape changes. Every label assertion remains valid against the flattened list.
- Existing `primitives.spec.ts` Sidebar tests (2 tests): unaffected — the Sidebar primitive still renders `<a>` elements for each item; the internal grouping is transparent to the consumer's `getByRole('link')` queries.
- Existing `primitives.spec.ts` KpiCard test (1): unaffected. `toContainText('+12%')` and `toContainText('$24,300')` still match; the icon is additive.
- Pre-revamp layout, pre-revamp specs: untouched. The retrofits are additive to `$lib/ui/` primitives that pre-revamp pages do not import.

No fixtures, mocks, or helpers need updating.

## Tests

### Permanent tests at iter close
- `sidebar-items.spec.ts`: 6 tests, all updated to the sections shape (unchanged count).
- `primitives.spec.ts`: **24 (existing) + 3 (new Sidebar sections/footer/roleLabel) + 1 (KpiCard icon) + 2 (TopBar responsive) + 2 (AppShell desktop/mobile) = 32 tests** inside this file.
- Total `make test-browser` at iter close: **138 passed** (591 backend + 138 browser).

### Scratch tests
None.

### Logs
- `logs/playwright-test-browser.log` — expect 138 passed.
- `logs/pytest.log` — expect 591 passed.

## Notes

Iter 068 closed on 2026-04-24. Five commits landed on `ux-changes`:
- Open doc (committed earlier).
- `5cab303` Prep A: Sidebar retrofit with sections + footer + roleLabel; sidebar-items returns `SidebarSection[]`.
- `cb7e137` Prep B: KpiCard icon slot.
- `081f620` Task 19: TopBar primitive (responsive hide of breadcrumb on mobile; search deferred).
- `d25190b` Task 21: AppShell with off-canvas mobile drawer + separate `/ui-demo/shell` route.

130 Playwright passes at open → 134 after prep A → 135 after prep B → 137 after Task 19 → 140 at close. Backend stays 591.

### Decisions resolved from Lovable mock evidence

All three Phase 4.0 brainstorms resolved by capturing `https://turbotonic.lovable.app` at 1440 / 390 / 390-drawer-open viewports via Playwright MCP:

- **Mobile drawer (Brainstorm 1 / plan Task 20)**: off-canvas from left, width `min(280px, 70vw)`, `translateX(-100%)` + `visibility: hidden` by default, transitions to `translateX(0)` when open. Overlay is a 35% opacity fixed-position button covering the viewport; tap to dismiss.
- **UserMenu layout (Brainstorm 2 / plan Task 22)**: confirmed `[avatar][humanized role][▾]` on desktop, collapses to `[avatar][▾]` on mobile. Implementation in iter 069.
- **TopBar search (Brainstorm 3)**: hidden on mobile, omitted from TopBar entirely in Phase 4.0 (no live-search backend). When added in backlog phase, TopBar will gain a `search?: Snippet` slot.

### Chrome alignment scope — Option B

User confirmed "production grade" + provided the Lovable mock URL. Locked on Option B: mock visual chrome + our real data-model routes.

Retrofits shipped to existing primitives:
- `sidebar-items.ts`: returns `SidebarSection[]` instead of `SidebarItem[]`. Single `Workspace` section for now; future Settings/Help would land in a second `Account` section.
- `Sidebar.svelte`: renders section headers (uppercase, `letter-spacing-wide`, `text-sidebar-muted`), accepts `roleLabel?: string` prop for humanized role display, accepts `footer?: Snippet` slot.
- `KpiCard.svelte`: gains `icon?: Snippet` slot rendered top-right via a `.header` flex row.

None of these retrofits break existing primitive tests — all consumers that don't pass the new props keep working.

### AppShell design

- Desktop (≥769px): CSS grid `240px 1fr`, sidebar is permanent.
- Mobile (≤768px): grid collapses to `1fr`, sidebar-wrap becomes fixed-position off-canvas with transition + visibility toggle.
- State: `sidebarOpen = $state(false)` local to AppShell.
- ErrorBoundary wraps `<main>` so iter-071+ aggregate pages get automatic error handling.
- `/ui-demo/shell` is a separate dev-only route for testing AppShell in isolation; the original `/ui-demo` stays unwrapped so primitive tests don't run through a shell.

### DDD vocab assessment

No new domain terms. `docs/ddd-vocab.md` unchanged.

### Backlog captured

- **Live TopBar search**: hook up to a future search-API backend. Mock shows it working at ≥768px. When implemented, TopBar gains a `search?: Snippet` slot with responsive hiding on mobile.
- **UserMenu**: iter 069 Task 23 implements. Desktop `[avatar][Supply Manager][▾]`, mobile `[avatar][▾]`.
- **Focus trap in mobile drawer**: currently the drawer opens but Tab doesn't trap focus inside it. Add in a hardening iteration (out of Phase 4.0 scope; listed in ship gates as a11y rider).
- **Escape key closes drawer**: not yet wired. Add in the same hardening pass.
- **`Account` section in sidebar**: Settings/Help routes don't exist. When they do, add a second section to `sidebar-items.ts`.
- **Users page `/users`**: link exists in sidebar for ADMIN; 404s until the page is built (iter 070+ or feature-backlog phase).
- **Prefers-reduced-motion on drawer transition**: drawer transitions via `transform` at 0.2s. Users with reduced-motion preference should get instant open/close.

### What exists after iter 068

Twenty-five primitives under `frontend/src/lib/ui/`:
- Leaves (iter 063, 7): Button, StatusPill, ProgressBar, Input, Select, DateInput, Toggle.
- Composites (iter 064, 5): FormField, PanelCard, AttributeList, FormCard, KpiCard (with icon slot from iter 068).
- Display + state (iter 065, 6): Timeline, ActivityFeed, LoadingState, EmptyState, ErrorState, ErrorBoundary.
- Table + headers (iter 066, 3): DataTable, PageHeader, DetailHeader.
- Shell (iter 067-068, 4): Sidebar (with sections + footer + roleLabel), TopBar, AppShell + `sidebar-items.ts`.

Plus one new route: `/ui-demo/shell` showing AppShell in isolation with a Shell demo content block.

`primitives.spec.ts`: 31 tests. `sidebar-items.spec.ts`: 7 tests (6 role matrix + 1 shape). `/ui-demo`: 14 sections + TopBar section = 15.

Carried forward: none. Task 20 pre-resolved from mock. Task 22 resolved ahead of iter 069.

### PM-delegate decisions (all resolved from mock evidence)

- **Mobile drawer**: Option A (off-canvas + overlay). Mock screenshot at 390px with drawer open shows ~70%-width drawer, dark overlay on right ~30%. Matches the plan default.
- **UserMenu prod/dev**: split via `import.meta.env.DEV`. Mock shows `[avatar][Supply Manager][▾]` on desktop, `[avatar][▾]` on mobile. Humanized role label sourced from a role → label map (implemented inside Sidebar + UserMenu as a small const).
- **TopBar search**: hide on mobile (mock shows it missing); Phase 4.0 ships it hidden everywhere since no live-search backend exists yet. Enable in backlog phase alongside search implementation.
- **Chrome scope**: Option B (mock visual chrome + our real routes). Section headers, footer slot, humanized role label, KpiCard icon slot all added to existing primitives before building TopBar/AppShell.