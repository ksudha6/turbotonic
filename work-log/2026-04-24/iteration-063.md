# Iteration 063 -- Leaf primitives: Button, StatusPill, ProgressBar, Input, Select, DateInput, Toggle

## Context

Third iteration of Phase 4.0. Iter 062 shipped design tokens, the `(nexus)` route-group scaffold, and a bare `/ui-demo` skeleton. This iteration populates `/ui-demo` with the first seven leaf primitives and introduces the permanent Playwright spec (`frontend/tests/primitives.spec.ts`) that every subsequent primitive iteration extends.

Scope: Plan Tasks 5 through 8.

- Task 5 -- `Button` (primary | secondary | ghost, disabled state, focus ring)
- Task 6 -- `StatusPill` (five tones: green | blue | orange | red | gray, scoped — coexists with pre-revamp `$lib/components/StatusPill.svelte`)
- Task 7 -- `ProgressBar` (value 0-100, ARIA progressbar role)
- Task 8 -- `Input`, `Select`, `DateInput`, `Toggle` bundled (four small leaf form controls)

All primitives live under `frontend/src/lib/ui/`. Pre-revamp components under `$lib/components/` are untouched. Style rules inside each primitive's `<style>` are Svelte-scoped (no leaks to pre-revamp pages).

Ship gates for 063:
- Mock-clarity: Button (primary, secondary, ghost) and the five StatusPill tones are locked in the design spec from the Lovable mock. Form controls follow native chrome (cheapest default). `DateInput` uses native `<input type="date">` — user confirmed. **No brainstorm stop needed.**
- Past-flow: 591 backend + 100 browser green before iteration opens (verified 2026-04-24 after dev-server restart). Must stay green at close. Pre-revamp pages must render identically.
- Future-flow: primitives are additive; `primitives.spec.ts` is the new permanent home for primitive regression.

## JTBD (Jobs To Be Done)

- As a developer building a composite primitive in iter 064+, when I need a button, status pill, progress bar, or form input, I want to `import` the primitive from `$lib/ui/`, so I do not have to re-invent keyboard handling, focus styling, or tone variants.
- As a reviewer auditing Phase 4.0, when I visit `/ui-demo`, I want to see every primitive shipped so far in one place, so I can visually verify the design system without opening individual files.
- As a Playwright author, when I need a stable element to assert against, I want every primitive to render with `data-testid="ui-<component>-<variant>"`, so my spec stays selector-stable across refactors.
- As an ADMIN or VENDOR interacting with future redesigned pages, when I focus an interactive element with the keyboard, I want a visible focus ring using the brand accent, so keyboard users are not blocked.

## Tasks

### Task 5 -- `Button` primitive
- [ ] Create `frontend/tests/primitives.spec.ts` with `Button primitive` describe block: primary focusable, secondary and ghost render, disabled is disabled. Run `cd frontend && npx playwright test primitives.spec.ts --reporter=list` — expect FAIL (route does not exist yet).
- [ ] Create `frontend/src/lib/ui/Button.svelte` per plan Task 5 Step 2 (variant: primary | secondary | ghost, disabled, onclick, children, data-testid; scoped styles using --button-solid-bg / --button-solid-fg / --surface-card / --gray-* / --brand-accent tokens).
- [ ] Replace `frontend/src/routes/ui-demo/+page.svelte` with the Button section (four buttons: primary, secondary, ghost, disabled).
- [ ] Re-run `cd frontend && npx playwright test primitives.spec.ts --reporter=list` — expect PASS.
- [ ] Run `make test-browser` — expect 100 → 103 passed (three new Button tests added to permanent suite).
- [ ] Commit: `Add Button primitive + ui-demo Button section (iter 063 task 5)`.

### Task 6 -- `StatusPill` primitive
- [ ] Append `StatusPill primitive` describe block to `primitives.spec.ts` (renders five tone variants with leading dot). Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/StatusPill.svelte` per plan Task 6 Step 2 (tone: green | blue | orange | red | gray, dot + label, scoped styles using --dot-* tokens and inline tone backgrounds).
- [ ] Extend `/ui-demo` with a `StatusPill` section showing all five tones.
- [ ] Run the new describe — expect PASS. Run `make test-browser` — expect 104 passed.
- [ ] Commit: `Add StatusPill primitive (iter 063 task 6)`.

### Task 7 -- `ProgressBar` primitive
- [ ] Append `ProgressBar primitive` describe block to `primitives.spec.ts` (renders progressbar role with `aria-valuenow=60`). Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/ProgressBar.svelte` per plan Task 7 Step 2 (value 0-100, clamped with `$derived`, optional label, role=progressbar + aria-valuenow/min/max, scoped styles).
- [ ] Extend `/ui-demo` with a `ProgressBar` section at value 60.
- [ ] Run — expect PASS. Run `make test-browser` — expect 105 passed.
- [ ] Commit: `Add ProgressBar primitive (iter 063 task 7)`.

