# Iteration 096 — Invite token (UUID) replaces username on registration link

## Context

Today the registration URL is `/register?username=<name>`. Anyone who knows a PENDING user's username can complete registration on their behalf — usernames are guessable (typically email-local-part or the obvious handle), and the backend `POST /api/v1/auth/register/options` accepts a raw username. The only thing standing between an attacker and a stolen account is "did the legitimate invitee click first." Iter 030 shipped the username-keyed flow as the smallest path to working passkeys; the security gap was logged at the time and has lived on the backlog ever since.

This iter runs as a parallel-track follow-up to iter 095. It is backend-and-auth-frontend only and has zero overlap with Phase 4.5 Tier 4 (cert UI fold-in), which is in flight on a separate branch and only touches `(nexus)/products/*`. The `/register` and `/setup` routes are pre-revamp and are explicitly *not* part of any Phase 4 tier — Phase 4's auth-page revamp is its own future iter.

The shape of the change is small and contained: the registration link becomes `/register?token=<uuid>`, where `<uuid>` is a per-invite secret stored on `users.invite_token`. The token is generated when an invite (or bootstrap) creates the PENDING user, returned to the inviter in the response so they can build the link, consumed by the registration handshake (both `options` and `verify` keyed off the token), and cleared as part of activation. Username never leaves the server during registration.

The bootstrap flow is structurally identical — the very first ADMIN is also a PENDING user the first time around, so `POST /api/v1/auth/bootstrap` already creates a User via `User.invite(...)`. Bootstrap returns `options` (and now `invite_token`) so `/setup` can redirect to `/register?token=...` rather than `/register?username=...`.

The domain layer needs the smallest possible change: `User.invite()` allocates an `invite_token` alongside `id`, and `User.activate()` clears it (single point of truth for "registration complete → token spent"). Repository persists it (ALTER TABLE column add) and exposes a `get_by_invite_token` lookup. Existing PENDING users are backfilled with a fresh token at `init_db` time so no manual data step is required during deploy.

## JTBD

As an ADMIN inviting a new user, I want the registration link I share to carry an unguessable secret rather than the user's username, so a bystander who knows the team's naming convention cannot complete registration on the invitee's behalf.

As an invited user opening the link, I want the registration UX to be identical to today — click link, click Register passkey, get a session — without having to type my username or know it ahead of time.

As a downstream iter (welcome-email-on-invite, stale-PENDING-cleanup, multi-passkey-recovery, /users frontend page), I want a stable invite_token field on the user record I can attach my behavior to.

## Endpoints

| Method + path | Body change | Returns |
|---|---|---|
| `POST /api/v1/users/invite` | unchanged | `{user, invite_token}` (was `{user}`) |
| `POST /api/v1/auth/bootstrap` | unchanged | `{options, user, invite_token}` (was `{options, user}`) |
| `POST /api/v1/auth/register/options` | `{token}` (was `{username}`) | `{options, user}` |
| `POST /api/v1/auth/register/verify` | `{credential, token}` (was `{credential, username}`) | `{user}` (sets session cookie, clears `invite_token`) |
| `POST /api/v1/auth/login/options` | unchanged | unchanged |
| `POST /api/v1/auth/login/verify` | unchanged | unchanged |

Login flow is untouched — it has always been keyed on username and that is fine, login does not leak account state to anyone who does not already hold a credential.

`invite_token` is **never** returned in any other surface — `_user_to_dict` does not expose it, the new `GET /api/v1/users/...` endpoints from iter 095 do not return it, and `/api/v1/auth/me` does not return it. It exists only on the response to invite/bootstrap (so the inviter can build the link) and is consumed only by the two register endpoints.

## Tasks

1. Schema + repo:
   - Add `invite_token TEXT` to the users table (nullable, no unique constraint at the column — uniqueness is enforced by UUID generation).
   - Idempotent `ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_token TEXT` in `backend/src/schema.py:init_db`, alongside the existing `email` column add.
   - Backfill: after the ALTER, `UPDATE users SET invite_token = gen_random_uuid()::text WHERE status = 'PENDING' AND invite_token IS NULL` so existing PENDING users from prior runs / seeds receive a fresh token. (Postgres `gen_random_uuid()` is available without extension on PG 13+.)
   - `UserRepository.save` persists `invite_token` (both INSERT and UPDATE branches).
   - `UserRepository._reconstruct` reads it back (nullable).
   - New `UserRepository.get_by_invite_token(token: str) -> User | None` — single fetch, exact match.

2. Domain `backend/src/domain/user.py`:
   - `User.__init__` gains `invite_token: str | None = None`.
   - `User.invite(...)` generates `invite_token=str(uuid4())` alongside `id`.
   - `User.create(...)` does NOT set an invite_token — `create` is for already-active users (test fixtures, dev-login seeding). `invite_token` stays None.
   - `User.activate()` clears `invite_token` to None as part of the PENDING → ACTIVE transition.
   - No new ValueError paths — the token is internal data, not a domain invariant.

