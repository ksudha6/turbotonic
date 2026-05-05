# Iteration 100 — `/users` ADMIN page

## Context

Iters 095, 096, 098, and 099 shipped a complete ADMIN user-management backend: list
(`?status=` + `?role=` filters), get, patch (display_name + email), invite, deactivate,
reactivate, reset-credentials, reissue-invite, and `USER_*` activity events. No frontend
consumes any of it; every operation is curl + dev DB.

The sidebar already has a `USERS` slot wired to ADMIN role at
`frontend/src/lib/ui/sidebar-items.ts:44-51`; it links to a 404 because the route does not
exist. This iter creates the route and the components behind it.

Iter A in `parallel-slate-plan.md`. Disjoint from iter 101 (auth route revamp) at the file
level; iter 101 touches `/routes/login`, `/routes/register`, `/routes/setup` only.

## JTBD

As an ADMIN, when a new user joins the team, I want a single page where I can invite them,
copy the resulting invite link, watch the user move from PENDING to ACTIVE in the list, and
later deactivate / reactivate / reset their credentials when their device changes — so I do
not have to keep curl handy and so the audit trail (iter 099) is human-visible.

As an ADMIN dealing with a lost passkey, I want a one-click "Reset credentials" action that
returns a fresh invite link I can share over Slack — without me needing to remember the right
endpoint name (it is the wrong call to use "Reissue invite" on an ACTIVE user, and the
backend correctly 409s, but the UI must steer me to the right action).

As an ADMIN doing routine roster review, I want to filter by status (ACTIVE / INACTIVE /
PENDING) and role to find stale or stuck accounts — so I can clean up offboarded staff or
chase up users who never completed registration.

## Pre-mortem facts (from the parallel-slate investigation)

- **Backend endpoints all live in `backend/src/routers/auth.py`** under prefix `/api/v1/users/`
  (the file is mis-named for legacy reasons; the prefix is correct in the router config).
  Surfaces:
  - `GET /api/v1/users/?status=&role=` → `{users: User[]}`
  - `POST /api/v1/users/invite` body `{username, role, display_name?, email?, vendor_id?}` →
    `{user, invite_token}`
  - `GET /api/v1/users/{id}` → `{user}`
  - `PATCH /api/v1/users/{id}` body `{display_name?, email?}` → `{user}`. Email: explicit
    `null` clears, omitted leaves untouched.
  - `POST /api/v1/users/{id}/deactivate` → `{user}` (409 self-without-cofounder, 409
    last-active-admin, 409 already-INACTIVE)
  - `POST /api/v1/users/{id}/reactivate` → `{user}` (409 not-INACTIVE)
  - `POST /api/v1/users/{id}/reset-credentials` → `{user, invite_token}` (409 already-PENDING,
    409 last-active-admin)
  - `POST /api/v1/users/{id}/reissue-invite` → `{user, invite_token}` (409 not-PENDING)

- **Frontend `User` type at `frontend/src/lib/types.ts` is missing `email`**. Backend
  `_user_to_dict` returns email; the type is silent on it. This iter adds `email: string |
  null` to the `User` type — that is a one-line fix that this iter must own; otherwise the
  patch flow for email cannot type-check.

- **`frontend/src/lib/api.ts` has zero user-related clients.** This iter appends seven:
  `listUsers(filters?)`, `inviteUser(input)`, `getUser(id)`, `patchUser(id, body)`,
  `deactivateUser(id)`, `reactivateUser(id)`, `resetCredentials(id)`, `reissueInvite(id)`.
  Eight, sorry. Naming matches the backend verb so future grep finds both sides at once.

- **`frontend/src/lib/permissions.ts` has no `canManageUsers`.** The existing pattern is
  `canCreatePO = (role) => is(role, 'SM')`. Add `canManageUsers = (role) => is(role,
  'ADMIN')` next to the existing helpers. ADMIN-bypass is already encoded in `is()`.

- **`frontend/src/lib/ui/sidebar-items.ts:44-51` already has the USERS slot.** No edits to
  that file. Verify the link target matches the route (`/users`).

