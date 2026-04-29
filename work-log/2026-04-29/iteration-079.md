# Iteration 079 — Dev quick-login (one-click session for seeded users)

## Context

Local development requires WebAuthn passkey auth to reach any non-public route. Passkeys bind to the device that registered them, so switching machines, clearing browser data, or wanting to test role × status surfaces across the six seeded users (alice/bob/carol/dave/erin/frank — see [backend/src/seed.py](backend/src/seed.py)) requires re-registering credentials and remembering usernames. This is friction during Phase 4 visual verification, where the natural workflow is "open the page as SM, then again as VENDOR, then as PROCUREMENT_MANAGER" within minutes.

The login page lives at [frontend/src/routes/login/+page.svelte](frontend/src/routes/login/+page.svelte) and the auth router lives at [backend/src/routers/auth.py](backend/src/routers/auth.py). Session creation is centralized at [backend/src/auth/session.py](backend/src/auth/session.py) `create_session_cookie`; both bootstrap and login flows call `_set_session_cookie` already.

## JTBD

When I am developing locally, I want one click per seeded user on the login page to start a session as that user, so I can verify role × status surfaces without re-running WebAuthn or remembering usernames. In production the surface must be invisible: the endpoint returns 404 and the login page renders the existing passkey form unchanged.

## Tasks

1. Backend: add `POST /api/v1/auth/dev-login` to [backend/src/routers/auth.py](backend/src/routers/auth.py). Request body `{username: str}`. Behavior:
   - If env var `DEV_AUTH` is unset or not equal to `"1"`, raise `HTTPException(404)` with detail `"Not found"` (matching FastAPI's default 404 shape so the endpoint is indistinguishable from non-existent).
   - Look up the user by username via `UserRepository.get_by_username`.
   - If the user is not found or status is not `ACTIVE`, raise `HTTPException(404, "User not found")`.
   - On success, call `_set_session_cookie(response, user.id)` and return `_user_to_dict(user)`.
2. Backend: add `GET /api/v1/auth/dev-users` to the same router. Behavior:
   - If `DEV_AUTH` is unset or not `"1"`, raise `HTTPException(404)`.
   - Returns `[{username, display_name, role}]` for all `ACTIVE` users via a new `UserRepository.list_active_users` method (or reuse an existing list method if one exists). Order alphabetically by username for stable rendering.
   - Includes vendor users alongside SM/ADMIN since dev verification spans all roles.
3. Backend: write the env-var check as a single helper `_dev_auth_enabled() -> bool` at the top of the auth router so the gate is explicit in one place.
4. Frontend: add `getDevUsers()` and `devLogin(username)` to [frontend/src/lib/auth.ts](frontend/src/lib/auth.ts) calling the two new endpoints. `getDevUsers` swallows 404 and returns `null` so the login page can decide whether to render the quick-login row.
5. Frontend: in [frontend/src/routes/login/+page.svelte](frontend/src/routes/login/+page.svelte) call `getDevUsers()` once on mount. If the response is `null`, render only the existing passkey form. If the response is an array, render a "Dev quick-login" section below the existing form with one button per user labelled `{display_name} ({role})`. Click triggers `devLogin(username)` then redirects (same redirect logic as the passkey path).
6. Frontend: dev quick-login buttons use the existing `Button` primitive at [frontend/src/lib/ui/Button.svelte](frontend/src/lib/ui/Button.svelte) so they pick up the design tokens already loaded on the login route.
7. Configuration: document the `DEV_AUTH=1` env var in [backend/README.md](backend/README.md) under a "Dev shortcuts" subsection. State that the flag must never be set in production.
8. DDD vocab: no new domain terms emerge; this iter is dev-tooling only.

## Tests

### Existing test impact

- Backend pytest auth tests at [backend/tests/test_auth.py](backend/tests/test_auth.py) (assuming this file exists; if not, tests live alongside other auth tests) — unaffected by this iter because the new endpoints are gated by an env var that is not set in pytest. The existing bootstrap, register, and login flows are untouched.
- Frontend Playwright tests under [frontend/tests/](frontend/tests/) — most specs mock `/auth/me` directly and never hit the login page. The two specs that do touch login ([frontend/tests/auth.spec.ts](frontend/tests/auth.spec.ts) if it exists; otherwise the bootstrap flow tested in `auth-bootstrap.spec.ts`) need the new `getDevUsers` call mocked out (return 404) so they do not see the quick-login UI. Expected impact: 0-2 tests need a `page.route('**/api/v1/auth/dev-users', ...)` mock added.

### Permanent — backend

1. `test_auth_dev_login.py::dev_login returns 404 when DEV_AUTH unset` — call `POST /api/v1/auth/dev-login` with `{"username": "alice"}` and `DEV_AUTH` unset; assert response status is 404.
2. `test_auth_dev_login.py::dev_login returns 404 when DEV_AUTH not equal to 1` — set `DEV_AUTH=0`, call the endpoint, assert 404.
3. `test_auth_dev_login.py::dev_login creates session for active user` — set `DEV_AUTH=1`, seed user alice (ADMIN, ACTIVE), call endpoint with `{"username": "alice"}`; assert response 200, body matches `_user_to_dict(alice)`, response sets the `tt_session` cookie. Then call `GET /api/v1/auth/me` with that cookie and assert it returns alice.
4. `test_auth_dev_login.py::dev_login rejects unknown username` — set `DEV_AUTH=1`, call endpoint with `{"username": "ghost"}`; assert 404.
5. `test_auth_dev_login.py::dev_login rejects inactive user` — seed user with `status=PENDING`, call endpoint, assert 404.
6. `test_auth_dev_users.py::dev_users returns 404 when flag unset` — call `GET /api/v1/auth/dev-users` with no `DEV_AUTH`; assert 404.
7. `test_auth_dev_users.py::dev_users lists active users alphabetically` — set `DEV_AUTH=1`, seed all six users plus one PENDING user; assert response is the six ACTIVE users sorted by username, PENDING user excluded.

### Permanent — frontend

1. `dev-login.spec.ts::quick-login row hidden when dev-users endpoint returns 404` — mock `/api/v1/auth/dev-users` with 404; load `/login`; assert no element with `data-testid="dev-login-row"` appears and the existing passkey form still renders.
2. `dev-login.spec.ts::quick-login row renders one button per user when dev-users returns a list` — mock the endpoint with the six seeded users; assert `data-testid="dev-login-row"` is visible and `data-testid="dev-login-{username}"` exists for each of alice, bob, carol, dave, erin, frank.
3. `dev-login.spec.ts::clicking a quick-login button creates a session and redirects to dashboard` — mock dev-users + `/api/v1/auth/dev-login` (returns user payload); click `data-testid="dev-login-carol"`; assert `/auth/dev-login` was called with `{username: "carol"}` and the page navigated to `/dashboard`.
4. `dev-login.spec.ts::quick-login honors the redirect query param` — same as #3 but load `/login?redirect=%2Fpo%2F123`; assert post-click navigation lands on `/po/123`.

### Scratch

None. The new endpoints are simple gate + lookup; the eleven permanent tests cover the env-gate, the role × status surfacing, and the redirect flow.

## Notes

(populated at iteration close)
