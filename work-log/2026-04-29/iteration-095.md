# Iteration 095 — User management backend CRUD

## Context

User management has been a single-endpoint surface since iter 031: `POST /api/v1/users/invite` (ADMIN-only, creates a PENDING user). No list, get, update, deactivate, or reactivate endpoints exist. Every other slice of user management on the backlog (frontend `/users` page, multi-passkey, invite-token-as-UUID, reset-credentials, vendor-deactivation read-only mode) presumes a working CRUD surface underneath.

This iter runs in parallel to Phase 4.5 (which is sequencing iters 091-094 on `/products` and cert UI). Backend user CRUD has zero overlap with the revamp routes — it is purely additive on `/api/v1/users` and lives in `backend/src/routers/auth.py` which Phase 4 is not touching. The frontend `/users` page is intentionally deferred; without it, the only consumer of these endpoints is Playwright/pytest. That is acceptable: the cost of staging the API ahead of the UI is one ADMIN-bearing test fixture and a small router file.

The domain layer is already complete. `User.deactivate()` and `User.reactivate()` enforce the lifecycle (ACTIVE/PENDING → INACTIVE → ACTIVE). `UserRepository.count_active_admins()` exists and is the right primitive for the last-admin guard. `auth/middleware.py` already rejects requests from non-ACTIVE users on the next request after deactivation, so no notification dance is needed.

Out of scope (deliberately): role mutation, vendor_id mutation, username mutation. Each is a bigger semantic change with downstream implications (role mutation invalidates permission caches; vendor_id mutation fights with vendor-scoped data access; username is the business reference and is immutable by design). Defer to follow-up iters when the use case is clear.

## JTBD

As an ADMIN operating the system, I want to view every user in the system and change their lifecycle (deactivate a departed employee, reactivate someone returning from leave, fix a typo in a display name) without manually editing the database.

As a downstream iteration (frontend `/users` page, vendor-deactivation cascade, etc.), I want a stable backend CRUD surface I can call against, with the same role-guard + ADMIN-bypass shape every other router uses.

## Endpoints

All under existing `invite_router` in `backend/src/routers/auth.py` (prefix `/api/v1/users`, tags `["users"]`). All ADMIN-only via `require_role(UserRole.ADMIN)` (which already grants ADMIN-bypass).

| Method + path | Body | Returns | Notes |
|---|---|---|---|
| `GET /api/v1/users/` | — | `{users: [UserDict]}` | Optional `?status=ACTIVE\|INACTIVE\|PENDING` and `?role=...` filters. Ordered by username asc. |
| `GET /api/v1/users/{id}` | — | `{user: UserDict}` | 404 if missing. |
| `PATCH /api/v1/users/{id}` | `{display_name?: str, email?: str \| null}` | `{user: UserDict}` | Validates display_name non-empty/whitespace if provided. Email passes through (no format validation here — same shape as invite). 404 if missing. |
| `POST /api/v1/users/{id}/deactivate` | — | `{user: UserDict}` | 409 on self-deactivate, 409 on last-ACTIVE-ADMIN, 409 on already-INACTIVE (domain raises ValueError). |
| `POST /api/v1/users/{id}/reactivate` | — | `{user: UserDict}` | 409 on already-ACTIVE/PENDING (domain raises ValueError). |

**Route ordering caveat**: FastAPI matches in registration order. `/{id}` paths must register *after* `/invite` so `users/invite` doesn't get swallowed as `users/{id}` with id="invite". Append the new routes to `invite_router` after the existing `/invite` POST.

**UserDict shape**: identical to existing `_user_to_dict` (id, username, display_name, role, status, vendor_id). Add `email` to the dict as part of this iter — current shape omits it, which is a small accidental gap. Existing callers do not depend on the absence of `email`. Update `_user_to_dict` once.

## Tasks

