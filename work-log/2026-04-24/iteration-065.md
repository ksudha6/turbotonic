# Iteration 065 -- Display + state primitives: Timeline, ActivityFeed, LoadingState, EmptyState, ErrorState, ErrorBoundary

## Context

Fifth iteration of Phase 4.0. Iter 064 closed with 12 primitives live under `frontend/src/lib/ui/` (7 leaves + 5 composites). This iteration ships six more (Plan Tasks 12-13):

- **Task 12** -- `Timeline` (ordered steps with done/current/upcoming state), `ActivityFeed` (dot + primary + secondary entry rows).
- **Task 13** -- `LoadingState` (aria-live spinner), `EmptyState` (title + description + optional action), `ErrorState` (alert message + optional retry button wrapping iter-063 Button), `ErrorBoundary` (Svelte 5 `<svelte:boundary>` wrapping ErrorState).

`/ui-demo` gets two more sections. `primitives.spec.ts` gains 5 tests (Timeline step count, ActivityFeed text, LoadingState role, EmptyState text, ErrorState text + retry). ErrorBoundary is installed but not unit-tested — it's exercised indirectly once iter 068 wires it into AppShell.

Brainstorm-stop assessment: the "state primitives" brainstorm marker is discharged here. The Lovable mock is silent on loading/empty/error visual treatments in most flows. The plan's defaults (centered spinner, centered title+description empty, #fef2f2 bg alert banner with red-700 text) are reasonable and follow common patterns. No user-facing brainstorm is triggered. One small addition beyond the plan: `prefers-reduced-motion` fallback for the spinner — basic accessibility for motion-sensitive users, cheap and non-negotiable.

Ship gates for 065:
- Mock-clarity: state primitive visuals follow industry defaults; mock silent. No stop.
- Past-flow: 591 backend + 114 browser at iter open. Must stay green.
- Future-flow: all primitives additive under `$lib/ui/`; no iter-063 or iter-064 primitive modified.

## JTBD (Jobs To Be Done)

- As a developer wiring the dashboard's production pipeline in iter 071+, when I need to show an ordered set of milestone steps with done/current/upcoming state, I want `Timeline` to do it from a `steps` array.
- As a developer wiring the dashboard's activity feed in iter 071+, when I need to render a vertical list of events with a colored dot + primary text + relative-time secondary, I want `ActivityFeed` from an `entries` array.
- As a developer wiring any list or detail page, when I need to show the page loading, or the empty state, or the error state, I want `LoadingState` / `EmptyState` / `ErrorState` as drop-in primitives so each surface looks the same.
- As an ADMIN or VENDOR experiencing a runtime render error in the redesigned app, when the page's child component throws, I want the `ErrorBoundary` to catch it and show a retry UI rather than a blank page.
- As a user with reduced-motion enabled in their OS, when a page is loading, I want the spinner to not rotate, so I do not get motion-sick.

## Tasks

### Task 12 -- `Timeline` and `ActivityFeed`

