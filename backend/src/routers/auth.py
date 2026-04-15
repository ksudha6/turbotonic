from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from src.auth.session import COOKIE_NAME, create_session_cookie
from src.auth.webauthn_service import (
    create_authentication_options,
    create_registration_options,
    verify_authentication,
    verify_registration,
)
from src.db import get_db
from src.domain.user import User, UserRole, UserStatus
from src.user_repository import UserRepository
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def get_user_repo() -> AsyncIterator[UserRepository]:
    async with get_db() as conn:
        yield UserRepository(conn)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]


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
    }


# --- Request models ---

class BootstrapRequest(BaseModel):
    username: str
    display_name: str


class UsernameRequest(BaseModel):
    username: str


class InviteRequest(BaseModel):
    username: str
    display_name: str
    role: str
    vendor_id: str | None = None


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
    return {"options": options, "user": _user_to_dict(user)}


@router.post("/register/options")
async def register_options(body: UsernameRequest, response: Response, repo: UserRepoDep):
    user = await repo.get_by_username(body.username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
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
    username = body.get("username")
    if not credential_json or not username:
        raise HTTPException(status_code=400, detail="Missing credential or username")
    user = await repo.get_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
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


@router.get("/dev-login")
async def dev_login(response: Response, repo: UserRepoDep):
    """Dev-only: auto-login as seed-admin. Remove before production."""
    user = await repo.get_by_username("seed-admin")
    if user is None:
        raise HTTPException(status_code=404, detail="No seed-admin user. Run: uv run python tools/seed_data.py")
    _set_session_cookie(response, user.id)
    return {"user": _user_to_dict(user)}


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
async def invite_user(body: InviteRequest, request: Request, repo: UserRepoDep):
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
    return {"user": _user_to_dict(user)}
