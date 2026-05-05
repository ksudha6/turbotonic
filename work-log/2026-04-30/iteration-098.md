# Iteration 098 — Reset credentials + reissue invite

## Context

Two operational gaps remain after iters 095 and 096:

1. **Lost device.** A user whose only passkey is on a broken laptop has no recovery path. ADMIN can `deactivate` but cannot revoke passkey rows, so the `invite + register` two-step won't work — the user row is INACTIVE (not PENDING) and `webauthn_credentials` rows still point at the broken device.

2. **Lost invite link.** If ADMIN closes the tab after `POST /invite`, the token is gone. The only option today is `deactivate` + a duplicate-username invite, which is impossible if state has accrued under the original user row.

Both use the consume-once `invite_token` machinery from iter 096. The first reverses activation: revoke credentials, drop status to PENDING, mint a fresh token. The second mints a fresh token only. Together these complete the ADMIN ops console (invite, list, get, patch, deactivate, reactivate, reset-credentials, reissue-invite). No frontend in this iter; the only consumer until the `/users` page ships is pytest.

This iter runs in parallel to iter 097 (Phase 4.6 Tier 1 `/shipments/[id]` shell port). Backend-only, no overlap with `/shipments/*`.

## JTBD

As an ADMIN, when a user reports their device is lost, I want a single endpoint that revokes their passkeys and re-issues an invite link, so they can re-register on a new device without me having to delete and re-invite (which loses any state under the original user id).

As an ADMIN, when an invite link goes missing before the user opens it, I want to mint a new link for the same PENDING user without churning the invite row, so I can re-share without polluting the audit trail with a delete-and-re-invite sequence.

As a downstream iter (`/users` frontend page, support tooling), I want stable endpoints I can wire row actions to, so the UI does not need to encode the recovery dance manually.

## Endpoints

| Method + path | Body | Returns | Notes |
|---|---|---|---|
| `POST /api/v1/users/{id}/reset-credentials` | — | `{user, invite_token}` | ADMIN-only. 404 on unknown id. 409 on already-PENDING (reissue-invite is the right call there). Last-active-admin guard fires before applying. Deletes all `webauthn_credentials` rows for the user, sets status to PENDING, allocates a fresh `invite_token`. Allowed on ACTIVE *and* INACTIVE — INACTIVE → PENDING is a valid recovery for someone returning from leave with no working passkey. |
| `POST /api/v1/users/{id}/reissue-invite` | — | `{user, invite_token}` | ADMIN-only. 404 on unknown id. 409 if status is not PENDING (the right call there is `reset-credentials`). Allocates a fresh `invite_token`, leaves everything else untouched. |

Both endpoints return the same shape as `POST /invite` (`{user, invite_token}`) so the frontend can branch by HTTP status alone.

Both endpoints leave the response shape silent on the *old* token — once the user row's `invite_token` is overwritten, the old value is unrecoverable. That is the consume-once contract working as intended.

Self-target rules:
- **`reset-credentials`**: ADMIN may target themselves. The last-active-admin guard already covers the lockout case (single ACTIVE admin trying to drop their own status to PENDING fails with the system-level message). Multi-admin self-reset succeeds and ends the calling session immediately on the next request (the middleware rejects PENDING users from `request.state`). The new invite link is in the response — ADMIN must use a fresh browser to consume it.
- **`reissue-invite`**: not applicable — ADMIN's own row is not PENDING (else they could not be calling this endpoint). 409 fires on the status check.

Route ordering: both routes use `POST /{user_id}/<verb>`, registered after `POST /invite` in `invite_router`. Iter 095 already established this pattern with `deactivate` and `reactivate`.

## Tasks

1. Domain `backend/src/domain/user.py`:
   - `User.reset_credentials()` — raise `ValueError("user is already PENDING")` if `status is UserStatus.PENDING`. Otherwise set `status = UserStatus.PENDING` and `invite_token = str(uuid4())`. The verb is intentionally past-tense in noun form (`reset_credentials` not `revoke_credentials`) to match the lifecycle vocabulary already in `activate / deactivate / reactivate`.
   - `User.reissue_invite()` — raise `ValueError("only PENDING users have an invite to reissue")` if status is not PENDING. Otherwise set `invite_token = str(uuid4())`. Domain does not touch credentials here — there are no credential rows on a PENDING user.
   - Both methods are aggregate-internal mutators; the credential-row deletion is not a domain operation (credentials are a separate aggregate root persisted in `webauthn_credentials`). Repository orchestrates that step, not the User aggregate.

