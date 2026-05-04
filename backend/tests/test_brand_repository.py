from __future__ import annotations

import pytest
import pytest_asyncio
import asyncpg

from src.brand_repository import BrandRepository
from src.domain.brand import Brand, BrandStatus
from src.domain.vendor import Vendor, VendorType
from src.vendor_repository import VendorRepository
from src.schema import init_db

import os

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test",
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def conn():
    connection = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(connection)
    tx = connection.transaction()
    await tx.start()
    yield connection
    await tx.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def repo(conn):
    return BrandRepository(conn)


@pytest_asyncio.fixture
async def vendor_repo(conn):
    return VendorRepository(conn)


async def _make_vendor(vendor_repo: VendorRepository, name: str = "Test Vendor") -> Vendor:
    vendor = Vendor.create(name=name, country="US", vendor_type=VendorType.PROCUREMENT)
    await vendor_repo.save(vendor)
    return vendor


async def test_save_and_get(repo: BrandRepository) -> None:
    brand = Brand.create(
        name="Acme Brands",
        legal_name="Acme Brands Inc.",
        address="123 Commerce Blvd",
        country="US",
        tax_id="12-3456789",
    )
    await repo.save(brand)
    fetched = await repo.get(brand.id)
    assert fetched is not None
    assert fetched.id == brand.id
    assert fetched.name == brand.name
    assert fetched.legal_name == brand.legal_name
    assert fetched.address == brand.address
    assert fetched.country == brand.country
    assert fetched.tax_id == brand.tax_id
    assert fetched.status is BrandStatus.ACTIVE


async def test_save_duplicate_name_raises(repo: BrandRepository) -> None:
    brand1 = Brand.create(
        name="Unique Brand",
        legal_name="Unique Brand Ltd",
        address="123 St",
        country="US",
    )
    await repo.save(brand1)
    brand2 = Brand.create(
        name="Unique Brand",
        legal_name="Unique Brand Corp",
        address="456 Ave",
        country="DE",
    )
    with pytest.raises(ValueError, match="already exists"):
        await repo.save(brand2)


async def test_list_filters_by_status(repo: BrandRepository) -> None:
    active_brand = Brand.create(
        name="Active Brand",
        legal_name="Active Brand Ltd",
        address="100 Ave",
        country="US",
    )
    inactive_brand = Brand.create(
        name="Inactive Brand",
        legal_name="Inactive Brand Ltd",
        address="200 Ave",
        country="US",
    )
    inactive_brand.deactivate()
    await repo.save(active_brand)
    await repo.save(inactive_brand)

    active_list = await repo.list(BrandStatus.ACTIVE)
    # Filter to only what we inserted (there may be a Default brand from init_db)
    active_names = {b.name for b in active_list}
    assert "Active Brand" in active_names
    assert "Inactive Brand" not in active_names

    inactive_list = await repo.list(BrandStatus.INACTIVE)
    inactive_names = {b.name for b in inactive_list}
    assert "Inactive Brand" in inactive_names
    assert "Active Brand" not in inactive_names


async def test_assign_vendor_idempotent(
    repo: BrandRepository, vendor_repo: VendorRepository
) -> None:
    brand = Brand.create(
        name="Brand With Vendor",
        legal_name="Brand With Vendor Ltd",
        address="300 St",
        country="US",
    )
    await repo.save(brand)
    vendor = await _make_vendor(vendor_repo, "Assigned Vendor")

    # Assign twice — second call must not raise
    await repo.assign_vendor(brand.id, vendor.id)
    await repo.assign_vendor(brand.id, vendor.id)

    ids = await repo.list_vendor_ids(brand.id)
    assert ids == [vendor.id]


async def test_unassign_vendor(
    repo: BrandRepository, vendor_repo: VendorRepository
) -> None:
    brand = Brand.create(
        name="Brand Unassign",
        legal_name="Brand Unassign Ltd",
        address="400 Rd",
        country="US",
    )
    await repo.save(brand)
    vendor = await _make_vendor(vendor_repo, "Vendor To Unassign")

    await repo.assign_vendor(brand.id, vendor.id)
    await repo.unassign_vendor(brand.id, vendor.id)

    ids = await repo.list_vendor_ids(brand.id)
    assert ids == []


async def test_list_vendor_ids(
    repo: BrandRepository, vendor_repo: VendorRepository
) -> None:
    brand = Brand.create(
        name="Multi Vendor Brand",
        legal_name="Multi Vendor Brand Ltd",
        address="500 Blvd",
        country="US",
    )
    await repo.save(brand)
    v1 = await _make_vendor(vendor_repo, "Vendor Alpha")
    v2 = await _make_vendor(vendor_repo, "Vendor Beta")

    await repo.assign_vendor(brand.id, v1.id)
    await repo.assign_vendor(brand.id, v2.id)

    ids = await repo.list_vendor_ids(brand.id)
    assert set(ids) == {v1.id, v2.id}


async def test_count_active_pos_excludes_terminal_statuses(conn) -> None:
    # This test inserts raw PO rows to exercise the status-filter logic
    # without going through the full PO domain. We use raw SQL to control
    # the PO status precisely.
    from datetime import UTC, datetime
    from uuid import uuid4

    repo = BrandRepository(conn)
    brand = Brand.create(
        name="PO Count Brand",
        legal_name="PO Count Brand Ltd",
        address="600 Way",
        country="US",
    )
    await repo.save(brand)

    now_iso = datetime.now(UTC).isoformat()
    vendor_id = str(uuid4())

    # Insert a minimal vendor row
    await conn.execute(
        """
        INSERT INTO vendors (id, name, country, status, vendor_type, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        vendor_id, "Raw Vendor", "US", "ACTIVE", "PROCUREMENT", now_iso, now_iso,
    )

    async def _insert_po(status: str) -> str:
        po_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO purchase_orders
                (id, po_number, status, vendor_id, po_type, currency, issued_date,
                 required_delivery_date, created_at, updated_at, brand_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            po_id, f"PO-{po_id[:8]}", status, vendor_id, "PROCUREMENT", "USD",
            now_iso, now_iso, now_iso, now_iso, brand.id,
        )
        return po_id

    # Non-terminal statuses
    await _insert_po("DRAFT")
    await _insert_po("PENDING")
    await _insert_po("ACCEPTED")
    # Terminal statuses
    await _insert_po("REJECTED")

    count = await repo.count_active_pos(brand.id)
    # Only DRAFT, PENDING, ACCEPTED are active (REJECTED is terminal)
    assert count == 3


async def test_default_brand_seeded_on_init_db(conn) -> None:
    # init_db runs before this transaction starts; Default brand should exist
    repo = BrandRepository(conn)
    brands = await repo.list()
    names = [b.name for b in brands]
    assert "Default" in names

    default_brand = next(b for b in brands if b.name == "Default")
    assert default_brand.legal_name == "Default Brand — please update"
    assert default_brand.status is BrandStatus.ACTIVE
    assert default_brand.country == "US"