### Task 8 -- `Input`, `Select`, `DateInput`, `Toggle` primitives (bundled)
- [ ] Append `Form control primitives` describe block with four tests (Input fills, Select selects, DateInput renders, Toggle toggles aria-pressed). Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/Input.svelte` per plan Task 8 Step 2 (value bindable, type, placeholder, disabled, invalid, data-testid).
- [ ] Create `frontend/src/lib/ui/Select.svelte` per plan Task 8 Step 3 (options array of {value,label}, bindable value, disabled, invalid).
- [ ] Create `frontend/src/lib/ui/DateInput.svelte` per plan Task 8 Step 4 (native `<input type="date">`, bindable value).
- [ ] Create `frontend/src/lib/ui/Toggle.svelte` per plan Task 8 Step 5 (aria role=switch, bindable pressed, knob slide).
- [ ] Extend `/ui-demo` with a `Form controls` section showing all four.
- [ ] Run — expect PASS. Run `make test-browser` — expect 109 passed.
- [ ] Commit: `Add Input/Select/DateInput/Toggle primitives (iter 063 task 8)`.

## Existing test impact

Pre-iteration audit:
- `frontend/tests/primitives.spec.ts` is NEW this iteration. Created in Task 5; extended across Tasks 6-8. It's the permanent home for primitive regression going forward.
- `/ui-demo` currently renders only `<h1>Phase 4.0 UI Demo</h1>`. No existing test visits `/ui-demo`. This iteration's `primitives.spec.ts` is the first.
- No pre-revamp spec depends on `$lib/ui/` — the namespace is new. All primitives scope their styles locally, so no risk of leakage into `.btn` / `.table` / `.badge` / `.card` / `.input` global rules consumed by pre-revamp pages.
- Pre-revamp `$lib/components/StatusPill.svelte` (the existing status pill used by po-list, po-detail, invoice-list) is untouched. The new `$lib/ui/StatusPill.svelte` is a separate module; same filename, different path.

If any pre-revamp spec breaks from this iteration, the likely causes are:
- Accidental edit to `global.css` (none planned; additive in iter 062 only). 
- Accidental edit to `$lib/components/StatusPill.svelte` (must not happen; plan creates `$lib/ui/StatusPill.svelte`).
- Port mismatch: the plan's Task 5 Step 6 capture script uses port 5173; Makefile uses 5174. If scratch screenshots are captured, use 5174.

No fixtures, mocks, or helpers need updating.

## Tests

### Permanent tests added this iteration
- `frontend/tests/primitives.spec.ts` with four describe blocks covering Button (3 tests), StatusPill (1 test asserting five tone testids), ProgressBar (1 test asserting role+aria), and Form controls (4 tests — Input, Select, DateInput, Toggle). Total 9 new tests. Expected suite count at close: **109 passed**.

All tests visit `/ui-demo` with mocked `/api/v1/auth/me` returning an ADMIN user and a catch-all `/api/v1/**` returning `[]`. This keeps primitives tests isolated from real backend state.

### Scratch tests
Plan Task 5 Step 6 requests 390px + 1024px JPEGs of `/ui-demo` at `frontend/tests/scratch/iteration-063/screenshots/`. Rename the iteration folder from the plan's `iteration-4-0-5` to `iteration-063` to match CLAUDE.md iteration numbering. Use port **5174**, not 5173.

### Logs
- `logs/playwright-test-browser.log` — `make test-browser` at iteration close, expect 109 passed.
- `logs/pytest.log` — iteration-open and iteration-close snapshots (expect 591 passed both times; no backend change in this iteration).

## Notes

Iter 063 closed on 2026-04-24. Seven commits landed on `ux-changes`:
- `40aa0fb` Task 5 Button primitive + `/ui-demo` Button section + new `primitives.spec.ts` (3 tests).
- `56ed31f` Task 5 review fix: rename DOM class `btn` → `ui-btn` (pre-revamp `global.css` `.btn:hover { opacity: 0.85 }` was leaking onto secondary/ghost variants), fix misleading test title, strengthen the secondary/ghost visibility test with `toHaveClass` assertions.
- `14ed9c9` Task 6 StatusPill primitive (five tone variants with leading dot).
- `66241b2` Task 6 review fix: strengthen StatusPill test with `toHaveClass(<tone>)` + `.dot` attached.
- `488c1a3` Task 7 ProgressBar primitive (role=progressbar, aria-valuenow clamped via `$derived`).
- `4e9f045` Task 8 form controls bundle: Input, Select, DateInput (native), Toggle (button+aria-pressed pattern).

Full suite green at iter open (591 backend + 100 browser) and iter close (591 backend + 109 browser — 9 new primitive tests).

### Decisions

- **`ui-<name>` class convention established.** Every `$lib/ui/` primitive's outermost DOM class is `ui-btn` / `ui-pill` / `ui-progress` / `ui-input` / `ui-select` / `ui-date` / `ui-toggle`. This prevents collision with pre-revamp global rules (`.btn`, `.badge`, `.input`, `.select`, `.card`, `.table`, `.form-group`, `.container`). The Button task exposed the risk when the pre-revamp `.btn:hover` leaked onto scoped-but-unrenamed Button variants; the convention was enforced retroactively for Task 5 and proactively for Tasks 6-8. This deviates from the plan's literal class names in every primitive but preserves the plan's intent (scoped styling, token-driven).
- **Playwright mock order.** The plan's failing-first helpers called `mockUser` before `mockApiCatchAll`, but Playwright route handlers dispatch LIFO. The catch-all matched `/api/v1/auth/me` and the root layout redirected to `/login`, breaking every primitive test. Corrected order (`mockApiCatchAll` first, then `mockUser`) applied consistently across all 9 tests.
- **Toggle ARIA.** The plan applied `role="switch"` AND `aria-pressed={pressed}` on the same element. These conflict per ARIA (switch uses `aria-checked`). Shipped `<button type="button" aria-pressed>` without `role="switch"` — a valid toggle-button pattern that matches the test assertion.
- **Button ghost variant kept.** Earlier PM-delegate consideration was to defer ghost until a real consumer needed it. After reading Plan Task 5, ghost is explicitly in the plan with its own scoped styling; shipped as-is.
- **DateInput native.** `<input type="date">` wrapped in the token-driven border/padding. No custom calendar, no library.

### DDD vocab assessment

No new domain terms emerged. The primitives are UI design-system vocabulary (Button, StatusPill, ProgressBar, Input, Select, DateInput, Toggle), not business domain terms. `docs/ddd-vocab.md` unchanged.

### Backlog captured from code reviews

- **StatusPill hex-to-token refactor.** Five tone rules use raw hex values that exactly match existing `--<color>-100` / `--<color>-800` tokens in `global.css`. Mechanical refactor deferred to a later iter to avoid mid-iteration drift. The pre-revamp `$lib/components/StatusPill.svelte` already uses tokens; this refactor brings the new primitive to the same hygiene level.
- **Tone vocabulary reconciliation.** `--amber-*` tokens vs `.orange` tone class on StatusPill. One or the other should be renamed so consumers read a consistent color family. Deferred.
- **ProgressBar clamp edge cases.** Primitive clamps `value` via `$derived(Math.max(0, Math.min(100, value)))` but the test only exercises `value=60`. Add tests for `value=-10` (expect `aria-valuenow='0'`) and `value=150` (expect `aria-valuenow='100'`) when a consumer surfaces the need. Deferred.
- **Scratch screenshots (Plan Task 5 Step 6).** 390px + 1024px JPEGs of `/ui-demo`. Optional visual-verification artifact; did not run this iteration. Can be captured on demand before Phase 4.0 close (iter 070).
- **Plan capture-script port.** Plan says `localhost:5173`; Makefile runs vite on `5174`. If anyone resurrects the capture script, update the port. Low-priority plan-cleanup.

### What exists after iter 063

Seven primitives under `frontend/src/lib/ui/`:
- `Button.svelte` (primary | secondary | ghost, disabled)
- `StatusPill.svelte` (green | blue | orange | red | gray tones with leading dot)
- `ProgressBar.svelte` (0-100 clamped, optional label, ARIA progressbar)
- `Input.svelte` (bindable value, invalid state)
- `Select.svelte` (bindable value, options, invalid state)
- `DateInput.svelte` (native `<input type="date">`, bindable value)
- `Toggle.svelte` (button + aria-pressed, bindable pressed)

All exercised by `frontend/tests/primitives.spec.ts` (9 tests) via the `/ui-demo` gallery route. Pre-revamp `$lib/components/StatusPill.svelte` and the rest of `$lib/components/` continue to serve pre-revamp pages unchanged.

Carried forward: none. All four plan tasks (5, 6, 7, 8) completed.