2. Repository `backend/src/user_repository.py`:
   - New `delete_credentials_by_user_id(user_id: str) -> None`. Single `DELETE FROM webauthn_credentials WHERE user_id = $1`. Idempotent (no rows is fine).

3. Router `backend/src/routers/auth.py`:
   - New `POST /{user_id}/reset-credentials` handler on `invite_router`:
     - `_require_admin(request)` (re-uses iter 095 helper)
     - `target = await repo.get_by_id(user_id)`; 404 if None.
     - Last-active-admin guard: identical shape to `deactivate_user` — if `target.role is UserRole.ADMIN and target.status is UserStatus.ACTIVE`, call `repo.count_active_admins()`; raise 409 "cannot reset credentials for the last active admin" when count <= 1. Detail message names the system-level concern, not the user-level one.
     - `target.reset_credentials()` inside a try; map domain `ValueError` to 409 with the message (covers the already-PENDING case).
     - `await repo.delete_credentials_by_user_id(target.id)` *before* `repo.save(target)` so a save-failure leaves credentials intact (less surprising than the inverse: orphan credentials with a PENDING user).
     - Wait, that ordering is wrong — if `delete_credentials_by_user_id` lands and `save(target)` fails, credentials are gone but the user is still ACTIVE. The user can no longer log in (credentials are required by `login/verify`) but the row says they are ACTIVE — confusing. Reverse: call `save(target)` first (status -> PENDING, new token), then delete credentials. If the DELETE fails, the user is PENDING with stale credentials, and `register/options` rejects with "User already has credentials" (existing iter-030 guard). ADMIN sees the failure and can retry — clean recovery. **Order: save then delete.**
     - Return `{"user": _user_to_dict(target), "invite_token": target.invite_token}`.
   - New `POST /{user_id}/reissue-invite` handler on `invite_router`:
     - `_require_admin(request)`
     - `target = await repo.get_by_id(user_id)`; 404 if None.
     - `target.reissue_invite()` inside a try; map domain `ValueError` to 409.
     - `await repo.save(target)`.
     - Return `{"user": _user_to_dict(target), "invite_token": target.invite_token}`.

4. Tests `backend/tests/test_user_recovery.py` (new file):
   - **Existing test impact**:
     - `backend/tests/test_user_management.py` (iter 095): no break — endpoints there are unchanged. The new endpoints are additive on `invite_router`.
     - `backend/tests/test_invite_token.py` (iter 096): no break — bootstrap, invite, and register flows are unchanged. The new endpoints do not modify the existing handlers.
     - `backend/tests/test_auth_endpoints.py`: no break — bootstrap → register-verify → logout helpers untouched.
     - `backend/tests/test_auth_dev.py`: no break — dev-login flow unchanged.
     - `backend/tests/test_critical_path.py`: spot-check before declaring no break, but it is end-to-end on PO/invoice flow and does not touch user lifecycle.
     - `backend/tests/conftest.py::authenticated_client`: uses `User.create()` (active user, no invite_token, no credentials). The fixture is unaffected.
   - reset-credentials:
     - ACTIVE user: status flips to PENDING, new `invite_token` returned, credentials deleted (verify by calling `repo.get_credentials_by_user_id` directly through dep override after the call, expecting `[]`).
     - INACTIVE user: same as ACTIVE — INACTIVE -> PENDING is valid (recovery for returning leave-takers).
     - 409 on already-PENDING (the right call is reissue-invite).
     - 409 on last-active-admin self-reset (single-admin scenario).
     - Multi-admin self-reset succeeds, returns a new token; verify the calling cookie is now bound to a PENDING user (assert `me` returns 401 — middleware rejects PENDING).
     - Returns the new token in the response body; verify the token matches `User.invite_token` after re-fetch.
     - The old invite_token from the original invite is no longer valid (negative test): `register/options` with the original token returns 404. (Strictly: the original token was None on an ACTIVE user, but on a previously-PENDING-and-activated user it was already cleared by `User.activate()`. The interesting case is the user who was reset, then *reset again*: their token from the first reset must not work after the second.)
     - 403 non-ADMIN.
     - 404 unknown id.
     - Login flow is broken after reset: `login/options` with the user's username returns 404 because no credentials remain.
     - The new token works: `register/options` with the new token returns 200; a follow-up register-verify activates the user with a new credential.
   - reissue-invite:
     - PENDING user: new `invite_token` returned, status stays PENDING, no credential rows touched.
     - 409 on ACTIVE.
     - 409 on INACTIVE.
     - The original invite_token is invalidated: `register/options` with the original token returns 404 after reissue.
     - The new token works: `register/options` with the new token returns 200.
     - 403 non-ADMIN.
     - 404 unknown id.
   - Auth fixture: dev-login pattern (`DEV_AUTH=1` + `_seed_user` via dependency-overridden repo) — same as `test_user_management.py` and `test_invite_token.py`. Add a `_seed_active_user_with_credential` helper that runs the bootstrap → register-verify dance with mocked WebAuthn so reset-credentials tests have a target with real credential rows to delete.

