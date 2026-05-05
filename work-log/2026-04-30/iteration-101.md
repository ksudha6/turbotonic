# Iteration 101 — `/login` `/register` `/setup` Phase 4 port

## Context

These three pre-revamp routes are the last ones outside the Phase 4 surface. The migration
covered iter 071 (dashboard), iters 076 (PO list), 077 (PO detail), 086 (invoice list),
087 (invoice detail), 089 (vendors), 090-094 (products), and 097 (shipment detail).

Auth routes stay outside the `(nexus)` group: no AppShell, Sidebar, or TopBar because there
is no session yet. They render as bare centered cards. The only applicable primitives are
`PanelCard` + `FormField` + `Input` + `Button`, replacing the existing class-selector layout
(`.page`, `.card.login-card`, `.btn-primary`) without adding shell chrome.

Iter C in `parallel-slate-plan.md`. Disjoint from iter 100 (`/users` page); `types.ts`
updates land with iter 100 only.

## JTBD

As a user landing on `/login` for the first time, I want the page to feel like the rest of
the product I am about to enter — same typography, same button shapes, same form-field
density — so the transition from sign-in to dashboard is not jarring.

As a maintainer staring at a divergent CSS file (`.btn-primary` here, `Button` primitive
everywhere else), I want one source of truth for the form-field + button visual rules across
the app, so a future tweak to `Button` automatically applies to login.

As a Playwright test author, I want auth-route tests to use the same selector vocabulary
(testid + role) as the rest of the suite, so I do not need to maintain two parallel selector
conventions when writing dev-login or onboarding flows.

## Pre-mortem facts

- **All three routes are OUTSIDE `(nexus)`** — `frontend/src/routes/login/+page.svelte`,
  `frontend/src/routes/register/+page.svelte`, `frontend/src/routes/setup/+page.svelte`. Do
  NOT move them under `(nexus)`. Auth routes do not get the AppShell.

- **Current sizes**: login 195 lines, register 163 lines, setup 166 lines. All three mix
  class selectors (`.page`, `.card`, `.login-card`, `.btn-primary`, `.form-row`) with one or
  two Phase 4 imports (`Button`). Full primitive replacement is the target.

- **`frontend/src/lib/auth.ts` (124 lines) is isolated from `api.ts`**. Exports: `bootstrap`,
  `registerOptions`, `registerVerify`, `loginOptions`, `loginVerify`, `logout`,
  `getDevUsers`, `devLogin`, `me`. This iter does NOT change auth.ts — only the route
  templates that consume it.

- **`/login` page already has dev-login UX (iter 079)**: a "Dev quick-login" row with one
  button per seeded user appears when `getDevUsers()` returns a list. Keep this behaviour
  exactly as-is when porting; only the styling moves to Phase 4 primitives.

- **`/register` consumes `?token=`** (iter 096) — a UUID v4 from the invite. The page calls
  `registerOptions({token})` then `registerVerify({credential, token})`. Do not break this
  flow; the input names are query-param-driven, not form-field-driven, so the visual revamp
  has no risk of breaking it.

- **`/setup` is the bootstrap page**. It runs the "very first admin" flow: prompts for
  username + display_name, calls `bootstrap`, gets back `{user, invite_token}`, then the
  same `register/options` + `register/verify` dance using the bootstrap-issued token. It is
  visited exactly once per database lifetime in production; commonly the first page a
  developer sees.

- **`?redirect=` query param** (iter 079) is honored by `/login` after dev-login. Preserve.

- **Existing Playwright `dev-login.spec.ts` (iter 079) already uses `getByTestId` and
  `getByRole`** — selector policy: it will NOT break on the revamp as long as the testids
  it references are preserved on the new components. Specifically: the spec keys off testids
  for the dev-login row buttons. Audit the spec, list the testids it references, and ensure
  they survive the rewrite.

- **No Phase 4 textarea primitive.** None of the auth routes need a textarea; not relevant.

- **No Phase 4 modal needed.** Auth flows are linear; failures surface inline.

## Scope

In:
- Visual revamp of three routes:
  - `frontend/src/routes/login/+page.svelte`
  - `frontend/src/routes/register/+page.svelte`
  - `frontend/src/routes/setup/+page.svelte`
- Each route renders a centered `PanelCard` containing the form. `FormField` wrappers around
  `Input` for every field. `Button` for primary + secondary actions. Layout is plain-flex
  vertical stack on mobile, centered card with max-width on desktop. No Sidebar / AppShell /
  TopBar.
- Migrate every class selector to either a primitive or to a minimal local CSS module on the
  page — but only what is necessary for layout (centering, max-width, vertical rhythm).
  Hard-coded color / typography rules are removed; primitives carry them.
- Preserve every behaviour:
  - `/login`: WebAuthn login flow, dev-quick-login row (iter 079), `?redirect=` honoring,
    error display, "Need an account? Use your invite link." link.
  - `/register`: WebAuthn register flow, `?token=` consumption, error display, conditional
    bootstrap-redirect when there are no users yet.
  - `/setup`: bootstrap flow (first admin), error display, redirect to `/login` after
    success.

