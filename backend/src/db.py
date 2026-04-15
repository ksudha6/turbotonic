from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg

DEFAULT_DATABASE_URL = "postgresql://turbo_tonic@localhost:5432/turbo_tonic"

_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str | None = None) -> None:
    global _pool
    url = dsn or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    _pool = await asyncpg.create_pool(url)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_db() -> AsyncIterator[asyncpg.Connection]:
    assert _pool is not None, "Database pool not initialized. Call init_pool() first."
    async with _pool.acquire() as conn:
        yield conn
