from __future__ import annotations

from typing import AsyncIterator

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

        app.dependency_overrides[get_repo] = override_get_repo
        app.dependency_overrides[po_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[vendor_get_vendor_repo] = override_get_vendor_repo
        app.dependency_overrides[dash_get_repo] = override_get_repo
        app.dependency_overrides[dash_get_vendor_repo] = override_get_vendor_repo

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