- **No Modal / Dialog primitive in `frontend/src/lib/ui/`.** The codebase pattern for modals
  is hand-rolled per surface, mirroring iter 081's `PoLineModifyModal`, iter 084's
  `PoDocumentUploadDialog`, iter 087's `InvoiceDisputeModal`, iter 088's
  `InvoiceCreateModal`. Each uses a `<dialog>` (or a positioned `role="dialog"` div) with
  `aria-modal="true"`, `aria-labelledby` keyed to a `crypto.randomUUID()` heading id (iter
  080 convention), and Phase 4.0 `Button`s. This iter follows the same convention.
  Promotion to a primitive is its own future iter — out of scope.

- **No Phase 4.0 Toast / notification primitive.** The invite flow needs to surface the
  generated `invite_token` somewhere — copying it from a transient toast is the standard UX
  but no toast component exists. Solution: render the new invite URL in an inline panel that
  sticks until dismissed, with a "Copy link" button. Same pattern can serve reset-credentials
  and reissue-invite responses. The panel is an inline component, not a modal — it is
  read-only output, not a form.

- **iter 099 just shipped `USER_*` activity events.** Surfacing them as an activity feed on
  the user detail row is tempting; out of scope. Activity panel ships in a follow-up. The
  events fire today regardless — this iter just doesn't render them.

- **Existing template to mirror**: `(nexus)/products/+page.svelte` (~150 lines) for the
  list-page shell with `PageHeader` + filter row + `DataTable` (or hand-rolled `<table>` if
  per-row actions need DOM control). For the action rail / status-aware actions, see iter
  089's `VendorListTable` (status pill + per-row Deactivate/Reactivate Button) and iter 077's
  `PoActionRail`.

## Scope

In:
- New route `frontend/src/routes/(nexus)/users/+page.svelte`. Inherits AppShell + Sidebar +
  TopBar from the `(nexus)` group.
- New components in `frontend/src/lib/user/`:
  - `UserListFilters.svelte` — status select (ALL / ACTIVE / INACTIVE / PENDING) + role
    select (ALL + the 6 roles). Mirror of `VendorListFilters` from iter 089.
  - `UserListTable.svelte` — responsive desktop `<table data-testid="user-table-desktop">`
    + mobile cards `<div data-testid="user-table-mobile">` with shared `user-row-{id}`
    testid scoped via the parent (iter 086 strict-mode pattern). Each row shows username,
    display_name, role, status (Phase 4.0 `StatusPill`: ACTIVE→green, INACTIVE→gray,
    PENDING→orange), email, and a per-row action menu (Edit, Deactivate / Reactivate, Reset
    credentials, Reissue invite). Action visibility is status-aware (Reissue invite only on
    PENDING; Reactivate only on INACTIVE; Deactivate only on ACTIVE). Reset credentials is
    available on ACTIVE and INACTIVE (matches backend allowed states).
  - `UserInviteModal.svelte` — hand-rolled modal mirroring `PoDocumentUploadDialog`. Form:
    username (`Input`), role (`Select` with the 6 roles), display_name (`Input`, optional),
    email (`Input`, optional, type=email), vendor_id (`Select`, only shown when role=VENDOR
    — fetched from `listVendors` on first reveal). On success closes and signals the parent
    to render an `InviteLinkPanel`.
  - `UserEditModal.svelte` — hand-rolled modal. Form: display_name (`Input`), email
    (`Input`, type=email, blank → null cleared). PATCH on submit.
  - `UserActionConfirm.svelte` — generic confirm-destructive modal for deactivate / reset /
    reissue. Renders title + body copy + Confirm + Cancel. The parent passes a callback;
    on success, success-case rendering happens in the parent (the parent shows the new
    invite link via `InviteLinkPanel` on reset and reissue).
  - `InviteLinkPanel.svelte` — non-modal inline panel that sticks above the table until
    dismissed. Renders the invite URL (`window.location.origin + '/register?token=' + token`)
    + a "Copy link" button + a "Dismiss" Button. Used for invite, reset-credentials, and
    reissue-invite responses.
- New API clients in `frontend/src/lib/api.ts`: 8 functions named per the backend verbs.
  Append at the bottom of the existing function block; do not reorder.
- `frontend/src/lib/permissions.ts`: append `canManageUsers`.
- `frontend/src/lib/types.ts`: append `email: string | null` to the existing `User`
  interface; add `UserRole`, `UserStatus` literal-union types if not present (check first —
  the existing User type may already type role and status); add `InviteUserInput`,
  `PatchUserInput` shape types for the API.

