# Backend

FastAPI + asyncpg + Postgres. Run via `make up` from the repo root; tests via `make test-backend`.

## Dev shortcuts

`DEV_AUTH=1` enables a one-click login surface for seeded users. With the flag set:

- `GET /api/v1/auth/dev-users` returns every ACTIVE user as `{username, display_name, role}` ordered by username.
- `POST /api/v1/auth/dev-login` with `{"username": "..."}` opens a session for that user, no WebAuthn challenge required.

The `/login` page detects the flag by calling `dev-users` on mount and renders a "Dev quick-login" row of buttons when the response is a list.

When the flag is unset (or set to anything other than `"1"`), both endpoints return 404 and the surface is invisible: the login page renders the existing passkey form unchanged.

The flag MUST never be set in production. It bypasses passkey auth entirely.
