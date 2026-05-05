# Iteration 099 — User-lifecycle activity events

## Context

Iters 095, 096, and 098 added five user lifecycle endpoints: `PATCH /api/v1/users/{id}`,
`POST /{id}/deactivate`, `POST /{id}/reactivate`, `POST /{id}/reset-credentials`,
`POST /{id}/reissue-invite`. None write a row to `activity_log`. Every other write surface
(PO, invoice, milestone, certificate, packaging, shipment, document upload) emits events
through `ActivityLogRepository.append`; user-lifecycle is the only mutation surface with no
audit trail.

The five endpoints already exist and are tested in `test_user_management.py` and
`test_user_recovery.py`. This iter adds the emission and asserts it — no behavior change.

Iter B in `parallel-slate-plan.md`. Backend domain + router + tests only; no frontend changes.

## JTBD

As an ADMIN reviewing the audit trail of who-changed-what on the user roster, I want every
user lifecycle mutation (invite acceptance hand-off via patch, deactivate, reactivate, credential
reset, invite reissue) to leave an `activity_log` row tagged with the actor, the target user,
and the operation, so post-incident review can answer "who deactivated this account?" or "who
re-issued this invite link?" without grep-ing application logs.

As a downstream consumer (a future ADMIN audit dashboard, or an outbound webhook for SOC
compliance), I want one canonical activity-log surface that emits a `USER_*` event per
lifecycle mutation, so consumers do not need to scrape route handlers to reconstruct the
audit picture.

## Scope

In:
- New `EntityType.USER` enum value.
- New `ActivityEvent` constants for the five lifecycle mutations (naming is past-tense flat,
  matching `PO_CREATED` / `INVOICE_PAID` / `SHIPMENT_BOOKED` precedent — not
  `USER_LIFECYCLE_*` from the plan; that prefix has no precedent in `activity.py`).
- `EVENT_METADATA` rows for each new event.
- Activity-repo dependency wiring in `backend/src/routers/auth.py` (the dep does not exist
  there yet).
- Emission calls inside the five endpoint handlers.
- New `backend/tests/test_user_activity_events.py` asserting one row per call, with the right
  shape (entity_type / entity_id / event / actor_id / detail).

Out:
- `USER_INVITED` event for the invite endpoint. The plan calls out exactly five lifecycle
  endpoints; invite creation is already audited via `users.created_at` and is the entry
  point, not a lifecycle mutation. Logged on backlog if it surfaces as a gap during the
  audit-dashboard iter.
- Email or webhook fan-out. Activity-log row only.
- Frontend surfacing. The `/users` page (iter 100 in this slate) will read these rows when it
  ships an activity panel — but the rows must exist first.

## Event vocabulary

Five new `ActivityEvent` constants, naming mirrors the existing flat past-tense convention:

| Constant | Endpoint | Detail format |
|---|---|---|
| `USER_UPDATED` | `PATCH /users/{id}` | `"<username> profile updated"` (mention which fields if cheap; otherwise omit) |
| `USER_DEACTIVATED` | `POST /{id}/deactivate` | `"<username> deactivated"` |
| `USER_REACTIVATED` | `POST /{id}/reactivate` | `"<username> reactivated"` |
| `USER_CREDENTIALS_RESET` | `POST /{id}/reset-credentials` | `"<username> credentials reset; new invite issued"` |
| `USER_INVITE_REISSUED` | `POST /{id}/reissue-invite` | `"<username> invite reissued"` |

The detail string is the human-readable cell visible in any future activity panel; pick wording
that reads naturally next to the existing `SHIPMENT_BOOKED` "<shipment_number> booked with
<carrier>..." pattern. Username is the right anchor — `user_id` is opaque to a human, and the
target user's username is on the row already.

`EntityType.USER` is the new enum member. The existing aggregates in `EntityType` are PO,
INVOICE, CERTIFICATE, PACKAGING, SHIPMENT — all root aggregates. The User aggregate already
has its own repo and lifecycle methods, so it is a peer of those, not a sub-entity.

`EVENT_METADATA[USER_*]` = `(NotificationCategory.LIVE, target_role=None)` for all five.
Rationale in Decisions.

## Tasks

1. **Domain `backend/src/domain/activity.py`**:
   - Add `EntityType.USER = "USER"`.
   - Add five `ActivityEvent` members with the names above.
   - Add five `EVENT_METADATA` rows, all `(NotificationCategory.LIVE, None)`.
   - Comment block above the five events: `# Iter 099: ADMIN user-lifecycle audit events.
     target_role=None broadcasts to all roles since TargetRole has no ADMIN member; in
     practice only ADMINs view these. If user-event noise appears in non-ADMIN feeds, add
     TargetRole.ADMIN and narrow.`