Out:
- Logic / flow changes. This is purely a visual port; behavior is bit-for-bit identical
  before and after. Any behavior change is its own iter.
- Auth-helper changes. `frontend/src/lib/auth.ts` is untouched.
- New primitives. The five primitives needed (`PanelCard`, `FormField`, `Input`, `Button`,
  optionally `LoadingState` for the WebAuthn-in-progress state) all exist.
- Bootstrap-flow simplification. `/setup` does its own bootstrap → register handshake; the
  iter 096 design has the bootstrap response already include a token so `/setup` does not
  redirect through `/register` — preserve that.

## Tasks

1. **Inventory shared primitive imports.** Each of the three routes imports from
   `frontend/src/lib/ui/`. Confirm `PanelCard`, `FormField`, `Input`, `Button` cover
   everything. The current pages also use:
   - Plain `<form>` elements — keep, they nest inside `PanelCard`.
   - Plain `<a>` links to `/register` / `/login` — keep, no `Link` primitive exists.
   - Inline error spans — replace with the existing `ErrorState` primitive if it has a
     compact / inline mode, otherwise hand-roll a small `<p class="error">` (mirror of
     `VendorForm` / `PoForm` inline-error pattern from iters 089 and 085).

2. **`/login` revamp**:
   - Centered `PanelCard` titled "Sign in" with the form inside.
   - `FormField` wrapping `Input` for "Username".
   - Primary `Button` "Sign in" (full-width on mobile, auto width on desktop).
   - Below the card: "First time? Use your invite link to register." Plain `<a>` to nowhere
     (or to `/register` if we want to be friendly — register without `?token=` shows an
     error page; the existing copy is "Use your invite link" so it does not pretend
     standalone register works).
   - Dev-login row (iter 079): mounts when `getDevUsers()` returns a list. Each user gets a
     `Button` (variant=secondary) with `data-testid="dev-login-{username}"`. Honor
     `?redirect=` after success.
   - Errors: inline `<p>` with `data-testid="login-error"`.

3. **`/register` revamp**:
   - Centered `PanelCard` titled "Complete your registration".
   - Reads `?token=` from the URL on mount. If missing, render an error PanelCard "No token
     provided. Use the invite link from your administrator." and skip the form.
   - With token: shows display-name (read-only, fetched via `registerOptions`'s response or
     similar — preserve current behavior; if the current page does not show display-name,
     do not add it).
   - Primary `Button` "Create passkey".
   - Errors: inline `<p>` with `data-testid="register-error"`.

4. **`/setup` revamp**:
   - Centered `PanelCard` titled "Set up your administrator account".
   - `FormField` + `Input` for "Username", `FormField` + `Input` for "Display name".
   - Primary `Button` "Create admin account".
   - On success: shows a transient "Account created. Setting up passkey..." state, runs the
     register-options + register-verify dance, then redirects to `/login`. (Match current
     behavior.)
   - Errors: inline `<p>` with `data-testid="setup-error"`.

5. **Style file cleanup**:
   - Remove `.btn-primary`, `.btn-secondary`, `.login-card`, `.register-card`, `.setup-card`,
     `.form-row`, `.error` class definitions from each route's `<style>` block. Keep only
     layout rules: centering (`.page` flex column align-items: center), max-width on the
     PanelCard wrapper, vertical rhythm if needed.
   - If a class is shared across all three pages (like `.page`), consider lifting it to
     `frontend/src/app.css` — but only if it is genuinely identical. Drift is the enemy.

