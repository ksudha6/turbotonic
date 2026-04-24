# Iteration 064 -- Composite primitives: FormField, PanelCard, AttributeList, FormCard, KpiCard

## Context

Fourth iteration of Phase 4.0. Iter 063 shipped seven leaf primitives (Button, StatusPill, ProgressBar, Input, Select, DateInput, Toggle) under `frontend/src/lib/ui/`. All use the `ui-<name>` outermost-class convention to avoid colliding with pre-revamp `global.css` rules. `frontend/tests/primitives.spec.ts` has 9 tests exercising them via `/ui-demo`.

This iteration ships five composite primitives (Plan Tasks 9-11):

- **Task 9** -- `FormField` (server-error contract: inline error message, `aria-invalid` on child input, optional hint)
- **Task 10** -- `PanelCard` (surface with header + optional action + body), `AttributeList` (label/value grid), `FormCard` (form with footer Cancel + Submit buttons)
- **Task 11** -- `KpiCard` (label + big value + tone-colored delta chip)

FormField requires a small extension to the iter 063 `Input` primitive: render `aria-invalid={invalid || undefined}` on the `<input>` so the FormField test assertion can observe it. This is backwards-compatible — Input keeps accepting the same props, it just now surfaces the invalid state through ARIA as well as CSS.

Scope note on the "brainstorm error states" marker on iter 064: the Lovable mock does not show explicit error-state visual designs for forms. The plan's FormField already handles the common case (server returns `error: string`; field shows it inline with `role="alert"` + `aria-invalid` on the input). Form-level errors (e.g., "Network failed") are an aggregate-page concern and land in iter 071+. No brainstorm stop needed at this layer.

Ship gates for 064:
- Mock-clarity: FormField error visual follows the plan's red-text-under-input pattern, which is the universal default. PanelCard / AttributeList / FormCard / KpiCard are visible in the mock as surface patterns. **No brainstorm stop.**
- Past-flow: 591 backend + 109 browser green at iter open. Must stay green at close.
- Future-flow: Composite primitives consume leaf primitives (FormCard uses Button, FormField wraps child primitives via snippet). Must not break any iter 063 leaf primitive.

## JTBD (Jobs To Be Done)

- As a developer building a redesigned form in iter 071+, when I need a labeled input with server error support, I want a `FormField` that takes a label, optional hint, optional error, and a child snippet, so my form handles validation surface without per-field wiring.
- As a developer building a redesigned detail page, when I need a surface with a title and a body, I want `PanelCard` + `AttributeList` so I can render "Details" sections without reinventing chrome.
- As a developer building a create/edit form, when I need a card with a header + body + Cancel/Submit footer, I want `FormCard` to wrap my fields with consistent submit handling.
- As a developer building the dashboard in iter 071+, when I need a stat widget showing label + value + trend delta, I want `KpiCard` so every metric renders identically.
- As a screen-reader user filling out a form with a validation error, I want the input's invalid state announced via `aria-invalid` and the error message announced via `role="alert"`, so I know which field needs correction.

## Tasks

### Task 9 -- `FormField` with server-error contract

Includes a small Input extension to surface `aria-invalid`.

