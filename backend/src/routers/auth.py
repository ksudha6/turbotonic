from __future__ import annotations

import os
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from src.activity_repository import ActivityLogRepository
from src.auth.session import COOKIE_NAME, create_session_cookie
from src.auth.webauthn_service import (
    create_authentication_options,
    create_registration_options,
    verify_authentication,
    verify_registration,
)
from src.db import get_db
from src.domain.activity import ActivityEvent, EntityType
from src.domain.user import User, UserRole, UserStatus
from src.user_repository import UserRepository
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _dev_auth_enabled() -> bool:
    # Read at request time so tests can flip DEV_AUTH via monkeypatch.setenv
    # without re-importing the module. The single check lives here so the gate
    # is visible in one place; both dev endpoints call it.
    return os.environ.get("DEV_AUTH") == "1"


async def get_user_repo() -> AsyncIterator[UserRepository]:
    async with get_db() as conn:
        yield UserRepository(conn)


async def get_activity_repo() -> AsyncIterator[ActivityLogRepository]:
    async with get_db() as conn:
        yield ActivityLogRepository(conn)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
ActivityRepoDep = Annotated[ActivityLogRepository, Depends(get_activity_repo)]


# Challenge stored in a signed cookie
CHALLENGE_COOKIE = "tt_challenge"


def _set_challenge_cookie(response: Response, challenge: bytes) -> None:
    from src.auth.session import _serializer
    signed = _serializer.dumps(bytes_to_base64url(challenge))
    response.set_cookie(CHALLENGE_COOKIE, signed, httponly=True, samesite="lax", max_age=300)


def _read_challenge_cookie(request: Request) -> bytes | None:
    from src.auth.session import _serializer
    cookie = request.cookies.get(CHALLENGE_COOKIE)
    if not cookie:
        return None
    try:
        b64 = _serializer.loads(cookie, max_age=300)
        return base64url_to_bytes(b64)
    except Exception:
        return None


def _set_session_cookie(response: Response, user_id: str) -> None:
    cookie_value = create_session_cookie(user_id)
    response.set_cookie(COOKIE_NAME, cookie_value, httponly=True, samesite="lax")


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role.value,
        "status": user.status.value,
        "vendor_id": user.vendor_id,
        "email": user.email,
    }


# --- Request models ---

class BootstrapRequest(BaseModel):
    username: str
    display_name: str


class UsernameRequest(BaseModel):
    username: str


class TokenRequest(BaseModel):
    token: str


class InviteRequest(BaseModel):
    username: str
    display_name: str
    role: str
    vendor_id: str | None = None


class UserUpdateRequest(BaseModel):
    display_name: str | None = None
    email: str | None = None


# --- Endpoints ---

@router.post("/bootstrap")
async def bootstrap(body: BootstrapRequest, response: Response, repo: UserRepoDep):
    count = await repo.count_users()
    if count > 0:
        raise HTTPException(status_code=409, detail="Users already exist. Bootstrap not allowed.")
    user = User.invite(
        username=body.username,
        display_name=body.display_name,
        role=UserRole.ADMIN,
    )
    await repo.save(user)
    options, challenge = create_registration_options(user.id, user.username, user.display_name)
    _set_challenge_cookie(response, challenge)
    return {
        "options": options,
        "user": _user_to_dict(user),
        "invite_token": user.invite_token,
    }


@router.post("/register/options")
async def register_options(body: TokenRequest, response: Response, repo: UserRepoDep):
    user = await repo.get_by_invite_token(body.token)
    if user is None:
        raise HTTPException(status_code=404, detail="Invalid invite token")
    if user.status is not UserStatus.PENDING:
        raise HTTPException(status_code=409, detail="User already registered")
    creds = await repo.get_credentials_by_user_id(user.id)
    if creds:
        raise HTTPException(status_code=409, detail="User already has credentials")
    options, challenge = create_registration_options(user.id, user.username, user.display_name)
    _set_challenge_cookie(response, challenge)
    return {"options": options, "user": _user_to_dict(user)}


@router.post("/register/verify")
async def register_verify(request: Request, response: Response, repo: UserRepoDep):
    challenge = _read_challenge_cookie(request)
    if challenge is None:
        raise HTTPException(status_code=400, detail="Missing or expired challenge")
    body = await request.json()
    credential_json = body.get("credential")
    token = body.get("token")
    if not credential_json or not token:
        raise HTTPException(status_code=400, detail="Missing credential or token")
    user = await repo.get_by_invite_token(token)
    if user is None:
        raise HTTPException(status_code=404, detail="Invalid invite token")
    try:
        credential_id, public_key, sign_count = verify_registration(credential_json, challenge)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Registration verification failed: {exc}") from exc
    await repo.save_credential(credential_id, user.id, public_key, sign_count)
    user.activate()
    await repo.save(user)
    _set_session_cookie(response, user.id)
    response.delete_cookie(CHALLENGE_COOKIE)
    return {"user": _user_to_dict(user)}


