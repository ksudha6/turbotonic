# Iteration 030 -- User entity and auth infrastructure

## Context

All 8 API routers and 11 frontend pages are unprotected; there is no user identity or session management. This iteration adds the User aggregate, WebAuthn passkey registration/login, cookie sessions (itsdangerous), and session middleware that populates `request.state.current_user`. Once identity exists, iterations 031-034 can layer role guards, vendor scoping, and frontend auth on top.

## JTBD (Jobs To Be Done)

- When I access any API endpoint, I want the system to verify my identity via a session cookie, so that only authenticated users can interact with the system
- When I first use the system, I want to register a passkey (WebAuthn) with my username, display name, and role, so that I have a credential tied to my identity
- When I return to the system, I want to authenticate with my passkey, so that I can resume my session without passwords
- When I want to end my session, I want to log out, so that my session cookie is invalidated
- When any page loads, I want to call /api/v1/auth/me to get my current user, so that the frontend knows who is logged in

## Tasks

### Domain: User aggregate
- [ ] Create `backend/src/domain/user.py` with User dataclass
  - Fields: id (str, UUID), username (str, unique), display_name (str), role (UserRole enum), status (UserStatus enum), created_at (datetime)
  - UserRole enum: SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER
  - UserStatus enum: ACTIVE, INACTIVE
  - Factory method `User.create(username, display_name, role)` that validates non-empty/whitespace-only username and display_name, sets status=ACTIVE, generates UUID, sets created_at
  - `deactivate()` and `reactivate()` methods with status guard

### Database: users and webauthn_credentials tables
- [ ] Add `users` table to `backend/src/schema.py`
  - Columns: id TEXT PK, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
- [ ] Add `webauthn_credentials` table to `backend/src/schema.py`
  - Columns: credential_id TEXT PK, user_id TEXT NOT NULL REFERENCES users(id), public_key BLOB NOT NULL, sign_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL

### Repository: UserRepository
- [ ] Create `backend/src/user_repository.py`
  - `save(user)` -- upsert user row
  - `get_by_id(user_id)` -- return User or None
  - `get_by_username(username)` -- return User or None (for login lookup)
  - `save_credential(credential_id, user_id, public_key, sign_count)` -- insert WebAuthn credential
  - `get_credentials_by_user_id(user_id)` -- return list of credential rows
  - `update_sign_count(credential_id, new_count)` -- update sign_count after successful auth

### Auth service: WebAuthn + sessions
- [ ] Add `py-webauthn` to backend dependencies in `pyproject.toml`
- [ ] Add `itsdangerous` to backend dependencies in `pyproject.toml` (if not already present)
- [ ] Create `backend/src/auth/webauthn_service.py`
  - `generate_registration_options(user)` -- returns options JSON for navigator.credentials.create()
  - `verify_registration_response(user, credential_response, challenge)` -- verifies and returns (credential_id, public_key, sign_count)
  - `generate_authentication_options(credentials)` -- returns options JSON for navigator.credentials.get()
  - `verify_authentication_response(credential, auth_response, challenge)` -- verifies and returns new sign_count
  - RP_ID and RP_NAME from config/environment (default: localhost for dev)
- [ ] Create `backend/src/auth/session.py`
  - Use itsdangerous.URLSafeTimedSerializer with a secret key (from env var or config, default for dev)
  - `create_session_cookie(user_id)` -- returns signed cookie value
  - `read_session_cookie(cookie_value, max_age=86400)` -- returns user_id or None if expired/invalid
  - Cookie name: `tt_session`
  - Cookie settings: httponly=True, samesite=Lax, secure=False for dev (True in production)

### Auth router: /api/v1/auth
- [ ] Create `backend/src/routers/auth.py`
- [ ] `POST /api/v1/auth/register/options` -- accepts {username, display_name, role}, creates User in DB (status=ACTIVE), returns WebAuthn registration options and sets challenge in a temporary cookie
- [ ] `POST /api/v1/auth/register/verify` -- accepts WebAuthn credential response, verifies against stored challenge, saves credential to webauthn_credentials, sets session cookie, returns user
- [ ] `POST /api/v1/auth/login/options` -- accepts {username}, looks up user and credentials, returns WebAuthn authentication options and sets challenge cookie
- [ ] `POST /api/v1/auth/login/verify` -- accepts WebAuthn auth response, verifies against stored credential, updates sign_count, sets session cookie, returns user
- [ ] `POST /api/v1/auth/logout` -- clears session cookie
- [ ] `GET /api/v1/auth/me` -- reads session cookie, returns current user or 401

### Session middleware
- [ ] Create `backend/src/auth/middleware.py`
  - FastAPI middleware that reads the `tt_session` cookie on every request
  - If valid: loads User from DB, sets `request.state.current_user`
  - If missing/invalid/expired: sets `request.state.current_user = None`
  - Does NOT reject unauthenticated requests (that is iteration 031's job)
- [ ] Register middleware in `backend/src/main.py`
- [ ] Register auth router in `backend/src/main.py`: `app.include_router(auth.router)`

### Challenge storage
- [ ] Store WebAuthn challenges in a temporary signed cookie (challenge cookie, short-lived)
  - Alternative: in-memory dict keyed by session, cleaned up on verify
  - Decision: signed cookie is simpler, no server-side state

### Tests (permanent)
- [ ] `backend/tests/test_user_domain.py`
  - User.create with valid inputs produces correct fields
  - User.create rejects empty username, whitespace-only username
  - User.create rejects empty display_name
  - deactivate() on ACTIVE user sets INACTIVE
  - deactivate() on INACTIVE user raises ValueError
  - reactivate() on INACTIVE user sets ACTIVE
  - reactivate() on ACTIVE user raises ValueError
- [ ] `backend/tests/test_auth_session.py`
  - create_session_cookie returns a non-empty string
  - read_session_cookie with valid cookie returns user_id
  - read_session_cookie with tampered cookie returns None
  - read_session_cookie with expired cookie returns None
- [ ] `backend/tests/test_auth_endpoints.py`
  - POST /api/v1/auth/me without cookie returns 401
  - Full registration flow (mock WebAuthn verification): register options -> register verify -> me returns user
  - Full login flow (mock WebAuthn verification): login options -> login verify -> me returns user
  - Logout clears session: me returns 401 after logout

### Tests (scratch)
- [ ] Manual passkey test with browser (WebAuthn requires browser context)
- [ ] Verify session cookie is set/cleared in browser dev tools

## Acceptance criteria
- [ ] `User.create()` produces a valid User with UUID id, ACTIVE status, and created_at
- [ ] `User.create()` rejects empty/whitespace-only username and display_name
- [ ] UserRole enum has exactly 4 values: SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER
- [ ] UserStatus enum has exactly 2 values: ACTIVE, INACTIVE
- [ ] `users` and `webauthn_credentials` tables are created by `init_db`
- [ ] WebAuthn registration flow: options -> browser credential -> verify -> credential stored
- [ ] WebAuthn login flow: options -> browser assertion -> verify -> sign_count updated
- [ ] Session cookie is httponly, samesite=Lax, set on register/login, cleared on logout
- [ ] `GET /api/v1/auth/me` returns current user with valid session, 401 without
- [ ] Session middleware populates `request.state.current_user` on every request (None if no session)
- [ ] Existing endpoints continue to work without authentication (no guards yet)
- [ ] `make test` passes with new tests