2. **Router `backend/src/routers/auth.py`**:
   - Wire an `ActivityRepoDep` dependency in this file (mirror the import + `get_activity_repo`
     pattern from `backend/src/routers/po_documents.py:40-51` or `backend/src/routers/activity.py:18-23`).
     Inject into the five handlers: `update_user`, `deactivate_user`, `reactivate_user`,
     `reset_credentials`, `reissue_invite`.
   - At the end of each happy-path branch (just before the response is returned, after `repo.save`
     has succeeded), call `await activity_repo.append(entity_type=EntityType.USER,
     entity_id=target.id, event=ActivityEvent.USER_<X>, detail="<username> <verb>")`.
   - Actor id: the existing `_require_admin(request)` already returns `current_user`. The
     `append` signature does not take `actor_id` directly — it is read off `request.state` by
     the repo, OR (more likely from the file already shown) is a parameter. Check the actual
     signature in `backend/src/activity_repository.py:42` and pass `actor_id=current_user.id`
     if the parameter exists. If the repo does not currently accept `actor_id`, add it as a
     keyword parameter with a default of `None` and persist it on the row — schema already has
     `actor_id` per `ActivityLogEntry.actor_id`. Do NOT change the column or any other call
     site beyond the new five.
   - Emission ordering for `reset_credentials`: emit AFTER both `repo.save(target)` AND
     `repo.delete_credentials_by_user_id(target.id)` succeed. If the DELETE fails, the user
     state is recoverable but the activity row would lie about credentials being reset.

3. **Tests `backend/tests/test_user_activity_events.py`** (new file):
   - **Existing test impact**:
     - `test_user_management.py` (iter 095): unchanged behavior on the 5 endpoints; no break
       expected. Spot-check that none of them assert "no activity row exists" — if any does,
       update the assertion to read "exactly one row" instead.
     - `test_user_recovery.py` (iter 098): same — spot-check for any "no activity" assertion.
       Iter-098 doc explicitly noted "no activity event in this iter" but did NOT assert the
       absence; verify before declaring no-break.
     - `test_invite_token.py` (iter 096): unchanged — no lifecycle endpoints touched there.
     - `test_auth_endpoints.py`, `test_auth_dev.py`, `test_critical_path.py`: no lifecycle
       endpoint exercise; no break.
   - One test per event:
     - `test_patch_user_emits_user_updated`: PATCH display_name, then query
       `activity_log` for `entity_type='USER' AND entity_id=<target.id>`; assert exactly one
       row, event = `USER_UPDATED`, actor_id = the calling admin's id, detail mentions the
       target username.
     - `test_deactivate_emits_user_deactivated`: same shape, event = `USER_DEACTIVATED`.
     - `test_reactivate_emits_user_reactivated`: same shape, event = `USER_REACTIVATED`.
     - `test_reset_credentials_emits_user_credentials_reset`: same shape, event =
       `USER_CREDENTIALS_RESET`.
     - `test_reissue_invite_emits_user_invite_reissued`: same shape, event =
       `USER_INVITE_REISSUED`.
   - Negative path:
     - `test_failed_deactivate_does_not_emit`: trigger a 409 (e.g. self-deactivate without
       another admin → caught by last-admin-guard); assert zero activity rows for the target.
       Same shape for one other endpoint (reset on already-PENDING → 409) to lock the
       "emit only on success" contract.
   - Use the dev-login fixture pattern from `test_user_management.py` and
     `test_user_recovery.py` (`DEV_AUTH=1` + `_seed_user` via dependency-overridden repo).
   - Read activity rows by direct query against the test DB, OR via the existing
     `GET /api/v1/activity` endpoint if its filtering shape covers `entity_type=USER`. Check
     `backend/src/routers/activity.py` for the supported filters; prefer the API path if
     available so the test exercises the read surface too. If filters do not cover USER yet
     (likely — USER is brand new), use a direct repo read inside the test rather than
     extending the API in this iter.

4. Run `make test-backend`, confirm 760 → 765+ pass. No frontend or playwright changes.

## Decisions

