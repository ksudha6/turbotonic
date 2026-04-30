from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class UserRole(Enum):
    ADMIN = "ADMIN"
    PROCUREMENT_MANAGER = "PROCUREMENT_MANAGER"
    SM = "SM"
    VENDOR = "VENDOR"
    QUALITY_LAB = "QUALITY_LAB"
    FREIGHT_MANAGER = "FREIGHT_MANAGER"


class UserStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


class User:
    # id owns aggregate identity; username owns the business reference
    def __init__(
        self,
        *,
        id: str,
        username: str,
        display_name: str,
        role: UserRole,
        status: UserStatus,
        vendor_id: str | None,
        created_at: datetime,
        email: str | None = None,
        invite_token: str | None = None,
    ) -> None:
        self._id = id
        self.username = username
        self.display_name = display_name
        self.role = role
        self.status = status
        self.vendor_id = vendor_id
        self._created_at = created_at
        self.email = email
        # Set on invite/bootstrap, consumed by registration handshake, cleared
        # by activate(). Never persisted into surfaces other than the original
        # invite/bootstrap response.
        self.invite_token = invite_token

    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @classmethod
    def create(
        cls,
        *,
        username: str,
        display_name: str,
        role: UserRole,
        vendor_id: str | None = None,
        email: str | None = None,
    ) -> User:
        _validate_fields(username, display_name, role, vendor_id)
        return cls(
            id=str(uuid4()),
            username=username,
            display_name=display_name,
            role=role,
            status=UserStatus.ACTIVE,
            vendor_id=vendor_id,
            created_at=datetime.now(UTC),
            email=email,
        )

    @classmethod
    def invite(
        cls,
        *,
        username: str,
        display_name: str,
        role: UserRole,
        vendor_id: str | None = None,
        email: str | None = None,
    ) -> User:
        _validate_fields(username, display_name, role, vendor_id)
        return cls(
            id=str(uuid4()),
            username=username,
            display_name=display_name,
            role=role,
            status=UserStatus.PENDING,
            vendor_id=vendor_id,
            created_at=datetime.now(UTC),
            email=email,
            invite_token=str(uuid4()),
        )

    def activate(self) -> None:
        # PENDING -> ACTIVE; only pending users complete registration. The
        # invite_token is consumed here so a stolen link cannot be reused.
        if self.status is not UserStatus.PENDING:
            raise ValueError(f"cannot activate user in {self.status.value} status")
        self.status = UserStatus.ACTIVE
        self.invite_token = None

    def deactivate(self) -> None:
        # ACTIVE or PENDING -> INACTIVE; already-inactive is an error
        if self.status is UserStatus.INACTIVE:
            raise ValueError("user is already INACTIVE")
        self.status = UserStatus.INACTIVE

    def reactivate(self) -> None:
        # INACTIVE -> ACTIVE; only inactive users transition back
        if self.status is not UserStatus.INACTIVE:
            raise ValueError("only INACTIVE users can be reactivated")
        self.status = UserStatus.ACTIVE

    def reset_credentials(self) -> None:
        # ACTIVE | INACTIVE -> PENDING with a fresh invite_token. The
        # webauthn_credentials rows themselves live on a separate aggregate
        # and are deleted by the repository; the User aggregate only owns the
        # status flip and the new token. Already-PENDING is the wrong call
        # (use reissue_invite() instead) and is rejected.
        if self.status is UserStatus.PENDING:
            raise ValueError("user is already PENDING")
        self.status = UserStatus.PENDING
        self.invite_token = str(uuid4())

    def reissue_invite(self) -> None:
        # PENDING -> PENDING with a fresh invite_token. Used when the original
        # invite link is lost before consumption. Non-PENDING users do not have
        # an invite to reissue; reset_credentials() is the right call there.
        if self.status is not UserStatus.PENDING:
            raise ValueError("only PENDING users have an invite to reissue")
        self.invite_token = str(uuid4())


def _validate_fields(
    username: str, display_name: str, role: UserRole, vendor_id: str | None
) -> None:
    if not username or not username.strip():
        raise ValueError("username must not be empty or whitespace-only")
    if not display_name or not display_name.strip():
        raise ValueError("display_name must not be empty or whitespace-only")
    if role is UserRole.VENDOR and vendor_id is None:
        raise ValueError("VENDOR role requires vendor_id")
    if role is not UserRole.VENDOR and vendor_id is not None:
        raise ValueError("vendor_id is only allowed for VENDOR role")