@router.post("/login/options")
async def login_options(body: UsernameRequest, response: Response, repo: UserRepoDep):
    user = await repo.get_by_username(body.username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status is UserStatus.PENDING:
        raise HTTPException(status_code=403, detail="Registration pending. Check your email for the welcome link.")
    if user.status is UserStatus.INACTIVE:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    creds = await repo.get_credentials_by_user_id(user.id)
    if not creds:
        raise HTTPException(status_code=404, detail="No credentials found")
    credential_list = [(row["credential_id"], row["public_key"]) for row in creds]
    options, challenge = create_authentication_options(credential_list)
    _set_challenge_cookie(response, challenge)
    return {"options": options}


@router.post("/login/verify")
async def login_verify(request: Request, response: Response, repo: UserRepoDep):
    challenge = _read_challenge_cookie(request)
    if challenge is None:
        raise HTTPException(status_code=400, detail="Missing or expired challenge")
    body = await request.json()
    credential_json = body.get("credential")
    username = body.get("username")
    if not credential_json or not username:
        raise HTTPException(status_code=400, detail="Missing credential or username")
    user = await repo.get_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    creds = await repo.get_credentials_by_user_id(user.id)
    # Find the matching credential
    matched_cred = None
    for cred in creds:
        if cred["credential_id"] == credential_json.get("id"):
            matched_cred = cred
            break
    if matched_cred is None:
        raise HTTPException(status_code=400, detail="Credential not recognized")
    try:
        new_sign_count = verify_authentication(
            credential_json,
            challenge,
            matched_cred["public_key"],
            matched_cred["sign_count"],
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Authentication verification failed: {exc}") from exc
    await repo.update_sign_count(matched_cred["credential_id"], new_sign_count)
    _set_session_cookie(response, user.id)
    response.delete_cookie(CHALLENGE_COOKIE)
    return {"user": _user_to_dict(user)}


@router.post("/dev-login")
async def dev_login(body: UsernameRequest, response: Response, repo: UserRepoDep):
    # Dev-only quick-login. Gated by DEV_AUTH=1; without it the endpoint is
    # indistinguishable from a non-existent route (404). With DEV_AUTH=1 the
    # caller passes a username, the user must be ACTIVE, and we set the same
    # session cookie the WebAuthn login flow sets.
    if not _dev_auth_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    user = await repo.get_by_username(body.username)
    if user is None or user.status is not UserStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="User not found")
    _set_session_cookie(response, user.id)
    return {"user": _user_to_dict(user)}


@router.get("/dev-users")
async def dev_users(repo: UserRepoDep):
    # Dev-only: lists every ACTIVE user so the login page can render one
    # quick-login button per user. Same DEV_AUTH gate as dev-login, identical
    # 404 shape so the surface is invisible in production.
    if not _dev_auth_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    users = await repo.list_active_users()
    return [
        {
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role.value,
        }
        for user in users
    ]


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"detail": "Logged out"}


@router.get("/me")
async def me(request: Request, repo: UserRepoDep):
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": _user_to_dict(user)}


# --- Invite endpoint (under /api/v1/users) ---

invite_router = APIRouter(prefix="/api/v1/users", tags=["users"])


@invite_router.post("/invite")
async def invite_user(
    body: InviteRequest,
    request: Request,
    repo: UserRepoDep,
    activity_repo: ActivityRepoDep,
):
    current_user = getattr(request.state, "current_user", None)
    if current_user is None or current_user.role is not UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only ADMIN users can invite")
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid role: {body.role!r}")
    existing = await repo.get_by_username(body.username)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Username already taken")
    try:
        user = User.invite(
            username=body.username,
            display_name=body.display_name,
            role=role,
            vendor_id=body.vendor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await repo.save(user)
    await activity_repo.append(
        entity_type=EntityType.USER,
        entity_id=user.id,
        event=ActivityEvent.USER_INVITED,
        detail=f"{user.username} invited as {user.role.value}",
        actor_id=current_user.id,
    )
    return {"user": _user_to_dict(user), "invite_token": user.invite_token}


def _require_admin(request: Request) -> User:
    # Local helper matching the manual request.state pattern used elsewhere in
    # this router. Returns the current ADMIN user or raises 403.
    current_user = getattr(request.state, "current_user", None)
    if current_user is None or current_user.role is not UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only ADMIN users can manage users")
    return current_user


@invite_router.get("/")
async def list_users(
    request: Request,
    repo: UserRepoDep,
    status: str | None = None,
    role: str | None = None,
):
    _require_admin(request)
    status_filter: UserStatus | None = None
    role_filter: UserRole | None = None
    if status is not None:
        try:
            status_filter = UserStatus(status)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status!r}")
    if role is not None:
        try:
            role_filter = UserRole(role)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid role: {role!r}")
    users = await repo.list_users(status=status_filter, role=role_filter)
    return {"users": [_user_to_dict(u) for u in users]}


