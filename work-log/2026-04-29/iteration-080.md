# Iteration 080 — Primitive `label` / `aria-label` plumbing (Phase 4.x cleanup)

## Context

The CLAUDE.md selector policy (iter 076) mandates new Playwright tests query by `getByRole`, `getByLabel`, or `getByTestId` only. Every primitive in [frontend/src/lib/ui/](frontend/src/lib/ui/) accepts a `testid` prop today, but most do not expose a `label` or `aria-label` prop, so role-based queries collide on multi-instance pages and label-based queries fall through. Backlog item "Primitive `label` / `aria-label` plumbing" (queued from iter 076 close) covers the retrofit.

This iter is a single mechanical pass across the primitive surface. Components with implicit accessible names (FormField wraps its child in `<label>`; Button's text is its name; Toggle's `label` prop is already wired) are unchanged. Components without one get either (a) an `ariaLabel` prop forwarded to `aria-label`, (b) a `label` prop forwarded to `aria-label` on the container, or (c) a generated id wired to `aria-labelledby` on the existing visible heading.

## JTBD

When I write a Playwright test against a primitive instance that has no implicit accessible name, I want `getByRole(...)` and `getByLabel(...)` to return that instance unambiguously, so I can satisfy the CLAUDE.md selector policy without adding a `testid` as the only option.

## Tasks

1. Frontend: control primitives ([Input](frontend/src/lib/ui/Input.svelte), [Select](frontend/src/lib/ui/Select.svelte), [DateInput](frontend/src/lib/ui/DateInput.svelte)) gain an `ariaLabel?: string` prop forwarded to `aria-label`. The implicit `<label>` parent (when used through [FormField](frontend/src/lib/ui/FormField.svelte)) already names the control via `for=`/`id` association, so `ariaLabel` is only needed for standalone usage.
2. Frontend: list and table container primitives ([ActivityFeed](frontend/src/lib/ui/ActivityFeed.svelte), [Timeline](frontend/src/lib/ui/Timeline.svelte), [AttributeList](frontend/src/lib/ui/AttributeList.svelte), [DataTable](frontend/src/lib/ui/DataTable.svelte)) gain a `label?: string` prop forwarded to `aria-label` on the root element. Default copy on `ActivityFeed` ("Activity feed") and `Timeline` ("Timeline") so most callsites need no extra prop.
3. Frontend: titled container primitives ([PanelCard](frontend/src/lib/ui/PanelCard.svelte), [KpiCard](frontend/src/lib/ui/KpiCard.svelte), [FormCard](frontend/src/lib/ui/FormCard.svelte), [DetailHeader](frontend/src/lib/ui/DetailHeader.svelte), [PageHeader](frontend/src/lib/ui/PageHeader.svelte)) generate a `crypto.randomUUID()` id at component init and wire `aria-labelledby` to the existing visible heading element. Existing visible title copy stays as the source of truth; no new prop required.
4. Frontend: [Sidebar](frontend/src/lib/ui/Sidebar.svelte) sections get the same uuid + `aria-labelledby` treatment for nav grouping.
5. Frontend: [UserMenu](frontend/src/lib/ui/UserMenu.svelte) trigger defaults `ariaLabel="Open user menu"`; the dropdown gets a static `aria-label="Account actions"` so role queries scope correctly.
6. Frontend: ARIA platform fixes that surface during retrofit:
   - [AttributeList](frontend/src/lib/ui/AttributeList.svelte) uses `<dl>`, which has no implicit role; tests assert on the `aria-label` attribute directly rather than via `getByRole`.
   - [DetailHeader](frontend/src/lib/ui/DetailHeader.svelte) and [PageHeader](frontend/src/lib/ui/PageHeader.svelte) gain explicit `role="banner"` so they resolve outside top-level document scope.