- [ ] Extend `frontend/src/lib/ui/Input.svelte` to render `aria-invalid={invalid || undefined}` on the `<input>` element. The existing `class:invalid` toggle stays. The Input's `invalid` prop default (`false`) is unchanged.
- [ ] Append `FormField primitive` describe block to `primitives.spec.ts` (1 test: shows inline error + sets aria-invalid on child input). Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/FormField.svelte` per plan Task 9 Step 2 with one deviation: outermost class `ui-field` (not plan's `.field`).
- [ ] Extend `/ui-demo` with a FormField in error state showing an Input child via snippet.
- [ ] Run — expect PASS (10 total passed). Run `make test-browser` — expect 110.
- [ ] Commit: `Add FormField with server-error contract + Input aria-invalid (iter 064 task 9)`.

### Task 10 -- `PanelCard`, `AttributeList`, `FormCard`

- [ ] Append `Panel primitives` describe block to `primitives.spec.ts` (3 tests: PanelCard title visible, AttributeList renders label+value, FormCard has Cancel+Submit). Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/PanelCard.svelte` per plan Task 10 Step 2 with class rename `.panel` → `.ui-panel`.
- [ ] Create `frontend/src/lib/ui/AttributeList.svelte` per plan Task 10 Step 3 with class rename `.list` → `.ui-attr-list`.
- [ ] Create `frontend/src/lib/ui/FormCard.svelte` per plan Task 10 Step 4 with class rename `.card` → `.ui-form-card`. **Critical:** pre-revamp `global.css` defines a global `.card` rule (border, shadow, padding). Without the rename, FormCard inherits double-styling from that rule.
- [ ] Extend `/ui-demo` with PanelCard + AttributeList section and a FormCard section.
- [ ] Run — expect PASS (13 total). Run `make test-browser` — expect 113.
- [ ] Commit: `Add PanelCard + AttributeList + FormCard (iter 064 task 10)`.

### Task 11 -- `KpiCard`

- [ ] Append `KpiCard` test (1 test: label + value + delta visible). Run — expect FAIL.
- [ ] Create `frontend/src/lib/ui/KpiCard.svelte` per plan Task 11 Step 2 with class rename `.kpi` → `.ui-kpi`.
- [ ] Extend `/ui-demo` with a KpiCard section.
- [ ] Run — expect PASS (14 total). Run `make test-browser` — expect 114.
- [ ] Commit: `Add KpiCard primitive (iter 064 task 11)`.

## Existing test impact

Pre-iteration audit:
- `frontend/tests/primitives.spec.ts` — extended by three describe blocks (FormField, Panel primitives, KpiCard). No existing tests touched.
- `frontend/src/lib/ui/Input.svelte` — the aria-invalid extension is additive. The existing `'Input primitive accepts typed text'` test does not assert aria-invalid absence (it only checks value fill), so the change does not regress it.
- No pre-revamp spec depends on any `$lib/ui/` file — the namespace is still new as of iter 063.
- `/ui-demo` currently has five sections (Button, StatusPill, ProgressBar, Form controls, implicit seeded content). Adding four more sections (FormField, Panel, FormCard, KpiCard) does not break the page; sections stack vertically.

If any pre-revamp spec breaks, the likely cause is:
- Accidental edit to `global.css` — none planned.
- Accidental edit to `$lib/components/` — none planned.
- Test selector collision between existing and new `data-testid` values — audit before dispatch: existing testids start with `ui-btn-*`, `ui-pill-*`, `ui-progress-*`, `ui-input-*`, `ui-select-*`, `ui-date-*`, `ui-toggle-*`. New testids start with `ui-field*`, `ui-panel*`, `ui-attr-list*`, `ui-formcard*`, `ui-kpi*`. No overlap.

No fixtures, mocks, or helpers need updating.

## Tests

### Permanent tests added this iteration
- `frontend/tests/primitives.spec.ts` extended to **14 tests total**:
  - Button: 3 (from iter 063)
  - StatusPill: 1 (from iter 063, strengthened)
  - ProgressBar: 1 (from iter 063)
  - Form controls: 4 (from iter 063)
  - FormField: 1 (new)
  - Panel primitives: 3 (new — PanelCard, AttributeList, FormCard)
  - KpiCard: 1 (new)

Each test visits `/ui-demo` with mock order `mockApiCatchAll` then `mockUser` (LIFO convention from iter 063).

Expected `make test-browser` count at close: **114 passed**.

### Scratch tests
None. Visual verification of the new primitives can be done ad-hoc via the dev server visiting `/ui-demo`; scratch screenshots deferred to iter 070 (Phase 4.0 close).

### Logs
- `logs/playwright-test-browser.log` — `make test-browser` at iteration close, expect 114 passed.
- `logs/pytest.log` — iteration-open and iteration-close snapshots (expect 591 passed both times; no backend change).

## Notes

Iter 064 closed on 2026-04-24. Four commits landed on `ux-changes`:
- `2acbfb3` Task 9 FormField + Input aria-invalid extension.
- `e7d6ec8` Task 10 PanelCard + AttributeList + FormCard.
- `4eb93ba` Task 11 KpiCard.