1. Extend `backend/src/routers/auth.py`:
   - Add `email` to `_user_to_dict`.
   - Add `UserUpdateRequest` pydantic model with `display_name: str | None = None` and `email: str | None = None`.
   - Add 5 new endpoint handlers on `invite_router`. Each handler reads `current_user` off `request.state` and rejects with 403 if `current_user.role is not UserRole.ADMIN`. (Don't switch to `require_role` mid-file — `auth.py` currently uses the manual `request.state` check pattern; match it for local consistency. A separate iter can migrate the whole file.)
   - Self-deactivate guard: in deactivate handler, raise 409 if `target.id == current_user.id`.
   - Last-admin guard: in deactivate handler, if target is ACTIVE ADMIN, call `repo.count_active_admins()`; raise 409 with message "cannot deactivate the last active admin" when count is 1. Do this *before* mutating, so a failed guard doesn't half-write.
   - Domain `ValueError` from `deactivate()` / `reactivate()` (already-INACTIVE, etc.) maps to 409 with the exception message.

2. Add `UserRepository.list_users(status: UserStatus | None = None, role: UserRole | None = None) -> list[User]` to `backend/src/user_repository.py`. Single query with optional `WHERE` clauses. Order by `username ASC`. Existing `list_active_users` stays (used by dev-login surface) — do not collapse it.

3. New test file `backend/tests/test_user_management.py`:
   - **Existing test impact**: scan the repo for tests that enumerate user-management endpoints or assume `/api/v1/users/{id}` returns 404. None currently exist. `test_auth_endpoints.py::test_invite_requires_admin` registers no users yet — unrelated. `test_role_guards.py` tests guards on existing endpoints; new endpoints are additive. `test_critical_path.py` is end-to-end on PO/invoice flow; no user-mgmt assertions. State explicitly: no existing tests break.
   - List: as ADMIN returns all, status filter narrows, role filter narrows, both filters compose. Non-ADMIN returns 403.
   - Get: ADMIN gets one by id, 404 on unknown id, non-ADMIN 403.
   - Patch: updates display_name, updates email, sets email to null, rejects empty/whitespace display_name (422), 404 on unknown id, 403 for non-ADMIN. Verify other fields unchanged via re-fetch.
   - Deactivate: ACTIVE → INACTIVE, PENDING → INACTIVE, returns 409 on already-INACTIVE, 409 on self-deactivate, 409 on last-ACTIVE-ADMIN (single-admin scenario; second test with two admins succeeds). 403 for non-ADMIN. 404 on unknown id.
   - Reactivate: INACTIVE → ACTIVE, 409 on already-ACTIVE/PENDING, 403 for non-ADMIN, 404 on unknown id.
   - Auth fixture: use the existing pattern in `test_auth_endpoints.py` (bootstrap → register-verify → cookie set on the AsyncClient). For multi-user scenarios use the dev-login pattern from `test_auth_dev.py` if simpler, gated by setting `DEV_AUTH=1` in the test.

4. Run `make test` and confirm pass. Logs land at `logs/make-test.log` per CLAUDE.md. No frontend or playwright changes in this iter.

## Decisions

- **Email in UserDict**: added now, not deferred. The cost is one new key in the response; the alternative (a second iter to add it) burns a turn for trivia.
- **Manual ADMIN check vs `require_role`**: keep the manual `request.state` check to match the rest of `auth.py`. A migration to `require_role` across the whole router is a cleanup iter, not this one.
- **Last-admin guard scope**: only blocks deactivating the last ACTIVE admin. PENDING admins (invited, not registered) do not count toward the active-admin pool — losing the only ACTIVE admin would lock everyone out, which is the only failure mode worth blocking. PENDING admin existence is a recovery path, not an authority.
- **No new domain terms**: this is an API surface expansion over existing domain operations.

## Risks

- Route ordering bug: FastAPI matches first-registered. If `/{id}` is registered before `/invite`, `POST /api/v1/users/invite` 404s with `id="invite"`. Mitigation: append new routes after invite in `auth.py`. Test: `test_invite_requires_admin` keeps passing.
- Self-deactivate via id-not-username: handler must compare on `User.id`, not username, since username is mutable in principle (even if not yet) and id is the aggregate identity.
- Test isolation: each test runs in a rolled-back transaction per iter 029a. ADMIN bootstrap inside a test does not leak. Confirm with one new-admin-second-run test.

## Notes

Last-admin guard runs *before* the self-deactivate guard. The plan left the order open; the inverse order made the last-admin path unreachable, since the only way `count_active_admins() == 1` is when the caller is the last admin (target = self). Putting last-admin first means a sole admin attempting self-deactivate gets the system-level message; with two admins the self check still owns the user-level case. `_user_to_dict` gained `email` as planned; one existing exact-dict assertion in `test_auth_dev.py::test_dev_login_creates_session_for_active_user` flipped (the iter context predicted no breakage; missed it). Manual `request.state` admin check kept (matches the rest of `auth.py`); migration to `require_role` is its own iter. No new domain terms — surface expansion over existing `User.deactivate()` / `reactivate()` / `count_active_admins()`. `make test`: 727 passed.