Out:
- Activity panel on user detail. Iter 099's `USER_*` events fire today; surfacing them is a
  follow-up.
- Inline username / role / vendor_id mutation. Backend does not support it (iter 095 doc).
- Bulk actions. The list is small; multi-select adds complexity for negligible value.
- A Modal primitive in `lib/ui/`. Three modals + one panel here all hand-roll the convention;
  promote to a primitive in a future cleanup iter once the pattern is well-tested across 5+
  consumers.
- Email-confirmed invite flow (sending the link directly). Out of scope; ADMIN copies and
  shares the link manually.

## Permissions / route guards

- `(nexus)/users/+page.ts` (route load) redirects to `/dashboard` if `canManageUsers(user.role)`
  returns false. Mirror of `(nexus)/vendors/+page.ts`'s redirect-on-no-permission shape.
- ADMIN-only at the page level. Sub-component callbacks assume ADMIN; do not double-guard.
- Self-deactivate is a 409 path on the backend; the UI does not pre-emptively hide it. Show
  the 409 detail message inline on confirm-modal submit. (Last-admin guard returns its own
  message; both render via the same inline-error path.)

## Tasks

1. **Types `frontend/src/lib/types.ts`**:
   - Add `email: string | null` to `User`.
   - Add (if missing) `UserRole = 'ADMIN' | 'SM' | 'VENDOR' | 'FREIGHT_MANAGER' |
     'QUALITY_LAB' | 'PROCUREMENT_MANAGER'` and `UserStatus = 'ACTIVE' | 'INACTIVE' |
     'PENDING'`. The backend canonicalizes via Python enums; the frontend mirrors as union
     literals. Reuse anywhere `User.role` / `User.status` are referenced.
   - Add `InviteUserInput`, `PatchUserInput`, `UserListFilters` shape types.
   - Add `InviteUserResponse = { user: User; invite_token: string }`. Shared by invite,
     reset, reissue.

2. **Permissions `frontend/src/lib/permissions.ts`**:
   - `export const canManageUsers = (role: UserRole) => is(role, 'ADMIN');`
   - Use the existing `is()` helper. ADMIN bypass is already encoded.

