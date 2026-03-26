from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.db import get_db
from src.main import app
from src.repository import PurchaseOrderRepository
from src.routers.purchase_order import get_repo
from src.routers.purchase_order import get_vendor_repo as po_get_vendor_repo
from src.routers.dashboard import get_repo as dash_get_repo
from src.routers.dashboard import get_vendor_repo as dash_get_vendor_repo
from src.routers.vendor import get_vendor_repo as vendor_get_vendor_repo
from src.schema import init_db
from src.vendor_repository import VendorRepository


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    # Each test gets a fresh in-memory SQLite database.
    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        await init_db(conn)

        async def override_get_repo() -> AsyncIterator[PurchaseOrderRepository]:
            await conn.execute("PRAGMA foreign_keys = ON")
            yield PurchaseOrderRepository(conn)

        async def override_get_vendor_repo() -> AsyncIterator[VendorRepository]:
            await conn.execute("PRAGMA foreign_keys = ON")
            yield VendorRepository(conn)

        # bulk_transition calls get_db() directly; patch it in the router module
        # so it yields the same in-memory connection used by the rest of the test.
        @asynccontextmanager
        async def _test_get_db(*_args, **_kwargs) -> AsyncIterator[aiosqlite.Connection]:
            yield conn

        app.dependency_overrides[get_repo] = override_get_repo
        app.dependency_overrides[po_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[vendor_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[dash_get_repo] = override_get_repo
        app.dependency_overrides[dash_get_vendor_repo] = override_get_vendor_repo

        transport = ASGITransport(app=app)
        with patch("src.routers.purchase_order.get_db", _test_get_db):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac

    app.dependency_overrides.clear()
