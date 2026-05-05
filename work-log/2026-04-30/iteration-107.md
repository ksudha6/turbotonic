# Iteration 107 — TargetRole.ADMIN with system-event routing

## Context

`TargetRole` in `backend/src/domain/activity.py` covers five operational roles: SM, VENDOR,
QUALITY_LAB, FREIGHT_MANAGER, PROCUREMENT_MANAGER. ADMIN has no value. When iter 099 added
user-lifecycle events (USER_UPDATED, USER_DEACTIVATED, USER_REACTIVATED,
USER_CREDENTIALS_RESET, USER_INVITE_REISSUED), all five were assigned `target_role=None` as a
broadcast. Iter 100 shipped the `/users` ADMIN page that consumes these events; the activity
feed filters by target_role, so ADMIN-scoped events never appear in ADMIN feeds because the
enum value is missing.

`POST /api/v1/users/invite` has no activity event. The USER_* events from iter 099 cover the
five lifecycle mutation endpoints; invite creation was deferred. This iter adds USER_INVITED
alongside TargetRole.ADMIN.

## JTBD

- ADMIN needs visibility into user-lifecycle events (invited, invite resent, credential reset,
  deactivated, reactivated, profile updated) in their notification feed without those rows
  appearing in SM, VENDOR, or other non-ADMIN feeds.

## Tasks

1. Add `TargetRole.ADMIN = "ADMIN"` to the enum in `backend/src/domain/activity.py`.
2. Add `ActivityEvent.USER_INVITED = "USER_INVITED"` to the enum.
3. Update `EVENT_METADATA` for all six user-lifecycle events to use `TargetRole.ADMIN`:
   USER_INVITED, USER_UPDATED, USER_DEACTIVATED, USER_REACTIVATED, USER_CREDENTIALS_RESET,
   USER_INVITE_REISSUED.
4. Update the `NotificationDispatcher` in `backend/src/services/notifications.py`: when
   resolving an ADMIN-targeted event, fan-out to all ACTIVE ADMIN users via a single SQL query
   (`list_active_emails_by_roles(("ADMIN",))`). No existing dispatch paths change.
5. Wire `USER_INVITED` emission in `invite_user` endpoint in `backend/src/routers/auth.py`,
   following the same pattern as the other five lifecycle endpoints. The invite endpoint already
   takes `ActivityRepoDep`; add injection if missing.
6. Update `backend/tests/test_user_activity_events.py`: add a test for USER_INVITED and update
   existing tests to assert `target_role is TargetRole.ADMIN` on the logged rows.
7. Add `backend/tests/test_admin_target_role.py` with dispatcher and routing tests.
8. Run `make test` and confirm green.

## Tests

### Existing test impact

`test_user_activity_events.py` tests currently assert on row shape but do not check
`target_role`. The rows previously had `target_role=None`; after this iter they carry
`TargetRole.ADMIN`. Tests that call `_activity_rows_for` and check the full row shape will
continue to pass as long as they do not assert `target_role is None`. None of the existing
tests in that file assert on target_role, so no break is expected.

`test_notifications.py` does not exercise ADMIN fan-out (all current dispatch paths go to SM
or VENDOR). No break expected.

### New tests

- `test_invite_user_emits_user_invited`: POST /api/v1/users/invite, assert one USER_INVITED
  row with entity_type=USER, target_role=TargetRole.ADMIN, actor_id=admin id.
- `test_admin_target_role_routes_to_admin_users`: dispatcher dispatch with an ADMIN-targeted
  event sends email to ACTIVE ADMIN users only, not SM or VENDOR users.
- `test_admin_target_role_excludes_non_admin`: same setup, assert SM email not in recipient
  list.
- `test_existing_sm_route_unchanged`: SM-targeted event (PO_CREATED) still reaches SM users,
  not ADMIN users.
- `test_user_lifecycle_events_carry_admin_target_role`: one assertion per lifecycle event that
  the EVENT_METADATA value is (LIVE, TargetRole.ADMIN).

## Notes

`TargetRole.ADMIN` was added to the enum alongside `ActivityEvent.USER_INVITED` (the one
user-lifecycle event that iter 099 had explicitly deferred). All six USER_* events
(USER_INVITED, USER_UPDATED, USER_DEACTIVATED, USER_REACTIVATED, USER_CREDENTIALS_RESET,
USER_INVITE_REISSUED) now carry `TargetRole.ADMIN` in EVENT_METADATA, replacing the previous
`target_role=None` broadcast. The activity_log filter queries already handled
`target_role='ADMIN'` correctly once the enum value existed; no query changes were needed.
ADMIN fan-out for email was wired in the dispatcher as `resolve_admin_recipients()` using
`list_active_emails_by_roles(("ADMIN",))` — a single SQL query, no per-user iteration. No
email templates for USER_* events exist yet; the recipient path is ready for future use.
The `test_role_guards._make_client_with_role` helper needed `auth_get_activity_repo` added to
its dependency override map because `invite_user` now injects `ActivityRepoDep`; without the
override, the dependency would use the real pool rather than the test transaction connection.
Test count: 767 → 777 (+10). Three warnings (sync test functions in an asyncio-marked module)
are advisory only and do not affect test validity.