@invite_router.get("/{user_id}")
async def get_user(user_id: str, request: Request, repo: UserRepoDep):
    _require_admin(request)
    target = await repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _user_to_dict(target)}


@invite_router.patch("/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    request: Request,
    repo: UserRepoDep,
    activity_repo: ActivityRepoDep,
):
    current_user = _require_admin(request)
    target = await repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if body.display_name is not None:
        if not body.display_name.strip():
            raise HTTPException(
                status_code=422,
                detail="display_name must not be empty or whitespace-only",
            )
        target.display_name = body.display_name
    # Email passes through unchanged shape: explicit None clears, omitted leaves
    # untouched. Pydantic default of None means we cannot distinguish "omitted"
    # from "set to null"; the request shape uses `email: null` to clear, and
    # the only callers are the ADMIN UI that always sends both fields.
    if "email" in body.model_fields_set:
        target.email = body.email
    await repo.save(target)
    await activity_repo.append(
        entity_type=EntityType.USER,
        entity_id=target.id,
        event=ActivityEvent.USER_UPDATED,
        detail=f"{target.username} profile updated",
        actor_id=current_user.id,
    )
    return {"user": _user_to_dict(target)}


@invite_router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    request: Request,
    repo: UserRepoDep,
    activity_repo: ActivityRepoDep,
):
    current_user = _require_admin(request)
    target = await repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Last-admin guard runs before the self-deactivate guard so a single ADMIN
    # trying to disable themselves gets the system-level message instead of the
    # account-level one. With multiple admins, count_active_admins() >= 2 so
    # the self check below catches the user-level case.
    if target.role is UserRole.ADMIN and target.status is UserStatus.ACTIVE:
        active_admin_count = await repo.count_active_admins()
        if active_admin_count <= 1:
            raise HTTPException(
                status_code=409,
                detail="cannot deactivate the last active admin",
            )
    if target.id == current_user.id:
        raise HTTPException(status_code=409, detail="cannot deactivate yourself")
    try:
        target.deactivate()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(target)
    await activity_repo.append(
        entity_type=EntityType.USER,
        entity_id=target.id,
        event=ActivityEvent.USER_DEACTIVATED,
        detail=f"{target.username} deactivated",
        actor_id=current_user.id,
    )
    return {"user": _user_to_dict(target)}


@invite_router.post("/{user_id}/reactivate")
async def reactivate_user(
    user_id: str,
    request: Request,
    repo: UserRepoDep,
    activity_repo: ActivityRepoDep,
):
    current_user = _require_admin(request)
    target = await repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        target.reactivate()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(target)
    await activity_repo.append(
        entity_type=EntityType.USER,
        entity_id=target.id,
        event=ActivityEvent.USER_REACTIVATED,
        detail=f"{target.username} reactivated",
        actor_id=current_user.id,
    )
    return {"user": _user_to_dict(target)}


@invite_router.post("/{user_id}/reset-credentials")
async def reset_credentials(
    user_id: str,
    request: Request,
    repo: UserRepoDep,
    activity_repo: ActivityRepoDep,
):
    current_user = _require_admin(request)
    target = await repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Mirror the iter-095 deactivate guard: dropping the only ACTIVE admin's
    # status to PENDING locks every admin out the same way deactivation does.
    if target.role is UserRole.ADMIN and target.status is UserStatus.ACTIVE:
        active_admin_count = await repo.count_active_admins()
        if active_admin_count <= 1:
            raise HTTPException(
                status_code=409,
                detail="cannot reset credentials for the last active admin",
            )
    try:
        target.reset_credentials()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    # Save before deleting credentials. If the DELETE fails after a successful
    # save, the user is PENDING with stale credentials and the iter-030 guard
    # ("User already has credentials") rejects register/options — recoverable
    # by retrying. The inverse order would leave an ACTIVE user with no
    # credentials, breaking login with no signal of why.
    await repo.save(target)
    await repo.delete_credentials_by_user_id(target.id)
    await activity_repo.append(
        entity_type=EntityType.USER,
        entity_id=target.id,
        event=ActivityEvent.USER_CREDENTIALS_RESET,
        detail=f"{target.username} credentials reset; new invite issued",
        actor_id=current_user.id,
    )
    return {"user": _user_to_dict(target), "invite_token": target.invite_token}


@invite_router.post("/{user_id}/reissue-invite")
async def reissue_invite(
    user_id: str,
    request: Request,
    repo: UserRepoDep,
    activity_repo: ActivityRepoDep,
):
    current_user = _require_admin(request)
    target = await repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        target.reissue_invite()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await repo.save(target)
    await activity_repo.append(
        entity_type=EntityType.USER,
        entity_id=target.id,
        event=ActivityEvent.USER_INVITE_REISSUED,
        detail=f"{target.username} invite reissued",
        actor_id=current_user.id,
    )
    return {"user": _user_to_dict(target), "invite_token": target.invite_token}
