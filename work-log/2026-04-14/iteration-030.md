# Iteration 030 -- User entity and auth infrastructure

## Context

All 8 API routers and 11 frontend pages are unprotected; there is no user identity or session management. This iteration adds the User aggregate (with 6 roles), WebAuthn passkey registration/login, cookie sessions (itsdangerous), session middleware, and invite-only registration with first-user bootstrap. Once identity exists, iterations 031-034 can layer role guards, vendor scoping, and frontend auth on top.

## JTBD (Jobs To Be Done)

- When I access any API endpoint, I want the system to verify my identity via a session cookie, so that only authenticated users can interact with the system
- When the system has no users, I want the first registration to create an ADMIN account automatically, so that the system can be bootstrapped without manual DB edits
- When I am an admin, I want to invite new users by specifying their username, display name, and role, so that registration is controlled and no one can self-assign a role
- When I receive an invitation, I want to register a passkey (WebAuthn) against my pre-created user record, so that I have a credential tied to my identity
- When I return to the system, I want to authenticate with my passkey, so that I can resume my session without passwords
- When I want to end my session, I want to log out, so that my session cookie is invalidated
- When any page loads, I want to call /api/v1/auth/me to get my current user, so that the frontend knows who is logged in

## Tasks

### Domain: User aggregate
- [ ] Create `backend/src/domain/user.py` with User dataclass
  - Fields: id (str, UUID), username (str, unique), display_name (str), role (UserRole enum), status (UserStatus enum), vendor_id (str | None), created_at (datetime)
  - UserRole enum: ADMIN, PROCUREMENT_MANAGER, SM, VENDOR, QUALITY_LAB, FREIGHT_MANAGER
  - UserStatus enum: ACTIVE, INACTIVE, PENDING (PENDING = invited but no passkey registered yet)
  - `vendor_id` is nullable; set only for VENDOR-role users to link them to their vendor entity
  - Factory method `User.create(username, display_name, role, vendor_id=None)` that validates non-empty/whitespace-only username and display_name, sets status=ACTIVE, generates UUID, sets created_at
  - `User.invite(username, display_name, role, vendor_id=None)` -- same as create but sets status=PENDING (user has no passkey yet)
  - `activate()` -- transitions PENDING to ACTIVE (called after passkey registration)
  - `deactivate()` and `reactivate()` methods with status guard
  - Validation: VENDOR role requires vendor_id; non-VENDOR roles reject vendor_id
  - Domain rule: cannot deactivate the last active ADMIN user

### Database: users, webauthn_credentials tables
- [ ] Add `users` table to `backend/src/schema.py`
  - Columns: id TEXT PK, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL, vendor_id TEXT REFERENCES vendors(id), created_at TEXT NOT NULL
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
  - `count_users()` -- return total user count (for first-user bootstrap check)

### Auth service: WebAuthn + sessions
- [ ] Add `py-webauthn` to backend dependencies in `pyproject.toml`
- [ ] Add `itsdangerous` to backend dependencies in `pyproject.toml` (if not already present)
- [ ] Create `backend/src/auth/webauthn_service.py`
  - `generate_registration_options(user)` -- returns options JSON for navigator.credentials.create()
  - `verify_registration_response(user, credential_response, challenge)` -- verifies and returns (credential_id, public_key, sign_count)
  - `generate_authentication_options(credentials)` -- returns options JSON for navigator.credentials.get()
  - `verify_authentication_response(credential, auth_response, challenge)` -- verifies and returns new sign_count
  - Note: py-webauthn validates sign count regression internally (rejects if received sign_count <= stored sign_count when > 0). No custom code needed for clone detection.
  - RP_ID and RP_NAME from config/environment (default: localhost for dev)
- [ ] Create `backend/src/auth/session.py`
  - Use itsdangerous.URLSafeTimedSerializer with a secret key (from env var or config, default for dev)
  - `create_session_cookie(user_id)` -- returns signed cookie value (stores only user_id, never role)
  - `read_session_cookie(cookie_value, max_age=86400)` -- returns user_id or None if expired/invalid
  - Cookie name: `tt_session`
  - Cookie settings: httponly=True, samesite=Lax, secure=False for dev (True in production)

### Auth router: /api/v1/auth
- [ ] Create `backend/src/routers/auth.py`
- [ ] `POST /api/v1/auth/bootstrap` -- if zero users exist: accepts {username, display_name}, creates User with role=ADMIN and status=PENDING, returns WebAuthn registration options and sets challenge cookie. Returns 409 if any users already exist.
- [ ] `POST /api/v1/auth/register/options` -- accepts {username} for a PENDING user (pre-created by admin invite), returns WebAuthn registration options and sets challenge cookie. Returns 404 if user not found, 409 if user already has credentials.
- [ ] `POST /api/v1/auth/register/verify` -- accepts WebAuthn credential response, verifies against stored challenge, saves credential to webauthn_credentials, transitions user from PENDING to ACTIVE, sets session cookie, returns user
- [ ] `POST /api/v1/auth/login/options` -- accepts {username}, looks up user and credentials, returns WebAuthn authentication options and sets challenge cookie.
  - If user exists but status is PENDING: return 403 with body {"detail": "Registration pending. Check your email for the welcome link."}
- [ ] `POST /api/v1/auth/login/verify` -- accepts WebAuthn auth response, verifies against stored credential, updates sign_count, sets session cookie, returns user
- [ ] `POST /api/v1/auth/logout` -- clears session cookie
- [ ] `GET /api/v1/auth/me` -- reads session cookie, returns current user or 401