3. Routers `backend/src/routers/auth.py`:
   - `bootstrap` returns `{options, user, invite_token}`.
   - `invite_user` returns `{user, invite_token}`.
   - `register_options` request model becomes `TokenRequest(BaseModel): token: str`. Look up via `repo.get_by_invite_token(body.token)`. 404 on miss. Reject if user is not PENDING (already-registered guard preserved). Reject if user already has credentials (preserved).
   - `register_verify` reads `body.get("token")` instead of `body.get("username")`. Look up via `repo.get_by_invite_token`. 404 on miss. After `verify_registration` succeeds and `save_credential` lands, call `user.activate()` — which now also clears `invite_token` — and `repo.save(user)`. Set session cookie.
   - The 400 "Missing credential or username" in `register_verify` becomes "Missing credential or token".
   - `_user_to_dict` does NOT change — `invite_token` stays out of the standard user dict (matches `email` precedent prior to iter 095, and stronger: this is a secret, not a profile field).

4. Frontend `frontend/src/lib/auth.ts`:
   - `registerOptions(token: string)` (was `username: string`) — body `{token}`.
   - `registerVerify(token: string, credential: ...)` (was `username, credential`) — body `{token, credential}`.
   - Type `RegisterOptionsResponse` unchanged (still `{options, user}`).
   - Bootstrap response type gains `invite_token: string` so `/setup` can read it.

5. Frontend pages:
   - `frontend/src/routes/register/+page.svelte`: read `token` from `page.url.searchParams` instead of `username`. `loadState === 'invalid'` when token is missing. `registerOptions(token)` and `registerVerify(token, credential)` calls. Display name still comes from the `user` object the options endpoint returns. Copy unchanged.
   - `frontend/src/routes/setup/+page.svelte`: after bootstrap success, navigate to `/register?token=${invite_token}` (was `/register?username=${user.username}`). The bootstrap response now carries `invite_token` directly, so no second fetch.
   - Login page is untouched.

6. Seed `backend/src/seed.py`:
   - Existing `User.invite(...)` calls automatically pick up the new generated token via the domain change.
   - No seed-script behavior change required, but the seed log at end-of-run can optionally print the token for the seeded PENDING users so dev demos can copy-paste a register link. Out of scope unless trivial.

7. Tests:
   - **Existing test impact** (this is an iteration-doc requirement; the iter 095 retrospective showed I miss this when I am too quick).
     - `backend/tests/test_auth_endpoints.py::test_bootstrap_creates_admin` — currently asserts `result["user"]["role"] == "ADMIN"` etc. The response now also has `invite_token`. The existing assertions are positive (key presence), so they pass; but the test does not currently assert *absence* of unexpected keys. **No break.**
     - `backend/tests/test_auth_endpoints.py::test_register_verify_activates_user_and_sets_session` — calls the helper `_register_verify(client, "admin")` which sends `{"username": "admin", "credential": ...}`. **Breaks** because the verify endpoint will reject `username` and require `token`. Fix the helper to read the token from the prior bootstrap response and send `{"token": <uuid>, "credential": ...}`.
     - `backend/tests/test_auth_endpoints.py::test_register_options_unknown_user_returns_404` — sends `{"username": "nobody"}`. **Breaks** because the body shape changed. Replace with a `test_register_options_unknown_token_returns_404` that sends `{"token": "<random-uuid>"}` and asserts 404.
     - `backend/tests/test_auth_endpoints.py::test_logout_clears_session` — chains bootstrap + register_verify via the helpers above. **Breaks transitively** when the helper changes; fixing the helper fixes this test.
     - `backend/tests/test_auth_endpoints.py::test_login_options_pending_user_returns_403` — only does bootstrap (not verify). **No break.**
     - `backend/tests/test_critical_path.py` — read this file as part of this task and update the registration helpers there too if it does the bootstrap → register-verify dance. (The iter 095 context noted it does end-to-end PO/invoice flow; spot-check before assuming no break.)
     - `backend/tests/conftest.py::authenticated_client` — uses `User.create(...)` (active user, no invite flow). **No break.**
     - `backend/tests/test_user_management.py` (iter 095) — uses dev-login + `_seed_user` via repo override. **No break.**
     - `frontend/tests/auth-flow.spec.ts` — Playwright auth flow. Check whether it walks the register screen with `?username=`; if so, migrate to `?token=`. If it stubs `/api/v1/auth/register/options` it stays valid because the body shape is internal to the call.
     - `frontend/tests/dev-login.spec.ts` — does not touch register flow. **No break.**
   - **New permanent backend tests** (`backend/tests/test_invite_token.py`):
     - `test_invite_returns_token` — invite returns `invite_token` matching uuid4 shape; the user dict does not contain it (separation-of-secrets check).
     - `test_bootstrap_returns_token` — bootstrap returns `invite_token`.
     - `test_register_options_by_token_works` — bootstrap → use returned token → `register/options` with `{token}` returns `{options, user}` matching the bootstrapped admin.
     - `test_register_options_unknown_token_returns_404` — random token, 404.
     - `test_register_options_already_registered_returns_409` — bootstrap → register-verify → call options again with the (now-cleared) original token → 404 (token cleared) AND with a fresh invite for a second user that has had its credential created via direct repo manipulation → 409. The ergonomic case is just "token cleared after activate → 404 on reuse" which proves the consume-once contract.
     - `test_register_verify_clears_token` — bootstrap → register-verify → fetch the user from repo and assert `invite_token is None`.
     - `test_register_verify_unknown_token_returns_404` — random token, 404.
     - `test_register_options_username_no_longer_accepted` — sending `{"username": "admin"}` returns 422 (pydantic validation) since the model now requires `token`. Locks the username path closed.
   - **No new frontend tests** strictly required if the existing `auth-flow.spec.ts` is migrated cleanly. Add one positive `?token=` register spec if `auth-flow.spec.ts` does not already cover it.