5. Run `make test` and confirm pass. Logs at `logs/make-test.log`. No frontend or playwright changes.

## Decisions

- **Two endpoints, not one.** Conflating reset-credentials and reissue-invite into a single "regenerate-invite" endpoint forces the caller to know the user's status before the call — exactly the kind of state-leak that the consume-once token design was meant to avoid. Two endpoints with status preconditions encoded in 409s is the right shape: the caller learns the precondition from the response, not from a probe.
- **Save then delete (credentials), not delete then save.** Detailed in Tasks #3 above. The orphan-credentials-on-PENDING-user state is recoverable (existing iter-030 guard rejects register/options); the orphan-active-user-with-no-credentials state is not (login is broken with no signal of why). Failure asymmetry argues for save-first.
- **No activity event in this iter.** `deactivate / reactivate / reset-credentials / reissue-invite / patch` should all fire `USER_LIFECYCLE_*` activity events for audit trail. None of them do today. Bundling all five into one "user-mgmt audit" iter is cleaner than spraying half-events across whichever iter is convenient. Logged on the backlog.
- **No frontend in this iter.** The `/users` page is the right consumer and is its own future iter. Until then, the new endpoints are exercised by pytest and curl. Cost of staging two endpoints ahead of the UI: ~zero — they are additive.
- **`reset-credentials` allows INACTIVE → PENDING.** Tighter rule "only ACTIVE → PENDING" would force ADMIN to reactivate first, which fires the iter-095 `reactivate` guard but also leaves a dead transient ACTIVE state in the audit (when there is one). Direct INACTIVE → PENDING is what ADMIN means by "give them a way back in."
- **Last-active-admin guard on reset, not on reissue.** Reset effectively deactivates (status drops to PENDING; middleware rejects PENDING). Reissue does not — PENDING stays PENDING, and the user could not log in either way. Mirroring the iter-095 guard on reset is correct; mirroring it on reissue is unnecessary.
- **Self-reset is allowed (subject to last-admin).** Mirrors `deactivate` self-target rules from iter 095. If ADMIN wants to reset their own credentials for a device migration, blocking is paternalistic. The subsequent session-failure is the natural consequence and is recoverable via the returned token.

## Risks

- **`webauthn_credentials.user_id` foreign key**: existing schema has `user_id TEXT NOT NULL REFERENCES users(id)`. No `ON DELETE CASCADE` — the DELETE on `webauthn_credentials` operates on the child rows directly, not via cascade. Reset deletes the credential rows, not the user, so the FK is satisfied. No schema change needed.
- **Race: ADMIN A and ADMIN B both reset the same user concurrently.** Worst case: two saves race on the user row, last-write-wins on `invite_token`, both DELETE statements run idempotently on `webauthn_credentials`. ADMIN A sees their token in the response but the persisted token is ADMIN B's. The response is briefly stale; resolved on next reset or invite. Not a correctness issue, just a UX one. Lock-free is acceptable here — the operation is rare and observed by humans.
- **Self-reset locks the calling session.** The cookie is unchanged, but the next request hits the middleware's PENDING check and `request.state.current_user` is None, so subsequent ADMIN actions return 403. The new invite link is in the response body; ADMIN must consume it from a fresh browser to recover. The test asserts this lockout behavior so the contract is locked.
- **Login flow expectation drift.** `login/options` returns 404 "No credentials found" today when a user has zero credential rows (existing iter-030 guard). After reset-credentials this 404 is the documented outcome for a reset user. Tests assert that path stays 404 (not 403 or 409), so no future contributor accidentally widens the response.

## Notes

The "login broken after reset" test was written against the wrong guard. I had assumed the iter-030 credential-count check (404 "No credentials found") would fire after reset; the actual order is status-check first, so a PENDING user with no credentials returns 403 "Registration pending" before login ever inspects credentials. The contract still satisfies the JTBD ("login is broken until re-register"), it just blocks at status, not at credentials. Test updated to assert the real outcome — and that lock now belongs to the test contract, so future contributors can't quietly invert the guard order. Save-then-delete on credentials worked as designed; no orchestration ambiguity surfaced under test. No domain `ValueError` cases needed beyond the two status-precondition checks. `make test`: 760 passed (+22 new).