- [ ] Append `Timeline` and `ActivityFeed` tests to `primitives.spec.ts` (2 tests: Timeline has 3 `<li>` steps, ActivityFeed contains `'PO accepted'` and `'2m ago'`). Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/Timeline.svelte` per plan Task 12 Step 2 with class rename `.timeline` → `ui-timeline`. Inner `.marker` / `.content` / `.label` / `.detail` scoped as-is.
- [ ] Create `frontend/src/lib/ui/ActivityFeed.svelte` per plan Task 12 Step 3 with class rename `.feed` → `ui-feed`. Inner `.dot` scoped as-is (no cross-primitive collision despite StatusPill also using `.dot`; Svelte hashes them separately).
- [ ] Extend `/ui-demo` with Timeline and ActivityFeed sections.
- [ ] Run — expect PASS. Run `make test-browser` — expect **116 passed** (114 + 2).
- [ ] Commit: `Add Timeline + ActivityFeed primitives (iter 065 task 12)`.

### Task 13 -- `LoadingState`, `EmptyState`, `ErrorState`, `ErrorBoundary`

Four state primitives. Three tested, one (ErrorBoundary) installed without a unit test.

- [ ] Append three state tests to `primitives.spec.ts`:
  - `LoadingState renders a spinner labelled for assistive tech` (asserts role=status).
  - `EmptyState renders title + description` (contains "No results" + "Try adjusting").
  - `ErrorState shows message and a Retry button` (contains "Something broke" + retry button visible).
  Run — expect 3 FAIL.
- [ ] Create `frontend/src/lib/ui/LoadingState.svelte` per plan Task 13 Step 2 with class rename `.wrap` → `ui-loading`. Adds a `@media (prefers-reduced-motion: reduce) { .spinner { animation: none; } }` clause so users with reduced-motion preference see a static ring.
- [ ] Create `frontend/src/lib/ui/EmptyState.svelte` per plan Task 13 Step 3 with class rename `.empty` → `ui-empty`.
- [ ] Create `frontend/src/lib/ui/ErrorState.svelte` per plan Task 13 Step 4 with class rename `.error` → `ui-error`. Wraps the iter-063 Button primitive as the Retry button; retry testid is `{testid}-retry`.
- [ ] Create `frontend/src/lib/ui/ErrorBoundary.svelte` per plan Task 13 Step 5 (no outermost class; `<svelte:boundary>` wraps children and falls back to ErrorState with `message='Something went wrong. Please refresh or try again.'`). Not used on `/ui-demo` (no throwable children in the gallery); will be installed into `(nexus)/+layout.svelte` in iter 068.
- [ ] Extend `/ui-demo` with a `State primitives` section showing LoadingState, EmptyState, and ErrorState (ErrorBoundary is not rendered on the gallery).
- [ ] Run — expect PASS. Run `make test-browser` — expect **119 passed** (116 + 3).
- [ ] Commit: `Add LoadingState, EmptyState, ErrorState, ErrorBoundary (iter 065 task 13)`.

## Existing test impact

Pre-iteration audit:
- `frontend/tests/primitives.spec.ts` — extended by 5 new tests (Timeline, ActivityFeed, LoadingState, EmptyState, ErrorState). No existing tests modified.
- No pre-revamp spec touches `$lib/ui/`. 
- The existing `/ui-demo` page has 8 sections at iter 065 open; we add 2 more (Timeline+ActivityFeed section, State primitives section) to reach 10.
- `ErrorBoundary` is created but not rendered on `/ui-demo`, and not imported anywhere yet. No behavior change until iter 068 installs it.

No fixtures, mocks, or helpers need updating.

## Tests

### Permanent tests added this iteration
- `frontend/tests/primitives.spec.ts` extended to **19 tests total**:
  - Button: 3, StatusPill: 1, ProgressBar: 1, Form controls: 4, FormField: 1, Panel primitives: 3, KpiCard: 1 (total 14 — from iter 063-064).
  - Timeline: 1, ActivityFeed: 1, LoadingState: 1, EmptyState: 1, ErrorState: 1 (total 5 — new this iter).

Expected `make test-browser` count at close: **119 passed**.

ErrorBoundary is installed without a dedicated test. Testing it requires a throwable child component, which is out of scope for an iteration focused on primitive shape. The primitive's correctness is verified when iter 068 wires it into `AppShell` and tests simulate a render error.

### Scratch tests
None. Visual verification via `/ui-demo` on the dev server suffices. Scratch screenshots deferred to iter 070.

### Logs
- `logs/playwright-test-browser.log` — `make test-browser` at iteration close, expect 119 passed.
- `logs/pytest.log` — iteration-open and iteration-close snapshots (expect 591 passed; no backend change).

## Notes

Pending — filled at iteration close.

### PM-delegate decisions (autonomous mode)

- **Reduced-motion fallback on LoadingState spinner.** Plan's spinner rotates via `@keyframes spin`; users with OS-level reduced-motion preference would still see rotation. Adding `@media (prefers-reduced-motion: reduce) { .spinner { animation: none; } }` is a ~3-line change that prevents motion sickness. Not a brainstorm-worthy decision — motion accessibility is a baseline, not a visual choice.
- **No brainstorm stop on state primitives.** Visual defaults for Loading / Empty / Error are industry-standard (centered spinner, centered copy, alert banner). Mock silent; plan's defaults ship.
- **ErrorBoundary not unit-tested.** Testing `<svelte:boundary>` requires a throwable child. Installation into AppShell in iter 068 will exercise it end-to-end. No primitive-level test.