8. Run `make test` and confirm pass. Logs land at `logs/make-test.log` per CLAUDE.md. Then `make test-browser` if frontend specs were touched.

## Decisions

- **UUID v4 over signed token**: A signed token (itsdangerous) carries timestamp metadata and is what `_serializer` already uses for challenge cookies. UUID v4 is simpler, has zero binding to a serializer config, and makes "consume once and clear" a one-line UPDATE. Token expiry is a separate concern logged on the backlog as "stale PENDING user cleanup" and is the right primitive (a periodic sweep), not per-token TTL.
- **Backfill at `init_db` rather than a one-shot migration script**: This codebase uses idempotent ALTER + UPDATE in `init_db` per the prior `email` column precedent (iter 060) and the line-items status backfill (iter 056). Matching that pattern keeps the deploy story unchanged.
- **Verify endpoint takes token, not (token + username)**: Sending both is redundant — the token already identifies the user. Sending only username with a token-gate would be a half-migration.
- **`invite_token` does not appear in `_user_to_dict`**: Even ADMIN-listing the user roster should not see invite tokens of other PENDING users, because the listing surface is broader than the inviter. The token leaks only at the point of invite creation and goes nowhere else.
- **No re-roll endpoint in this iter**: "ADMIN regenerates an invite link" is a real follow-up (and pairs with `POST /users/{id}/reset-credentials` from the backlog) but is its own iter. Today, if the link is lost, the ADMIN deactivates and re-invites, or waits for the iter that adds a re-roll method.
- **No expiry, no rate-limiting**: Both are reasonable improvements. Both are out of scope here. The iter focus is replacing the guessable-username vector; expiry and rate-limiting are layered defenses.
- **Domain `User.activate()` clears the token**: Single source of truth for "this person has registered." If a future iter adds a non-WebAuthn activation path it still flows through `activate()` and the token-clear is automatic.

## Risks

- **Existing PENDING users in dev databases without tokens**: The `init_db` backfill UPDATE handles this. If a deployment's PG user lacks `gen_random_uuid` (older PG, locked-down extensions), the UPDATE fails. Mitigation: use `md5(random()::text || clock_timestamp()::text)::uuid` as a fallback if needed; or require PG 13+ in deploy notes. Today the local stack runs PG 16, so `gen_random_uuid` is available.
- **Frontend setup-page change**: `/setup` redirects to `/register` after bootstrap. If the bootstrap response shape change misses a frontend caller, the redirect URL becomes `/register?token=undefined` and the register page shows "Invalid invite link." Catch in the test that walks setup → register, not at runtime.
- **Test helper churn**: The `_register_verify(client, username)` helper in `test_auth_endpoints.py` is used by three tests. Migrating it once at the helper level is the small fix; resist the temptation to inline the new shape into each test.
- **invite_token uniqueness**: UUID v4 collisions are not a real risk (2^122 space). No DB-level UNIQUE constraint needed; a stray duplicate would surface at lookup as a 500 (multiple-rows fetch), which is loud enough to detect if the impossible happens.
- **Token in URL → browser history / referrer leak**: A token in a URL is a one-time secret in the browser history. This is the same exposure as a password reset link and is the standard accepted tradeoff for invite-by-link flows. Mitigation lives in the consume-once design (token clears on first successful activate).

## Notes

Token clearing lives on `User.activate()` rather than the verify router, so any future activation path (non-WebAuthn admin override, recovery flow) inherits the consume-once contract for free. Login flow stayed on username — login does not leak account state to anyone who lacks credentials, and changing it would have churned every test fixture for no security gain. The legacy `{"username": ...}` body shape on `register/options` is now closed by pydantic's strict-required `TokenRequest`; deliberately verified by a permanent 422 test rather than a soft deprecation. Setup-page bootstrap re-uses the token from the same response (no separate fetch), so the very-first-admin flow still completes in a single round trip. `make test`: 738 passed (+11 new). `make test-browser`: 350 passed.