- **Naming: `USER_<VERB>` past-tense flat, not `USER_LIFECYCLE_<VERB>`**. The plan suggested
  the latter prefix; `domain/activity.py` has no precedent for a category-prefixed naming
  scheme — every existing event is flat (`PO_*`, `INVOICE_*`, `SHIPMENT_*`). Following the
  existing convention reads better in code (`ActivityEvent.USER_DEACTIVATED` not
  `ActivityEvent.USER_LIFECYCLE_DEACTIVATED`) and keeps the activity-log schema homogeneous.

- **`target_role=None` for all five events, not `TargetRole.ADMIN`**. `TargetRole` has no
  ADMIN member, only six operational roles (SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER,
  PROCUREMENT_MANAGER). Adding ADMIN there pulls in every site that exhaustively matches
  `TargetRole` — much wider blast radius than the user-lifecycle audit warrants. None means
  "broadcast", which technically surfaces these rows in every role's feed; in practice only
  ADMINs view the users page or any audit dashboard, so the noise is moot today. If
  `USER_*` rows show up in a non-ADMIN feed during the iter 100 frontend port, narrow then.

- **`USER_INVITED` is out of scope**. Five endpoints, five events, matching iter 098's stated
  audit gap. Invite creation is the entry point of the lifecycle, not a mutation. Adding it
  would pull `bootstrap` (first-admin) and `invite` (subsequent users) into the same iter,
  doubling the surface for marginal audit value (`users.created_at` already records
  creation time).

- **Emit only on success.** The `append` call sits AFTER `repo.save` (and after
  `delete_credentials_by_user_id` for reset). A 409/422 response means no activity row. If
  the DB call after save fails (rare; same-transaction or near-it), the activity row is
  missed — the contract is "row exists implies user state changed", not the inverse. Better
  to under-log on rare failure than to log a false positive on a 409 path.

- **`actor_id` populated from `_require_admin` return value.** The existing helper already
  returns `current_user`. Threading `current_user.id` into `activity_repo.append` is the only
  way to attribute the row to the calling admin; the row's `entity_id` is the target user,
  not the actor. Without this distinction, "who deactivated whom" is unanswerable from the
  log alone.

## Risks

- **`activity_repo.append` may not accept `actor_id` today.** Per the file head shown in
  context, the signature is `append(entity_type, entity_id, event, detail=None, target_role=...)`.
  If `actor_id` is set elsewhere (e.g. from `request.state` inside the repo via a context
  var, or via a decorator), no parameter add is needed. If neither, this iter adds an
  optional `actor_id` parameter that persists onto the row — additive, no other call site
  has to change. Sonnet decides at implementation time after reading the actual signature
  and any existing actor-id population strategy.

- **`EntityType.USER` enum addition could break exhaustive matches.** Other enum members are
  consumed by the activity-log read API and possibly notification dispatchers. Adding USER
  is additive; existing consumers either (a) match a known set and silently ignore unknown
  values, or (b) fail explicitly. The Sonnet sub-agent must grep all `EntityType.` usages,
  enumerate them, and verify no consumer raises on an unknown member. If any does, this iter
  either widens that consumer or scopes to USER-aware reads only.

- **Email-send-failed pattern.** `EMAIL_SEND_FAILED` is the only existing event with
  `target_role=None`. The behavior of the activity feed under that combination is verified
  in production. No new edge cases introduced by USER_* doing the same.

- **Concurrency: two ADMINs deactivating the same user concurrently.** Both writes succeed,
  both append a row. Two USER_DEACTIVATED rows for the same target_id is fine — the
  activity_log is append-only and the second deactivate is a 409 (`User.deactivate()` raises
  on already-INACTIVE), so only one row lands. No locking needed.

## Notes

`ActivityLogRepository.append` did not accept `actor_id` and the INSERT hardcoded the column to
`NULL`. Added an optional `actor_id: str | None = None` keyword and threaded it into the INSERT;
no other call site changed. `EntityType.USER` was additive — `list_for_entity` only special-cases
PO/INVOICE for vendor scoping, so USER falls through cleanly with no consumer break. The
conftest needed one new override (`auth_get_activity_repo`) wired to the same shared connection
as the other repo overrides; without it the auth router would resolve a fresh connection that
sits outside the test transaction. Neither `test_user_management.py` nor `test_user_recovery.py`
asserted "no activity row exists" so no existing test had to be updated. Negative paths picked
were single-admin self-deactivate (last-admin guard) and reset-credentials on already-PENDING.
Final test count: 760 → 767 (+7). No new domain term emerged that is not already in
ddd-vocab.md — `actor` and `target` are already in colloquial use and the row shape carries
the distinction explicitly.