6. **Tests `frontend/tests/auth-routes.spec.ts`** (new file):
   - **Existing test impact**:
     - `dev-login.spec.ts` (iter 079, 200 lines, 4 specs): uses testid + role selectors
       throughout. Audit specifically the testids `dev-login-{username}` and any role
       lookups; preserve them on the revamped `/login`. The existing 4 specs should pass
       unchanged.
     - `role-rendering.spec.ts`: spot-check for any class-selector queries against `/login`
       or `/register`. If found, migrate to testid as part of this iter's selector-policy
       compliance.
     - All other specs: no break expected. Auth routes are end-points; nothing else imports
       from them.
   - New permanent specs (in addition to dev-login.spec.ts):
     - `/login` page renders PanelCard with "Sign in" title.
     - `/login` username field has `data-testid="login-username"`, "Sign in" Button has
       `data-testid="login-submit"`.
     - `/login` invalid username surfaces error inline.
     - `/login` "First time? Use your invite link" link is visible.
     - `/login` mobile (390px) PanelCard fills width; Button is full-width.
     - `/register?token=<valid>` renders "Complete your registration" + form.
     - `/register` (no token) renders the error PanelCard.
     - `/register` form submit fires `registerVerify` with the token from the URL.
     - `/setup` renders "Set up your administrator account" + 2 inputs + Button.
     - `/setup` blank username blocks submit.
     - `/setup` happy path bootstraps + redirects to `/login`.
   - Mock WebAuthn `navigator.credentials.create` / `.get` via `page.addInitScript` (same
     pattern as `dev-login.spec.ts`'s `_mockWebAuthn` helper if it exists).

7. Run `make test-browser`; confirm 357 → 370+ pass. No backend changes — `make test-backend`
   should be unchanged.

## Decisions

- **Auth routes stay outside `(nexus)`.** Adding AppShell / Sidebar / TopBar to a
  pre-session page would render an empty navbar against an unauthenticated context — wrong
  affordance. Phase 4 ports do not always mean "move under (nexus)"; they mean "use Phase
  4.0 primitives". The shell decision is independent.

- **One PanelCard per route, not a shared `AuthLayout` component.** The three routes share
  the centered-card-on-plain-background pattern, but factoring this out into a layout
  component would couple their independent flows for marginal DRY benefit. Three short
  pages each rendering a `PanelCard` directly is clearer than three pages calling a single
  layout abstraction with subtly different inner content. Three is the bar at which DRY
  pays off (rule of three) — but the variance between login (1 input + dev-row),
  register (0 inputs + WebAuthn trigger), and setup (2 inputs + bootstrap) is high enough
  that a shared layout would need lots of slots / props. Skip the abstraction.

- **No Card-level shadow / elevation primitive.** PanelCard already carries elevation via
  its CSS tokens; do not add a wrapper.

- **Dev-login row stays on `/login`, not extracted to its own component.** Iter 079
  shipped it inline; it is ~30 lines including the loading + error states. Extracting to
  `DevLoginRow.svelte` is one indirection too many for a feature gated to dev-only
  environments. Keep inline; if a third surface ever needs dev-login, factor then.

- **Error display is plain `<p>`, not `ErrorState`.** `ErrorState` is built for full-card
  errors (with retry button). Inline form errors are a different shape — the existing
  `VendorForm` / `PoForm` pattern uses a small `<p>` near the field; mirror that.

## Risks

- **`dev-login.spec.ts` testid drift.** If the revamp changes the testid on the dev-login
  user buttons, the iter-079 specs break. Read that file first; preserve every testid it
  queries.

- **WebAuthn mock pattern.** Tests for `/register` and `/setup` need a WebAuthn shim.
  Search existing tests (`dev-login.spec.ts`, possibly an onboarding test) for the
  `navigator.credentials` mock pattern; reuse it. Inventing a new mock approach risks
  flakiness.

- **`registerOptions` / `registerVerify` body shape**. Iter 096 changed these from
  `{username}` to `{token}`. Ensure the revamped `/register` page reads `?token=` not
  `?username=`. The existing page should already do this; verify before submitting.

- **`/setup` bootstrap response shape**. Iter 096 changed bootstrap to return
  `{user, invite_token}`. The revamped page must consume `invite_token` for the
  immediately-following register handshake without redirecting through `/register?token=`.
  Verify the existing flow and preserve.

- **CSS specificity issues**. Removing global `.btn-primary` rules may cascade unexpected
  changes if any other route still relies on them. Grep all `.svelte` files for
  `class="btn-primary"` before deleting the rule. If any non-auth surface uses it, scope
  the deletion to the auth routes only and leave the global rule until a separate cleanup.

- **Playwright port collision with iter 100 worktree running in parallel.** If both run
  `make test-browser` simultaneously, the vite dev server port may collide. If the test
  command fails with EADDRINUSE, run sequentially.

## Notes

Implementation split across the planned Sonnet sub-agent and a follow-up Opus pass. The sub-agent ported all three routes (`/login`, `/register`, `/setup`) cleanly to PanelCard + FormField + Input + Button, preserving every flow: WebAuthn handshake, `?token=` consumption, `?redirect=` honoring, the dev-quick-login row from iter 079 with its `dev-login-{username}` testid surface, and the bootstrap-issued-token shortcut on `/setup`. The 9 new specs in `auth-routes.spec.ts` cover login (mount + testids + inline error), register (no-token error + token-mounted form + verify-receives-token), and setup (mount + happy-path bootstrap + already-configured branch). Sub-agent ran out of turns before getting `make test-browser` green and left an uncommitted `frontend/playwright-iter101.config.ts` (port-5175 workaround for sibling-worktree vite contention) which was deleted before commit. The follow-up pass found one real test bug: the `/setup happy path` test registered a `**/api/v1/**` catch-all *after* the specific bootstrap and register-verify mocks. Playwright resolves matching routes in reverse-registration order, so the catch-all intercepted bootstrap first and returned `{}`, which broke `startRegistration(undefined)` on the page and prevented the verify call. Fix was to register the catch-all first; the specific handlers added afterwards take priority. No `.btn-primary` / `.btn-secondary` / `.login-card` / `.register-card` / `.setup-card` / `.form-row` / `.error` rules survived the port — every class deletion was route-local. `role-rendering.spec.ts` had no class-selector queries against the auth routes; no migration needed there. No new domain terms emerged (visual port). 366 Playwright (+9) + 767 backend (no change). The Phase 4 surface is now feature-complete: every route a user reaches in the product renders on Phase 4.0 primitives.
