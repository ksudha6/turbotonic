# Iteration 062 -- Design tokens + (nexus) layout scaffold + /ui-demo route

## Context

Second iteration of Phase 4.0. iter 061 shipped the non-UI prerequisites (permissions ADMIN inheritance + seed variety). This iteration builds the visual baseline that all subsequent primitives consume:

1. **Design tokens** appended to `frontend/src/lib/styles/global.css`. Additive only — no deletion of pre-revamp component rules (`.btn`, `.table`, `.badge`, `.card`, `.input`). Those stay until every aggregate phase retires its old routes; deleting in 4.0 would break every pre-revamp page and violate past-flow.

2. **`(nexus)` route group** — new SvelteKit layout group at `frontend/src/routes/(nexus)/`, empty of user-facing pages. Gives iter 063+ a home for primitives-wrapped demo routes and iter 071+ a home for the redesigned Dashboard, Production, Invoice, Vendor, Product, and Auth pages. Pre-revamp `frontend/src/routes/+layout.svelte` stays for the rest of the app.

3. **`/ui-demo` route** — dev-only internal gallery at `frontend/src/routes/ui-demo/+page.svelte`. Not linked from nav. Each subsequent iter 063-069 extends this page with new primitives. Supports `frontend/tests/primitives.spec.ts` (permanent Playwright spec added in iter 063).

Ship gates for 062:
- Mock-clarity: tokens inferred from mock visuals (palette, spacing, radius) and already locked in the design spec; `(nexus)` scaffold is internal, no mock. `/ui-demo` is a dev tool, no mock. **No brainstorm stop needed.**
- Past-flow: 591 backend + 100 browser green before iteration opens. Must stay green at close. Pre-revamp routes must render identically (this iter is additive).
- Future-flow: no primitives exist yet. Tokens must not preempt primitive decisions in later iters (e.g., avoid over-specific tokens that force a particular component shape).

## JTBD (Jobs To Be Done)

- As a developer building a primitive in iter 063+, when I reach for a color/spacing/radius value, I want it available as a CSS variable under a stable name, so my primitive and every later primitive share the same token.
- As a reviewer auditing the revamp, when I visit `/ui-demo` I want to see every primitive the revamp has introduced so far, so I can visually verify the system without opening individual files.
- As a SvelteKit author building redesigned pages in iter 071+, when I create a new route under `(nexus)/`, I want the `(nexus)/+layout.svelte` to wrap my page in the eventual `AppShell` (stubbed passthrough in 062, real shell in iter 068), so I do not have to re-plumb the shell per page.
- As a Playwright author in iter 063+, when I assert a primitive's rendering, I want an authenticated route I can visit with a mocked user, so I can test primitives in isolation without coupling to a real aggregate's data.

## Tasks

### Task 3 -- Scaffold `(nexus)` layout group
- [ ] Create `frontend/src/routes/(nexus)/+layout.ts` with `prerender = false`, `ssr = false`, and a `load` that redirects to `/login?redirect=<path>` when the user is unauthenticated (same pattern as pre-revamp `+layout.ts`).
- [ ] Create `frontend/src/routes/(nexus)/+layout.svelte` as a minimal passthrough: imports `$lib/styles/global.css`, renders `{@render children()}`. `AppShell` wiring is deferred to iter 068 once the shell primitives exist.
- [ ] Run `cd frontend && npm run check`. Expected: no TypeScript errors.
- [ ] Run `make test-browser`. Expected: 100 passed. No new route in `(nexus)` yet so nothing new to test, just regression.

### Task 4 -- Append design tokens to `global.css`
- [ ] Append new tokens inside the existing `:root` block. Categories: shell surfaces (page, card, sidebar), text (primary, secondary, sidebar, muted), brand/accents, button solids, status dots (five tones), typography extensions (xs, 3xl, wide letter-spacing), spacing extensions (7, 20), breakpoint custom properties (390, 768, 1024, 1440).
- [ ] Do NOT delete or modify any existing token or component rule (`.btn`, `.table`, `.badge`, `.card`, `.input`, `.form-group`).
- [ ] Run `cd frontend && npm run build`. Expected: build succeeds.
- [ ] Run `make test-browser`. Expected: 100 passed. Pre-revamp pages must render identically -- tokens are additive.