7. Frontend: [StatusPill](frontend/src/lib/ui/StatusPill.svelte) is comment-only — its visible text already serves as the implicit accessible name; document the rationale inline so future contributors do not "fix" it.
8. Frontend: components intentionally untouched: [FormField](frontend/src/lib/ui/FormField.svelte) (already wraps with `<label>`), [Button](frontend/src/lib/ui/Button.svelte) (text is name), [Toggle](frontend/src/lib/ui/Toggle.svelte) (`label` prop already wired), [EmptyState](frontend/src/lib/ui/EmptyState.svelte) (already has role wiring), [AppShell](frontend/src/lib/ui/AppShell.svelte), [TopBar](frontend/src/lib/ui/TopBar.svelte), [ProgressBar](frontend/src/lib/ui/ProgressBar.svelte), [LoadingState](frontend/src/lib/ui/LoadingState.svelte), [ErrorState](frontend/src/lib/ui/ErrorState.svelte), [ErrorBoundary](frontend/src/lib/ui/ErrorBoundary.svelte).
9. Frontend: extend [/ui-demo](frontend/src/routes/ui-demo/+page.svelte) with labeled-instance examples (one Input + one Select + one DateInput with `ariaLabel`; a labeled DataTable, AttributeList, PanelCard; a titled FormCard and KpiCard) so Playwright tests have stable surfaces to query.

## Tests

### Existing test impact

- Existing primitive tests at [frontend/tests/primitives.spec.ts](frontend/tests/primitives.spec.ts) assert on testids only. Adding `ariaLabel`/`label` props is non-breaking; existing assertions continue to pass.
- Page-level Playwright tests are unaffected. `getByRole` queries that already worked (Button, Toggle, etc.) keep working; queries that previously fell back to testids continue to use testids.
- Backend pytest suite — no changes; this iter is frontend-only.

### Permanent — frontend

15 new tests in [frontend/tests/primitives.spec.ts](frontend/tests/primitives.spec.ts) covering one role/label query per retrofitted primitive:

1. `Input with ariaLabel is reachable via getByLabel`
2. `Select with ariaLabel is reachable via getByLabel`
3. `DateInput with ariaLabel is reachable via getByLabel`
4. `ActivityFeed default aria-label resolves via getByRole + name`
5. `Timeline default aria-label resolves via getByRole + name`
6. `AttributeList label sets aria-label attribute (dl has no implicit role)`
7. `DataTable label is reachable via getByRole table + name`
8. `PanelCard title is announced via aria-labelledby`
9. `KpiCard title is announced via aria-labelledby`
10. `FormCard title is announced via aria-labelledby`
11. `DetailHeader title is announced via aria-labelledby (role="banner")`
12. `PageHeader title is announced via aria-labelledby (role="banner")`
13. `Sidebar section header is announced via aria-labelledby`
14. `UserMenu trigger has default aria-label`
15. `UserMenu dropdown has static aria-label="Account actions"`

### Scratch

None. The fifteen permanent tests cover the retrofit surface one-for-one.

## Notes

Done in parallel with iter 077 (PO detail revamp). Zero file overlap between the two: iter 077 touches `routes/(nexus)/po/[id]/`, `routes/+layout.svelte`, and three test specs; iter 080 touches the primitive layer and `ui-demo/+page.svelte` plus `primitives.spec.ts`. The primitive retrofit was originally bundled into the iter 079 dispatch by mistake; the work was correct and tested but wrong scope, so it was split out into this iter at commit time. Future Sonnet dispatches will include an explicit scope-fence in the prompt to prevent backlog items from being silently absorbed into the active iter.

The retrofit fixes the existing 15 primitives but does not by itself stop the same drift from recurring. To make the pattern global, [CLAUDE.md](CLAUDE.md) gains a "Primitive accessible-name convention" section under the Selector policy: every new primitive picks one of three plumbing patterns (controls → `ariaLabel` prop; list/table containers → `label` prop; titled containers → uuid + `aria-labelledby` on the visible heading) at creation time, not as cleanup. Components with implicit names (Button text, FormField, Toggle) are exempt. Retrofit iters like this one are now flagged as a smell rather than a normal flow.
