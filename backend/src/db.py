from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite

DEFAULT_DB_PATH = "data/vendor_portal.db"


@asynccontextmanager
async def get_db(path: str = DEFAULT_DB_PATH) -> AsyncIterator[aiosqlite.Connection]:
    # WAL mode allows concurrent readers alongside a single writer.
    async with aiosqlite.connect(path) as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        yield conn