### Invite endpoint: /api/v1/users
- [ ] `POST /api/v1/users/invite` -- requires ADMIN role. Accepts {username, display_name, role, vendor_id?}. Creates User with status=PENDING. Returns the created user. This is how all non-bootstrap users are created.

### Session middleware
- [ ] Create `backend/src/auth/middleware.py`
  - FastAPI middleware that reads the `tt_session` cookie on every request
  - If valid: loads User from DB, checks `user.status == ACTIVE`, sets `request.state.current_user`
  - If valid but user is INACTIVE or PENDING: sets `request.state.current_user = None` (treated as unauthenticated)
  - If missing/invalid/expired: sets `request.state.current_user = None`
  - Does NOT reject unauthenticated requests (that is iteration 031's job)
- [ ] Register middleware in `backend/src/main.py`
- [ ] Register auth router in `backend/src/main.py`: `app.include_router(auth.router)`

### Test infrastructure
- [ ] Add `make test` target to Makefile that runs both `test-backend` and `test-browser` sequentially
- [ ] Add pre-commit hook (`.git/hooks/pre-commit`) that runs `make test-backend` and rejects the commit if tests fail
- [ ] Add `backend/tests/test_critical_path.py` -- single integration test exercising the full PO lifecycle:
  1. Create vendor
  2. Create PO with line items
  3. Submit PO
  4. Accept PO
  5. Create invoice from PO
  6. Submit invoice
  7. Post milestone (RAW_MATERIALS through READY_TO_SHIP)
  - This test is the regression safety net for all future iterations

### Challenge storage
- [ ] Store WebAuthn challenges in a temporary signed cookie (challenge cookie, short-lived)
  - Alternative: in-memory dict keyed by session, cleaned up on verify
  - Decision: signed cookie is simpler, no server-side state

### Existing test impact
- No existing tests break. Middleware sets `request.state.current_user = None` for unauthenticated requests but does not reject them. Auth enforcement is deferred to iteration 031.

### Tests (permanent)
- [ ] `backend/tests/test_user_domain.py`
  - User.create with valid inputs produces correct fields, status=ACTIVE
  - User.invite with valid inputs produces correct fields, status=PENDING
  - User.create rejects empty username, whitespace-only username
  - User.create rejects empty display_name
  - VENDOR role without vendor_id raises ValueError
  - Non-VENDOR role with vendor_id raises ValueError
  - activate() on PENDING user sets ACTIVE
  - activate() on ACTIVE user raises ValueError
  - deactivate() on ACTIVE user sets INACTIVE
  - deactivate() on INACTIVE user raises ValueError
  - deactivate() on last active ADMIN raises ValueError
  - reactivate() on INACTIVE user sets ACTIVE
  - reactivate() on ACTIVE user raises ValueError
- [ ] `backend/tests/test_auth_session.py`
  - create_session_cookie returns a non-empty string
  - read_session_cookie with valid cookie returns user_id
  - read_session_cookie with tampered cookie returns None
  - read_session_cookie with expired cookie returns None
- [ ] `backend/tests/test_auth_endpoints.py`
  - POST /api/v1/auth/me without cookie returns 401
  - Bootstrap flow: bootstrap -> register verify -> me returns ADMIN user
  - Bootstrap returns 409 when users already exist
  - Invite flow: admin invites user -> register options -> register verify -> me returns user
  - Register options returns 404 for unknown username
  - Register options returns 409 for user who already has credentials
  - Full login flow (mock WebAuthn verification): login options -> login verify -> me returns user
  - Logout clears session: me returns 401 after logout
  - Inactive user with valid cookie gets 401 from /me (middleware rejects inactive)
  - Login options for PENDING user returns 403 with "Registration pending" message

### Tests (scratch)
- [ ] Manual passkey test with browser (WebAuthn requires browser context)
- [ ] Verify session cookie is set/cleared in browser dev tools

## Acceptance criteria
- [ ] UserRole enum has exactly 6 values: ADMIN, PROCUREMENT_MANAGER, SM, FREIGHT_MANAGER, QUALITY_LAB, VENDOR
- [ ] UserStatus enum has exactly 3 values: ACTIVE, INACTIVE, PENDING
- [ ] VENDOR-role users require vendor_id; non-VENDOR roles reject vendor_id
- [ ] `users` and `webauthn_credentials` tables are created by `init_db`
- [ ] First-user bootstrap: when zero users exist, /bootstrap creates an ADMIN
- [ ] Bootstrap returns 409 if any users already exist
- [ ] Invite-only registration: only ADMIN can create new users via /users/invite
- [ ] Invited users register passkeys against their PENDING record, transitioning to ACTIVE
- [ ] WebAuthn registration flow: options -> browser credential -> verify -> credential stored
- [ ] WebAuthn login flow: options -> browser assertion -> verify -> sign_count updated
- [ ] Session cookie is httponly, samesite=Lax, stores only user_id
- [ ] Session cookie set on register/login, cleared on logout
- [ ] `GET /api/v1/auth/me` returns current user with valid session, 401 without
- [ ] Middleware populates `request.state.current_user` on every request (None if no session, inactive, or pending)
- [ ] Deactivated users with valid session cookies are treated as unauthenticated
- [ ] Existing endpoints continue to work without authentication (no guards yet)
- [ ] `make test` runs both backend and browser test suites
- [ ] Pre-commit hook rejects commits when backend tests fail
- [ ] Critical-path integration test passes (vendor -> PO -> submit -> accept -> invoice -> milestone)
- [ ] `make test` passes with all new and existing tests
