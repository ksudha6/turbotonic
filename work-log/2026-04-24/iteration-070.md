# Iteration 070 -- Phase 4.0 close

## Context

Final iteration of Phase 4.0. Iter 069 closed with 26 primitives + `redirects.ts` + `(nexus)/_smoke` sentinel route, 148 Playwright passes, 591 backend passes. This iteration ships phase-close riders (Plan Task 26):

1. Run the full test suite. Expected: 591 backend + 148 Playwright green (no regression from iter 069 close).
2. axe AA accessibility scan on `/ui-demo` and `/_smoke`. Zero AA violations required. Fix violations inline; do not suppress.
3. Capture 390px + 1024px JPEG screenshots of every `/ui-demo` section and of `/_smoke` for visual verification.
4. Summarize Phase 4.0 in a phase-close document.
5. Commit.

Nothing new ships to `$lib/ui/`. This is verification + handoff. The branch `ux-changes` is ready for merge to `main` after phase close.

### Phase 4.0 summary (draft — finalized in Notes at close)

- **10 iterations**: iter 061 through iter 070.
- **26 primitives** under `frontend/src/lib/ui/`: Button, StatusPill, ProgressBar, Input, Select, DateInput, Toggle (leaves); FormField, PanelCard, AttributeList, FormCard, KpiCard (composites); Timeline, ActivityFeed, LoadingState, EmptyState, ErrorState, ErrorBoundary (display+state); DataTable, PageHeader, DetailHeader (table+headers); Sidebar, TopBar, AppShell, UserMenu (shell).
- **3 supporting modules**: `sidebar-items.ts`, `redirects.ts`, plus `(nexus)` layout group.
- **46 primitive-layer tests** across 4 specs: `primitives.spec.ts` (33), `sidebar-items.spec.ts` (7), `redirects.spec.ts` (3), `nexus-shell.spec.ts` (3). Plus 100 pre-revamp tests → **148 Playwright total**.
- **Design tokens**: 22 new CSS custom properties in `global.css` (surfaces, brand, dots, typography, breakpoints, spacing extensions).
- **All 3 brainstorm stops resolved** from Lovable mock screenshots via Playwright MCP: per-role sidebar items (iter 067 Task 18, user input), mobile drawer pattern (iter 068 Task 20, off-canvas Option A), UserMenu prod/dev split (iter 069 Task 22, `import.meta.env.DEV`).

Ship gates for 070:
- Mock-clarity: N/A (phase close, no new visual work).
- Past-flow: 591 backend + 148 Playwright at iter open. Must stay green.
- Future-flow: axe scan catches a11y regressions before iter 071+ aggregate pages start consuming primitives.

## JTBD (Jobs To Be Done)

- As the Phase 4.1 implementer starting on the redesigned Dashboard, when I open a redesigned page, I want every primitive it uses to pass AA accessibility checks already, so I am not debugging contrast or focus issues on top of feature work.
- As a reviewer auditing Phase 4.0 before the branch merges to main, I want one summary document listing what shipped and where the shell + primitives live, so I can spot-check without reading 10 iteration docs.
- As a future maintainer reading `work-log/iterations-summary.md`, I want Phase 4.0's foundation record to end with "closed on 2026-04-24" so the status is unambiguous.

## Tasks

### Task 26.1 -- Run full test suite

- [ ] `make test-browser` — expect 148 passed.
- [ ] `make test` (alias for `test-backend test-browser`) — expect 591 backend + 148 browser green.
- [ ] Record counts in Notes.

### Task 26.2 -- axe AA scan

- [ ] `cd frontend && npm install --save-dev @axe-core/playwright` (if not already installed).
- [ ] Append two tests to `primitives.spec.ts`:
  - `axe: /ui-demo has zero AA violations`
  - `axe: /_smoke has zero AA violations`
  Each uses `AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()`.
- [ ] Run the new tests. If violations appear, fix them inline (usually missing labels or color contrast). Do not add axe excludes or `disableRules` workarounds.
- [ ] Expected final count: **150 passed** (148 + 2 axe tests).
- [ ] Commit: `Add axe AA scan on /ui-demo and /_smoke (iter 070 task 26.2)`.

### Task 26.3 -- Screenshots at 390 and 1024

- [ ] Capture 390px + 1024px JPEG viewports of `/ui-demo` and `/_smoke` via a one-off Playwright script at `frontend/tests/scratch/iteration-070/capture.ts`.
- [ ] Save under `frontend/tests/scratch/iteration-070/screenshots/` — gitignored (scratch tests are disposable per CLAUDE.md). Do NOT commit the screenshots.
- [ ] Document the capture procedure in the iteration-070 Notes so a reviewer can reproduce.

### Task 26.4 -- Phase close write-up

- [ ] Update `work-log/iterations-summary.md` header to "Last updated: iter 070 closed on 2026-04-24 — **Phase 4.0 complete**".
- [ ] Append iter 070 row to the iteration log table.
- [ ] Append a "Phase 4.0 completion" block to the "What exists and works" section summarizing the 26 primitives.

### Task 26.5 -- Commit phase-close artifacts

- [ ] Commit the axe tests + iteration doc + iterations-summary update.
- [ ] Do NOT commit scratch screenshots.
- [ ] Push to `origin/ux-changes` — branch is ready for PR → main.

## Existing test impact

- `primitives.spec.ts` grows by 2 axe tests. No existing tests modified.
- `frontend/package.json` + `frontend/package-lock.json` gain `@axe-core/playwright` dev dependency.
- Pre-revamp tests: untouched.

## Tests

### Permanent tests added
- 2 axe A11y tests on `/ui-demo` and `/_smoke`.

Expected `make test-browser` at close: **150 passed**.

### Scratch tests
- `frontend/tests/scratch/iteration-070/capture.ts` — screenshot script. Not committed.

### Logs
- `logs/playwright-test-browser.log` — expect 150 passed.
- `logs/pytest.log` — expect 591 passed.

## Notes

Pending — filled at iter close.