# Iteration 029a — Postgres Migration

## Context

The system uses SQLite (aiosqlite, WAL mode) with a single-file database. This blocks two upcoming needs: concurrent multi-user writes (auth iterations 030-033 add real users) and HTTPS deployment for stakeholder demos (WebAuthn requires HTTPS on non-localhost). Moving to Postgres now means 030-055 build on the production-grade stack from day one.

Current state:
- DB connection in `backend/src/db.py` using aiosqlite, `get_db()` context manager
- Schema in `backend/src/schema.py` with raw SQL CREATE TABLE + ad-hoc ALTER TABLE migrations
- 6 repository files using raw parameterized SQL with `?` placeholders
- 17 files import aiosqlite
- No Docker Compose, no Alembic, no migration tooling

## JTBD

- When multiple users hit the API concurrently, I want the database to handle parallel writes without SQLITE_BUSY errors, so that the system works under real multi-user load
- When I deploy to a staging server, I want the database to be a proper service (not a file), so that it survives container restarts and supports standard ops tooling
- When I run tests locally, I want the test database to be isolated and fast, so that my development loop stays tight

## Existing test impact

**Backend tests (13 files, ~209 async tests): all DB-touching tests broke.**

What was updated:
- `backend/tests/conftest.py`: replaced `:memory:` SQLite with asyncpg connection to Postgres test DB; removed PRAGMAs; wrapped each test in a rolled-back transaction for isolation
- 6 test files had `aiosqlite` imports replaced with `asyncpg`
- Type hints changed from `aiosqlite.Connection` to `asyncpg.Connection`
- 1 test removed: `test_migrate_vendors` tested the SQLite-only `_migrate_vendors` function which was removed

**Unaffected:**
- Frontend Playwright tests (8 files, 59 tests): all mock API routes, no real backend
- Pure domain model tests (`test_product.py`, `test_purchase_order.py`, `test_vendor.py`): no DB access

## Tasks

### 1. Docker: local Postgres
- [x] Create `docker-compose.yml` at project root (Postgres 16, port 5432, dev creds, data volume, test DB via init script)
- [x] Create `docker/init-test-db.sh`
- [x] Add `make db-up`, `make db-down`, `make db-reset` targets to Makefile

### 2. Dependencies
- [x] Replace `aiosqlite` with `asyncpg` in `pyproject.toml`
- [x] `uv lock` to update lockfile

### 3. Connection layer (`backend/src/db.py`)
- [x] Replace `get_db()` with connection pool (`init_pool`, `get_db`, `close_pool`)
- [x] Remove WAL pragma and `PRAGMA foreign_keys`
- [x] Update `backend/src/main.py` lifespan: `init_pool()` on startup, `close_pool()` on shutdown
- [x] `DATABASE_URL` from env with dev default

### 4. Schema (`backend/src/schema.py`)
- [x] Remove all `PRAGMA` statements
- [x] Remove redundant `ALTER TABLE ADD COLUMN` blocks (columns inline in CREATE TABLE)
- [x] Remove `_migrate_vendors` (SQLite-only migration)
- [x] Update `init_db(conn)` to use asyncpg execute

### 5. Repository changes (all 6 repos + dto.py)
- [x] `?` placeholders to `$1, $2, ...` numbered placeholders
- [x] `cursor.fetchone()`/`fetchall()` to `conn.fetchrow()`/`conn.fetch()`/`conn.fetchval()`
- [x] `LOWER(col) LIKE LOWER(?)` to `col ILIKE $N`
- [x] `BEGIN`/`COMMIT`/`ROLLBACK` to `async with conn.transaction()`
- [x] Dynamic IN clause placeholder generation
- [x] Remove all `aiosqlite` imports from production code

### 6. Router changes (all 7 routers)
- [x] Remove all `PRAGMA foreign_keys = ON` statements
- [x] Remove `aiosqlite` import from dashboard.py
- [x] Convert dashboard.py direct SQL queries from cursor pattern to asyncpg `fetch`

### 7. Test setup (`backend/tests/conftest.py` + test files)
- [x] Replace `:memory:` SQLite with asyncpg connection to `turbo_tonic_test`
- [x] Wrap each test in a rolled-back transaction for isolation
- [x] Update 6 test files that import `aiosqlite` directly
- [x] Remove `test_migrate_vendors` (tested removed SQLite migration)

### 8. Verify
- [x] 208 backend tests pass against Postgres (3.4s)
- [x] 59 Playwright tests pass (10.6s)
- [x] No `aiosqlite` imports remain in production code
- [x] No `PRAGMA` statements remain

## Notes

Replaced SQLite (aiosqlite) with Postgres 16 (asyncpg, connection pool). Installed Postgres via Homebrew instead of Docker due to disk space constraints. Removed the `_migrate_vendors` function and its test since it was a one-time SQLite data migration with no Postgres equivalent. The docker-compose.yml exists for future use when Docker is available. All 208 backend tests and 59 Playwright tests pass. A seed script (`tools/seed_data.py`) was added to populate demo data: 3 procurement vendors with POs in all states (Draft, Pending, Accepted, Rejected, Revised), and 2 OpEx vendors with 3 OpEx POs.
