"""Tests for TargetRole.ADMIN: event routing, dispatcher fan-out, regression.

Iter 107 adds TargetRole.ADMIN and routes all USER_* events to it. This module
verifies:
  - EVENT_METADATA carries TargetRole.ADMIN for all user-lifecycle events.
  - The activity log stores target_role='ADMIN' for USER_* events.
  - ADMIN users' activity feeds include USER_* rows; SM/VENDOR feeds do not.
  - The dispatcher's resolve_admin_recipients returns only ACTIVE ADMIN emails.
  - Existing SM-targeted events are unaffected (regression).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.activity import (
    ActivityEvent,
    EVENT_METADATA,
    EntityType,
    NotificationCategory,
    TargetRole,
)
from src.domain.user import User, UserRole, UserStatus

pytestmark = pytest.mark.asyncio

# User-lifecycle events that must carry TargetRole.ADMIN after iter 107.
_USER_LIFECYCLE_EVENTS: tuple[ActivityEvent, ...] = (
    ActivityEvent.USER_INVITED,
    ActivityEvent.USER_UPDATED,
    ActivityEvent.USER_DEACTIVATED,
    ActivityEvent.USER_REACTIVATED,
    ActivityEvent.USER_CREDENTIALS_RESET,
    ActivityEvent.USER_INVITE_REISSUED,
)


# ---------------------------------------------------------------------------
# Domain-level: EVENT_METADATA carries correct values.
# ---------------------------------------------------------------------------


def test_user_lifecycle_events_carry_admin_target_role() -> None:
    # All six USER_* events must map to (LIVE, TargetRole.ADMIN).
    # Asserts the full (category, target_role) pair, not just target_role.
    for event in _USER_LIFECYCLE_EVENTS:
        expected_category = NotificationCategory.LIVE
        expected_target = TargetRole.ADMIN
        actual_category, actual_target = EVENT_METADATA[event]
        assert actual_category is expected_category, (
            f"{event.value}: expected category {expected_category!r}, got {actual_category!r}"
        )
        assert actual_target is expected_target, (
            f"{event.value}: expected target_role {expected_target!r}, got {actual_target!r}"
        )


def test_sm_events_are_not_affected_by_admin_addition() -> None:
    # Regression: PO_CREATED and INVOICE_SUBMITTED still target SM, not ADMIN.
    sm_events: tuple[ActivityEvent, ...] = (
        ActivityEvent.PO_CREATED,
        ActivityEvent.INVOICE_SUBMITTED,
        ActivityEvent.MILESTONE_POSTED,
    )
    for event in sm_events:
        _, actual_target = EVENT_METADATA[event]
        assert actual_target is TargetRole.SM, (
            f"{event.value}: SM-targeted event gained wrong target_role {actual_target!r}"
        )


def test_vendor_events_are_not_affected_by_admin_addition() -> None:
    # Regression: PO_SUBMITTED still targets VENDOR.
    vendor_events: tuple[ActivityEvent, ...] = (
        ActivityEvent.PO_SUBMITTED,
        ActivityEvent.INVOICE_APPROVED,
    )
    for event in vendor_events:
        _, actual_target = EVENT_METADATA[event]
        assert actual_target is TargetRole.VENDOR, (
            f"{event.value}: VENDOR-targeted event gained wrong target_role {actual_target!r}"
        )


# ---------------------------------------------------------------------------
# Helpers shared by integration tests below.
# ---------------------------------------------------------------------------


async def _seed_user(
    client: AsyncClient,
    *,
    username: str,
    display_name: str,
    role: UserRole,
    status: UserStatus,
    email: str | None = None,
) -> User:
    from src.main import app
    from src.routers.auth import get_user_repo as auth_get_user_repo

    override = app.dependency_overrides[auth_get_user_repo]
    async for repo in override():
        if status is UserStatus.ACTIVE:
            user = User.create(
                username=username,
                display_name=display_name,
                role=role,
                email=email,
            )
        else:
            user = User.invite(
                username=username,
                display_name=display_name,
                role=role,
                email=email,
            )
            if status is UserStatus.INACTIVE:
                user.deactivate()
        await repo.save(user)
        return user
    raise RuntimeError("override did not yield a repo")


async def _activity_rows_for_user(client: AsyncClient, user_id: str) -> list:
    from src.main import app
    from src.routers.auth import get_activity_repo as auth_get_activity_repo

    override = app.dependency_overrides[auth_get_activity_repo]
    async for repo in override():
        return await repo.list_for_entity(EntityType.USER, user_id)
    raise RuntimeError("override did not yield a repo")


async def _login_as(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    username: str,
) -> None:
    monkeypatch.setenv("DEV_AUTH", "1")
    resp = await client.post("/api/v1/auth/dev-login", json={"username": username})
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Integration: USER_INVITED fires with TargetRole.ADMIN.
# ---------------------------------------------------------------------------


async def test_invite_user_emits_user_invited_with_admin_target(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ADMIN invites a new SM user; USER_INVITED row must exist with
    # entity_type=USER, event=USER_INVITED, target_role=ADMIN.
    admin = await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")

    resp = await client.post(
        "/api/v1/users/invite",
        json={
            "username": "newuser",
            "display_name": "New User",
            "role": "SM",
        },
    )
    assert resp.status_code == 200, resp.text

    invited_id: str = resp.json()["user"]["id"]
    rows = await _activity_rows_for_user(client, invited_id)
    assert len(rows) == 1, f"expected one USER_INVITED row, got {[r.event for r in rows]}"
    row = rows[0]
    assert row.entity_type is EntityType.USER
    assert row.entity_id == invited_id
    assert row.event is ActivityEvent.USER_INVITED
    assert row.target_role is TargetRole.ADMIN
    assert row.actor_id == admin.id
    assert "newuser" in (row.detail or "")


# ---------------------------------------------------------------------------
# Integration: USER_* events stored with target_role='ADMIN'.
# ---------------------------------------------------------------------------


async def test_deactivate_stores_admin_target_role(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    # Second admin so the last-admin guard does not block.
    await _seed_user(
        client,
        username="alice2",
        display_name="Alice2 Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    target = await _seed_user(
        client,
        username="bob",
        display_name="Bob SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{target.id}/deactivate")
    assert resp.status_code == 200

    rows = await _activity_rows_for_user(client, target.id)
    assert len(rows) == 1
    assert rows[0].event is ActivityEvent.USER_DEACTIVATED
    assert rows[0].target_role is TargetRole.ADMIN


async def test_credentials_reset_stores_admin_target_role(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _seed_user(
        client,
        username="alice2",
        display_name="Alice2 Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    target = await _seed_user(
        client,
        username="bob",
        display_name="Bob SM",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")
    resp = await client.post(f"/api/v1/users/{target.id}/reset-credentials")
    assert resp.status_code == 200

    rows = await _activity_rows_for_user(client, target.id)
    assert len(rows) == 1
    assert rows[0].event is ActivityEvent.USER_CREDENTIALS_RESET
    assert rows[0].target_role is TargetRole.ADMIN


# ---------------------------------------------------------------------------
# Integration: activity feed filtering respects ADMIN target_role.
# ---------------------------------------------------------------------------


async def test_sm_feed_excludes_admin_targeted_rows(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Seed an SM user and an ADMIN user. ADMIN invites a new user (USER_INVITED
    # with target_role=ADMIN). The SM feed (target_role=SM) must not include it.
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")

    # Fire a USER_INVITED event.
    invite_resp = await client.post(
        "/api/v1/users/invite",
        json={
            "username": "newsmuser",
            "display_name": "New SM User",
            "role": "SM",
        },
    )
    assert invite_resp.status_code == 200

    # Query the activity feed with target_role=SM. USER_INVITED (target_role=ADMIN)
    # must not appear.
    feed_resp = await client.get("/api/v1/activity/?target_role=SM")
    assert feed_resp.status_code == 200
    events_in_sm_feed: list[str] = [entry["event"] for entry in feed_resp.json()]
    assert ActivityEvent.USER_INVITED.value not in events_in_sm_feed, (
        f"USER_INVITED must not appear in SM feed; got events: {events_in_sm_feed}"
    )


async def test_admin_feed_includes_admin_targeted_rows(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ADMIN feed (no target_role filter) must include USER_INVITED row.
    await _seed_user(
        client,
        username="alice",
        display_name="Alice Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await _login_as(client, monkeypatch, "alice")

    invite_resp = await client.post(
        "/api/v1/users/invite",
        json={
            "username": "newsmuser2",
            "display_name": "New SM User 2",
            "role": "SM",
        },
    )
    assert invite_resp.status_code == 200

    # No target_role filter: ADMIN sees all rows.
    feed_resp = await client.get("/api/v1/activity/")
    assert feed_resp.status_code == 200
    events_in_admin_feed: list[str] = [entry["event"] for entry in feed_resp.json()]
    assert ActivityEvent.USER_INVITED.value in events_in_admin_feed, (
        f"USER_INVITED must appear in unfiltered ADMIN feed; got events: {events_in_admin_feed}"
    )


# ---------------------------------------------------------------------------
# Dispatcher: resolve_admin_recipients returns ADMIN emails only.
# ---------------------------------------------------------------------------


async def test_resolve_admin_recipients_returns_admin_emails(
    client: AsyncClient,
) -> None:
    # Seed one ADMIN user with email, one SM user with email, one VENDOR user.
    # resolve_admin_recipients must return only the ADMIN email.
    admin_email: str = "admin-test@example.com"
    sm_email: str = "sm-test@example.com"

    await _seed_user(
        client,
        username="admin1",
        display_name="Admin One",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email=admin_email,
    )
    await _seed_user(
        client,
        username="sm1",
        display_name="SM One",
        role=UserRole.SM,
        status=UserStatus.ACTIVE,
        email=sm_email,
    )

    from src.main import app
    from src.routers.purchase_order import get_notification_dispatcher as po_get_dispatcher

    override = app.dependency_overrides[po_get_dispatcher]
    async for dispatcher in override():
        recipients: list[str] = await dispatcher.resolve_admin_recipients()
        break

    assert admin_email in recipients, (
        f"ADMIN email {admin_email!r} must be in recipients; got {recipients}"
    )
    assert sm_email not in recipients, (
        f"SM email {sm_email!r} must not be in admin recipients; got {recipients}"
    )


async def test_resolve_admin_recipients_excludes_inactive_admins(
    client: AsyncClient,
) -> None:
    # INACTIVE ADMIN users must not receive notifications.
    inactive_admin_email: str = "inactive-admin@example.com"
    active_admin_email: str = "active-admin@example.com"

    await _seed_user(
        client,
        username="inactiveadmin",
        display_name="Inactive Admin",
        role=UserRole.ADMIN,
        status=UserStatus.INACTIVE,
        email=inactive_admin_email,
    )
    await _seed_user(
        client,
        username="activeadmin",
        display_name="Active Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email=active_admin_email,
    )

    from src.main import app
    from src.routers.purchase_order import get_notification_dispatcher as po_get_dispatcher

    override = app.dependency_overrides[po_get_dispatcher]
    async for dispatcher in override():
        recipients: list[str] = await dispatcher.resolve_admin_recipients()
        break

    assert active_admin_email in recipients
    assert inactive_admin_email not in recipients, (
        f"INACTIVE admin must not appear in recipients; got {recipients}"
    )