3. **API clients `frontend/src/lib/api.ts`**:
   - 8 functions matching the backend verbs. URL prefix `/api/v1/users`. JSON parsing +
     error-translation patterns mirror existing functions in the same file. Use the existing
     `request()` (or whatever the file's helper is called).

4. **Route + components**:
   - `(nexus)/users/+page.ts`: redirect-on-no-permission load function.
   - `(nexus)/users/+page.svelte`: `PageHeader` ("Users", with primary "Invite user"
     `Button`) + `UserListFilters` (Status / Role / Clear) + `InviteLinkPanel` (rendered
     conditionally after a successful invite / reset / reissue) + `UserListTable` +
     `LoadingState` overlay + `EmptyState` (no filter match) + `ErrorState`.
   - `UserListFilters` mirrors `VendorListFilters`'s mobile-collapsing panel pattern.
   - `UserListTable` desktop = `<table>` (DataTable's `render` returns string|number, so
     hand-rolled — same precedent as `PoListTable`); mobile = `<div role="list">` of cards.
     Per-row actions: render an action button per applicable verb (status-aware visibility).
     If row count grows, an overflow menu would be the right move; for now inline action
     buttons match the small-roster reality.
   - `UserInviteModal`: 5 form fields (username required, role required, display_name
     optional, email optional, vendor_id required-when-role-VENDOR). Validation: username
     non-empty trimmed, email format if provided. On submit calls `inviteUser`; on success
     closes the modal and emits the response upward; on 409 (duplicate username) renders the
     server message inline.
   - `UserEditModal`: 2 fields (display_name, email). Email blank → null on submit. On
     success closes; the parent re-fetches the list (or splices the updated user in).
   - `UserActionConfirm`: title (e.g. "Deactivate user"), body copy that names the target
     username and explains the consequence ("They will no longer be able to log in.
     Reactivating restores access without re-issuing credentials."), Confirm Button (red /
     destructive variant), Cancel Button. Async confirm callback; if it rejects with a
     server message, render inline.
   - `InviteLinkPanel`: read-only, shows full URL `${window.location.origin}/register?token=${
     token}`, "Copy link" button (uses `navigator.clipboard.writeText`), "Dismiss" Button.
     Persists across re-renders until dismissed.

5. **Sidebar**:
   - Verify `frontend/src/lib/ui/sidebar-items.ts` already lists USERS for ADMIN role; if the
     existing item points to anything other than `/users`, fix the path. No new code in this
     iter on sidebar-items.

6. **Tests `frontend/tests/users.spec.ts`** (new file):
   - **Existing test impact**:
     - `dev-login.spec.ts` (iter 079): uses testid + role selectors throughout — no break.
     - `role-rendering.spec.ts`: spot-check for any redirect-from-/users assertion that
       expects a 404 or "page not found"; if present, update to expect either the page
       (ADMIN) or `/dashboard` redirect (non-ADMIN). The redirect-from-/vendors precedent in
       this file at iter 089 is the model.
     - All other specs: no break expected. The page is brand new; the only shared surfaces
       are `api.ts` (append-only), `permissions.ts` (append-only), `types.ts` (append-only),
       sidebar-items.ts (no change).
   - New permanent specs (selector policy: getByRole / getByLabel / getByTestId only):
     - Page mount under AppShell (testid `app-shell` or whichever AppShell exposes).
     - Non-ADMIN role redirects to `/dashboard` (mock `/api/v1/me` as VENDOR or SM).
     - ADMIN list rendering: at least 3 users with mixed status renders rows with the right
       status pills.
     - Status filter narrows: select PENDING, only PENDING rows visible.
     - Role filter narrows: select VENDOR, only VENDOR rows visible.
     - Empty state on filter-with-no-match.
     - Error+retry on list fetch failure.
     - Invite flow: open modal, fill form, submit → modal closes, `InviteLinkPanel` appears
       with URL + Copy + Dismiss, list refetched (new row visible).
     - Invite validation: empty username blocks submit.
     - Invite 409 on duplicate username renders inline error.
     - Invite vendor_id field appears only when role=VENDOR.
     - Edit flow: open modal, change display_name, submit → modal closes, row updates.
     - Edit blank-email path: email field empty → PATCH body `email: null`, row email cell
       reads as empty.
     - Deactivate flow on ACTIVE user: confirm modal → submit → row pill flips to gray
       INACTIVE, action button swaps to Reactivate.
     - Deactivate self-self-self-409: ADMIN deactivates their own row → inline 409 message.
     - Reactivate flow on INACTIVE user: confirm → row pill flips to green ACTIVE.
     - Reset-credentials flow on ACTIVE user: confirm → InviteLinkPanel renders with new
       URL, row pill flips to PENDING.
     - Reissue-invite flow on PENDING user: confirm → InviteLinkPanel renders with new URL,
       row stays PENDING.
     - Reset-credentials hidden on PENDING (the right call is reissue-invite).
     - Reissue-invite hidden on ACTIVE / INACTIVE.
     - Mobile (390px viewport): `user-table-mobile` cards visible; `user-table-desktop` not
       visible. Filter panel collapses behind a "Filters" trigger (mirror of
       `VendorListFilters`).
   - Mock the 8 backend endpoints in a `setupUsersPage` helper at the top of the spec.

7. Run `make test-browser`; confirm 357 → 380+ pass. No backend changes — `make test-backend`
   should be unchanged.

## Decisions

- **Hand-roll modals, do not introduce a Modal primitive in this iter.** Every existing
  modal in the codebase is hand-rolled with the same `<dialog>` / `role="dialog"` +
  `aria-labelledby` shape (iter 081, 084, 087, 088). Promoting to a primitive is the right
  move once 5+ consumers exist and the variance is low enough to abstract — that is its own
  cleanup iter. Three new modals here (invite, edit, confirm) brings the total consumers to
  6+; primitive promotion is a follow-up.

- **Status-aware action visibility, not status-aware disabling.** Showing a disabled
  "Reissue invite" button on an ACTIVE user is noise — the action is not applicable. Hide
  rather than disable. Same model as iter 077's `PoActionRail` and iter 089's
  `VendorListTable` action swap.

- **Self-deactivate guard surfaces server message, not pre-emptive hide.** Hiding the
  Deactivate button on the calling admin's own row would force the UI to know which row is
  "self", which leaks the session identity into the table. The backend already 409s with a
  clear message ("cannot deactivate yourself"); render that inline. Same applies to the
  last-admin guard.

- **One `InviteLinkPanel` for all three token-returning paths.** Invite, reset-credentials,
  and reissue-invite all return `{user, invite_token}`. Distinguishing them in the UI by
  using three different panels is noise; one panel with one copy variant per source is
  enough. The panel's caption text varies ("New invite link", "Reset complete — new invite
  link", "Reissue complete — new invite link") but the affordances do not.

- **`?token=` URL composition uses `window.location.origin`.** The backend returns the raw
  token; the frontend assembles the URL. This makes the link work regardless of which host
  ADMIN is on (dev / staging / prod) without backend coupling to the frontend's URL scheme.

## Risks

- **Backend invite endpoint shape may not match `InviteUserInput`.** Read
  `backend/src/routers/auth.py` at the `/invite` handler and confirm the request body shape
  before writing the api.ts client. The schema is `{username, role, display_name, email,
  vendor_id}` per iter 095, but verify — getting the body wrong is a 422 with a
  hard-to-debug message.

- **`is()` helper in `permissions.ts` may already encode ADMIN bypass for every callee.**
  Adding `canManageUsers` should not double-bypass. Read the helper before adding.

- **`User` type in `types.ts` may already include email** (it should; the doc says it is
  missing but always verify before writing). If yes, skip that step.

- **Sidebar item link target.** If the existing `USERS` slot in `sidebar-items.ts` links to
  something other than `/users` (e.g. `/admin/users`), the route at `(nexus)/users/` will be
  unreachable from the sidebar. Verify and align.

- **`role-rendering.spec.ts` may have a redirect-on-/users assertion already.** Earlier iters
  may have asserted "VENDOR navigates to /users gets redirected" against a 404. With the
  page now real, the assertion needs to land on `/dashboard` (the redirect target). Search
  this file before running tests.

- **Playwright port collision with iter 101 worktree running in parallel.** If both run
  `make test-browser` simultaneously, the vite dev server port may collide. If the test
  command fails with EADDRINUSE, set `PORT` env var or run sequentially.

## Notes

`User` type at `frontend/src/lib/types.ts` did not have `email` (the doc was right; the
risk note hedged). One-line addition. `UserRole` and `UserStatus` literal unions already
existed; reused. The `email`-required change rippled into pre-existing `User`-typed test
fixtures (`invoice-detail.spec.ts`, `invoice-list.spec.ts`, `shipment-detail.spec.ts`)
and one demo route (`ui-demo/po-documents`) — added `email: null` to each. The
`po-detail.spec.ts`, `po-documents.spec.ts`, and `nexus-dashboard.spec.ts` errors that
flag `vendor_id: 'string'` against `vendor_id: null` are the pre-existing `typeof
SM_USER` literal-narrowing bug iter 086 noted; not in scope.

`role-rendering.spec.ts` had no `/users` redirect assertion. No update needed.

`UserRowAction` type extracted to `frontend/src/lib/user/user-row-actions.ts` rather
than re-exported from the `.svelte` table (Svelte type re-exports are not standard in
this codebase).

Reactivate skips the confirm modal — single-button reactivation, no destructive
consequence, mirrors `VendorListTable`'s reactivate-on-click. Other three (deactivate,
reset, reissue) go through `UserActionConfirm`. Self-deactivate 409 surfaces inline in
the confirm modal as designed.

`make test-browser` would normally exercise the new specs against the parent worktree's
vite dev server on port 5174. That server runs `main` (iter 099), which lacks the
`/users` route, so it cannot serve the new specs. Started a separate vite on port 5176
pointing at this worktree, ran the full suite via a transient `playwright.config.local.ts`
(deleted after the run; not committed). Result: 378 passed (baseline 357 + 21 new),
0 failures. The shared `playwright.config.ts` was not modified.

21 new permanent specs in `frontend/tests/users.spec.ts`. No backend changes.

No new domain terms. `InviteLinkPanel` and `UserActionConfirm` are component names, not
vocabulary.