### Task 5 bootstrap -- Create `/ui-demo` route skeleton
- [ ] Create `frontend/src/routes/ui-demo/+page.svelte` with an `<h1>Phase 4.0 UI Demo</h1>` heading and no primitive sections yet (iter 063 starts populating). Keep the file intentionally minimal.
- [ ] Verify navigation: visit `/ui-demo` in `npm run dev` manually (or via a smoke test in `frontend/tests/primitives.spec.ts` added in iter 063). Must render under the pre-revamp layout since we do not place it under `(nexus)` -- `/ui-demo` is a dev gallery, not a redesigned page.

Note: Task 5 from the plan includes `Button` + test bootstrap; that content lands in iter 063. This iteration only scaffolds the `/ui-demo` file so iter 063 can extend it without creating it.

## Existing test impact

Pre-iteration audit:
- No existing test touches `frontend/src/lib/styles/global.css` directly -- rules are consumed by existing component markup, not asserted by Playwright.
- No existing test imports from `frontend/src/routes/(nexus)/` (doesn't exist yet).
- No existing test visits `/ui-demo` (doesn't exist yet).
- `frontend/src/routes/+layout.ts` stays untouched. Its redirect behavior (deep-link preservation on `/login`) continues to be asserted by `auth-flow.spec.ts` and `po-lifecycle.spec.ts` login-redirect cases.

No existing test should break from this iteration. If `make test-browser` reports any failure, the cause is likely an unintended side effect of the token additions (e.g., token name collision with an existing CSS variable). Investigate before flipping tests.

No fixtures or helpers need updating.

## Tests

### Permanent tests added this iteration
None. Primitives testing starts in iter 063 with `frontend/tests/primitives.spec.ts`. This iteration ships the infrastructure those tests will use.

### Scratch tests
None. No visual surface to verify yet (the token additions are not rendered; the `(nexus)` scaffold is empty; `/ui-demo` has only a heading).

### Logs
- `logs/make-test-browser.log` at iteration close (expected: 100 passed).
- `cd frontend && npm run build` output captured in the implementer report (must succeed).

## Notes

Iter 062 closed on 2026-04-24. Three atomic commits landed on `phase-4-0-foundation`: `6ef63e6` ((nexus) scaffold), `f37ed25` (design tokens), `a5c1c05` (/ui-demo skeleton). Full suite green at both iteration open (591 + 100) and close (591 + 100).

No new domain terms introduced, so `docs/ddd-vocab.md` is unchanged.

Decisions:
- `(nexus)/+layout.svelte` ships as a minimal passthrough; AppShell wiring is deferred to iter 068 once the shell primitives exist. This keeps `(nexus)` empty but functional (auth redirect still enforced).
- `/ui-demo` placed at `frontend/src/routes/ui-demo/+page.svelte` (NOT under `(nexus)`) so it renders under the pre-revamp root layout. Dev-only gallery; iter 063+ populates it.
- Tokens are additive only. Pre-revamp component rules (`.btn`, `.table`, `.badge`, `.card`, `.input`) stay untouched; deletion deferred to end of revamp after every aggregate phase retires its old routes.

Incidental finding from the review: adding `--font-size-xs` retroactively fixed two pre-existing consumers that had been falling through to browser defaults (`frontend/src/routes/dashboard/+page.svelte:342,348`) or relying on an inline fallback (`frontend/src/routes/shipments/[id]/+page.svelte:249`). Both predate the revamp. No regression; these pages now render the intended size.

Carried forward: none. Three sub-tasks completed. Plan's Task 5 (full `Button` primitive + `primitives.spec.ts`) starts iter 063 with the skeleton ready.