Full suite green at iter open (591 backend + 110 browser — wait, 110 includes iter-064-task-9's FormField test which landed early in this iter; at iter-064 open proper the count was 109. Spelling it out: 109 at iter-063 close → 110 after Task 9 → 113 after Task 10 → 114 at iter-064 close). Backend stays 591 (no backend change in this iteration).

### Decisions

- **FormField `aria-invalid` wiring via Input extension.** Plan test asserts `aria-invalid='true'` on the child Input but the iter-063 Input primitive didn't render `aria-invalid`. Extended Input with `aria-invalid={invalid || undefined}` — the `|| undefined` omits the attribute entirely when the field is valid, matching W3C guidance that `aria-invalid="false"` is noise. Backwards-compatible; existing `'Input primitive accepts typed text'` test still passes.
- **FormCard class rename critical.** Pre-revamp `global.css` `.card` rule has its own surface-card bg, gray-200 border, radius-lg, shadow-sm, padding-6. Without renaming to `ui-form-card`, FormCard inherits the pre-revamp rule on top of the scoped one. Same convention as iter-063 `ui-btn`.
- **PanelCard and KpiCard class renames `.panel` → `ui-panel` and `.kpi` → `ui-kpi`.** Neither pre-revamp class exists today, but the `ui-<name>` convention is enforced for primitive insulation going forward.
- **No brainstorm stop on error states.** The plan's field-level error contract (server returns `error: string`, FormField renders inline with `role="alert"` + aria-invalid on child) is complete for this layer. Form-level banner errors and global error handling move to iter 065 (ErrorBoundary + ErrorState primitives).
- **KpiCard demo label "OUTSTANDING" (uppercase).** The primitive applies `text-transform: uppercase` in CSS, but Playwright's `toContainText` matches DOM text content, not CSS-rendered text. Plan passed `"Outstanding"` in the demo and asserted `'OUTSTANDING'` in the test — these would not match. Resolved by passing the demo label as uppercase literal; documented in commit. Follow-up: in real usage the KpiCard consumer will pass mixed-case labels and rely on CSS uppercase; the test harness on `/ui-demo` is a special case.

### DDD vocab assessment

No new domain terms emerged. The primitives (FormField, PanelCard, AttributeList, FormCard, KpiCard) are UI design-system vocabulary. `docs/ddd-vocab.md` unchanged.

### Backlog captured

- **KpiCard hex values for positive/negative delta tones** (`#dcfce7/#166534`, `#fee2e2/#991b1b`) duplicate existing `--green-100/--green-800` and `--red-100/--red-800` tokens. Mechanical refactor deferred along with the matching StatusPill backlog item.
- **FormField snippet type cleanup.** Snippet parameter type is `{ invalid: boolean; 'aria-invalid': boolean }` but no demo consumer uses `'aria-invalid'`. Consider simplifying to `{ invalid: boolean }` once a real consumer is wired in iter 071+.
- **AttributeList key uniqueness.** Each-block key is `item.label`, which breaks with duplicate labels (e.g. two "Amount" rows). If a consumer needs duplicates, replace with an index key or require a unique `id` per item.
- **KpiCard test relies on uppercase demo label.** Preferred fix: change the test assertion to `toContainText('Outstanding')` and let CSS handle visual uppercase. Deferred.

### What exists after iter 064

Twelve primitives under `frontend/src/lib/ui/`:
- Leaves (iter 063): Button, StatusPill, ProgressBar, Input, Select, DateInput, Toggle.
- Composites (iter 064): FormField, PanelCard, AttributeList, FormCard, KpiCard.

All exercised by `frontend/tests/primitives.spec.ts` (14 tests) via `/ui-demo`. The gallery now has 8 sections (Button, StatusPill, ProgressBar, Form controls, FormField, Panel + Attributes, FormCard, KpiCard). Input primitive now surfaces `aria-invalid` when `invalid` is true.

Carried forward: none. All three plan tasks (9, 10, 11) completed.
