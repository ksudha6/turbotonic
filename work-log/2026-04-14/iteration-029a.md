# Iteration 029a -- Postgres migration

## Context

The system uses SQLite (aiosqlite, WAL mode) with a single-file database. This blocks two upcoming needs: concurrent multi-user writes (auth iterations 030-033 add real users) and HTTPS deployment for stakeholder demos (WebAuthn requires HTTPS on non-localhost). Moving to Postgres now means 030-055 build on the production-grade stack from day one.

## JTBD (Jobs To Be Done)

- When multiple users hit the API concurrently, I want the database to handle parallel writes without SQLITE_BUSY errors, so that the system works under real multi-user load
- When I deploy to a staging server, I want the database to be a proper service (not a file), so that it survives container restarts and supports standard ops tooling
- When I run tests locally, I want the test database to be isolated and fast, so that my development loop stays tight

## Tasks

### Docker: local Postgres
- [ ] Create `docker-compose.yml` at project root
  - Postgres 16 service, port 5432
  - Default dev credentials: user=turbo_tonic, password=turbo_tonic, db=turbo_tonic
  - Volume for data persistence across restarts
  - Test database: turbo_tonic_test (created via init script or test setup)
- [ ] Add `make db-up` and `make db-down` targets to Makefile

### Dependencies
- [ ] Replace `aiosqlite` with `asyncpg` in `pyproject.toml`
- [ ] Add `asyncpg` to dependencies
- [ ] Remove `aiosqlite` from dependencies
- [ ] Run `uv lock` to update lockfile

### Connection layer: backend/src/db.py
- [ ] Replace `get_db()` context manager with connection pool
  - `init_pool()` -- creates `asyncpg.create_pool()` with DATABASE_URL from env (default: `postgresql://turbo_tonic:turbo_tonic@localhost:5432/turbo_tonic`)
  - `get_db()` -- async context manager that acquires a connection from the pool
  - `close_pool()` -- closes the pool on shutdown
- [ ] Remove WAL pragma (Postgres doesn't need it)
- [ ] Remove `PRAGMA foreign_keys = ON` (Postgres enforces FKs by default)
- [ ] Update `backend/src/main.py` lifespan: call `init_pool()` on startup, `close_pool()` on shutdown

### Schema: backend/src/schema.py
- [ ] Replace `CREATE TABLE IF NOT EXISTS` syntax where needed (mostly compatible)
- [ ] Replace `TEXT` primary keys -- keep as TEXT (Postgres supports this fine, no change needed)
- [ ] Replace `BLOB` with `BYTEA` for webauthn_credentials.public_key (future table, but set the pattern)
- [ ] Remove all `PRAGMA` statements
- [ ] Replace `ALTER TABLE ADD COLUMN` error-suppression pattern with `ADD COLUMN IF NOT EXISTS` (Postgres 9.6+)
- [ ] Keep `init_db(conn)` function signature, but use `conn.execute()` with asyncpg instead of aiosqlite

### Repository changes: placeholder syntax
All 6 repository files use `?` placeholders. Postgres requires `$1, $2, ...` numbered placeholders.

- [ ] `backend/src/repository.py` (PurchaseOrderRepository)
  - Replace all `?` with numbered `$1, $2, ...` placeholders
  - Replace `aiosqlite.Row` row factory with asyncpg Record access (asyncpg returns Record objects with attribute/index access by default)
  - Replace `cursor.fetchone()` / `cursor.fetchall()` with `conn.fetchrow()` / `conn.fetch()`
  - Replace `cursor.lastrowid` patterns if any (not expected with UUID PKs)
  - Dynamic WHERE clause construction: update placeholder numbering to be sequential across dynamic filters
  - `LIKE` patterns: Postgres `ILIKE` for case-insensitive search (replace `LOWER(col) LIKE LOWER(?)` with `col ILIKE $N`)
  - Transaction pattern: replace `BEGIN`/`COMMIT`/`ROLLBACK` with `async with conn.transaction()`

- [ ] `backend/src/vendor_repository.py` (VendorRepository)
  - Same placeholder and row access changes
  - Dynamic WHERE construction: sequential placeholder numbering

- [ ] `backend/src/product_repository.py` (ProductRepository)
  - Same placeholder and row access changes

- [ ] `backend/src/invoice_repository.py` (InvoiceRepository)
  - Same placeholder and row access changes
  - Transaction pattern: `async with conn.transaction()`
  - Dynamic WHERE with JOINs: renumber placeholders

- [ ] `backend/src/milestone_repository.py` (MilestoneRepository)
  - Same placeholder and row access changes

- [ ] `backend/src/activity_repository.py` (ActivityLogRepository)
  - Same placeholder and row access changes
  - Dynamic IN clause: replace `",".join("?" * len(ids))` with `",".join(f"${i}" for i in range(start, start+len(ids)))`

### Test setup: backend/tests/conftest.py
- [ ] Replace `:memory:` SQLite with asyncpg connection to test database
  - Connect to `turbo_tonic_test` database
  - Before each test: create tables, run test, drop tables (or use transactions that roll back)
  - Strategy: wrap each test in a transaction that rolls back -- fastest, no cleanup needed
- [ ] Remove `PRAGMA` statements
- [ ] Update dependency injection to use asyncpg connection
- [ ] Ensure test isolation: each test sees a clean database state

### Makefile updates
- [ ] Update `make test` to ensure test database exists before running pytest
- [ ] Add `make db-reset` to drop and recreate the dev database

### Environment config
- [ ] Read DATABASE_URL from environment variable with sensible dev default
- [ ] Document in README or .env.example: `DATABASE_URL=postgresql://turbo_tonic:turbo_tonic@localhost:5432/turbo_tonic`

## SQL compatibility notes

These patterns are already Postgres-compatible (no changes needed):
- `COALESCE()`, `CAST(... AS REAL)` (use `CAST(... AS DOUBLE PRECISION)` or `::float`), `SUM()`, `COUNT()`
- `LEFT JOIN`, subqueries, `GROUP BY`, `ORDER BY ... LIMIT ... OFFSET`
- `CREATE TABLE IF NOT EXISTS`
- TEXT primary keys for UUIDs
- ISO 8601 datetime strings stored as TEXT (works, though Postgres TIMESTAMPTZ is better long-term)

These need changes:
- `?` → `$1, $2, ...` (all repos)
- `LOWER(col) LIKE LOWER(?)` → `col ILIKE $N` (search queries)
- `BLOB` → `BYTEA` (binary data)
- `PRAGMA` → removed
- `BEGIN`/`COMMIT`/`ROLLBACK` → `async with conn.transaction()`
- Dynamic placeholder generation for IN clauses

## Acceptance criteria
- [ ] `docker-compose up` starts Postgres and the app connects to it
- [ ] All 9 existing tables are created in Postgres by `init_db`
- [ ] All existing API endpoints work identically (same requests, same responses)
- [ ] `make test` passes all existing tests against Postgres (not SQLite)
- [ ] No SQLite imports remain in production code
- [ ] No `PRAGMA` statements remain
- [ ] All repository queries use `$N` numbered placeholders
- [ ] Transactions use `async with conn.transaction()` pattern
- [ ] `make db-up`, `make db-down`, `make db-reset` work
- [ ] DATABASE_URL is configurable via environment variable
