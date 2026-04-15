from __future__ import annotations

import pytest

from src.domain.user import User, UserRole, UserStatus


def test_create_user_active():
    user = User.create(username="alice", display_name="Alice", role=UserRole.SM)
    assert user.username == "alice"
    assert user.display_name == "Alice"
    assert user.role is UserRole.SM
    assert user.status is UserStatus.ACTIVE
    assert user.vendor_id is None
    assert len(user.id) == 36  # UUID


def test_invite_user_pending():
    user = User.invite(username="bob", display_name="Bob", role=UserRole.SM)
    assert user.status is UserStatus.PENDING


def test_create_empty_username_raises():
    with pytest.raises(ValueError, match="username"):
        User.create(username="", display_name="X", role=UserRole.SM)


def test_create_whitespace_username_raises():
    with pytest.raises(ValueError, match="username"):
        User.create(username="   ", display_name="X", role=UserRole.SM)


def test_create_empty_display_name_raises():
    with pytest.raises(ValueError, match="display_name"):
        User.create(username="alice", display_name="", role=UserRole.SM)


def test_vendor_role_requires_vendor_id():
    with pytest.raises(ValueError, match="vendor_id"):
        User.create(username="v1", display_name="V1", role=UserRole.VENDOR)


def test_non_vendor_rejects_vendor_id():
    with pytest.raises(ValueError, match="vendor_id"):
        User.create(username="a1", display_name="A1", role=UserRole.SM, vendor_id="some-id")


def test_vendor_role_with_vendor_id():
    user = User.create(username="v1", display_name="V1", role=UserRole.VENDOR, vendor_id="vendor-123")
    assert user.vendor_id == "vendor-123"
    assert user.role is UserRole.VENDOR


def test_activate_pending_user():
    user = User.invite(username="bob", display_name="Bob", role=UserRole.SM)
    assert user.status is UserStatus.PENDING
    user.activate()
    assert user.status is UserStatus.ACTIVE


def test_activate_active_user_raises():
    user = User.create(username="alice", display_name="Alice", role=UserRole.SM)
    with pytest.raises(ValueError, match="cannot activate"):
        user.activate()


def test_deactivate_active_user():
    user = User.create(username="alice", display_name="Alice", role=UserRole.SM)
    user.deactivate()
    assert user.status is UserStatus.INACTIVE


def test_deactivate_inactive_user_raises():
    user = User.create(username="alice", display_name="Alice", role=UserRole.SM)
    user.deactivate()
    with pytest.raises(ValueError, match="already INACTIVE"):
        user.deactivate()


def test_reactivate_inactive_user():
    user = User.create(username="alice", display_name="Alice", role=UserRole.SM)
    user.deactivate()
    user.reactivate()
    assert user.status is UserStatus.ACTIVE


def test_reactivate_active_user_raises():
    user = User.create(username="alice", display_name="Alice", role=UserRole.SM)
    with pytest.raises(ValueError, match="INACTIVE"):
        user.reactivate()


def test_all_roles_exist():
    expected = {"ADMIN", "PROCUREMENT_MANAGER", "SM", "VENDOR", "QUALITY_LAB", "FREIGHT_MANAGER"}
    actual = {r.value for r in UserRole}
    assert actual == expected


def test_all_statuses_exist():
    expected = {"ACTIVE", "INACTIVE", "PENDING"}
    actual = {s.value for s in UserStatus}
    assert actual == expected
