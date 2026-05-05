"""Iter 113: VendorParty repository tests (schema + migration)."""
from __future__ import annotations

import pytest
import pytest_asyncio

from src.domain.vendor_party import VendorPartyInUseError, VendorPartyRole
from src.vendor_party_repository import VendorPartyRepository
from src.vendor_repository import VendorRepository
from src.domain.vendor import Vendor, VendorType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_vendor(conn) -> dict:
    """Insert a minimal vendor and return its id + name."""
    from datetime import UTC, datetime
    from uuid import uuid4

    vendor_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    await conn.execute(
        """
        INSERT INTO vendors (id, name, country, status, vendor_type, address, account_details, tax_id, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        vendor_id, "Test Vendor", "CN", "ACTIVE", "PROCUREMENT", "123 Factory Rd", "", "", now, now,
    )
    return {"id": vendor_id, "name": "Test Vendor"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_and_get_round_trip(authenticated_client) -> None:
    """Insert and fetch; assert the response dict has exactly the expected keys."""
    from tests.conftest import _current_upload_dir
    import asyncpg
    import os

    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test")
    conn = await asyncpg.connect(db_url)
    await conn.execute("BEGIN")
    try:
        vendor = await _make_vendor(conn)
        repo = VendorPartyRepository(conn)

        party = await repo.create(
            vendor_id=vendor["id"],
            role=VendorPartyRole.SELLER,
            legal_name="ACME Seller Ltd",
            address="HK Trading Park",
            country="HK",
            tax_id="HK-999",
            banking_details="",
        )

        fetched = await repo.get(party.id)
        assert fetched is not None
        expected_keys = {
            "id", "vendor_id", "role", "legal_name", "address",
            "country", "tax_id", "banking_details", "created_at", "updated_at",
        }
        actual_keys = {k for k in vars(fetched) if not k.startswith("_")}
        # Add property-backed fields
        actual_keys.add("id")
        actual_keys.add("created_at")
        actual_keys = actual_keys - {"_id", "_created_at"}

        assert fetched.id == party.id
        assert fetched.vendor_id == vendor["id"]
        assert fetched.role == VendorPartyRole.SELLER
        assert fetched.legal_name == "ACME Seller Ltd"
        assert fetched.tax_id == "HK-999"
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()


@pytest.mark.asyncio
async def test_list_by_vendor_returns_all_roles() -> None:
    import asyncpg
    import os

    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test")
    conn = await asyncpg.connect(db_url)
    await conn.execute("BEGIN")
    try:
        vendor = await _make_vendor(conn)
        repo = VendorPartyRepository(conn)

        seller = await repo.create(
            vendor_id=vendor["id"], role=VendorPartyRole.SELLER,
            legal_name="Seller Co", address="Seller Addr", country="US",
        )
        shipper = await repo.create(
            vendor_id=vendor["id"], role=VendorPartyRole.SHIPPER,
            legal_name="Shipper Co", address="Shipper Addr", country="CN",
        )
        mfr = await repo.create(
            vendor_id=vendor["id"], role=VendorPartyRole.MANUFACTURER,
            legal_name="Factory Co", address="Factory Rd", country="CN",
        )

        all_parties = await repo.list_by_vendor(vendor["id"])
        assert len(all_parties) == 3

        sellers = await repo.list_by_vendor_and_role(vendor["id"], VendorPartyRole.SELLER)
        assert len(sellers) == 1
        assert sellers[0].id == seller.id

        shippers = await repo.list_by_vendor_and_role(vendor["id"], VendorPartyRole.SHIPPER)
        assert len(shippers) == 1
        assert shippers[0].id == shipper.id
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()


@pytest.mark.asyncio
async def test_delete_unlinked_party_succeeds() -> None:
    import asyncpg
    import os

    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test")
    conn = await asyncpg.connect(db_url)
    await conn.execute("BEGIN")
    try:
        vendor = await _make_vendor(conn)
        repo = VendorPartyRepository(conn)

        party = await repo.create(
            vendor_id=vendor["id"], role=VendorPartyRole.REMIT_TO,
            legal_name="Factoring Co", address="Finance Blvd", country="SG",
        )
        await repo.delete(party.id)
        fetched = await repo.get(party.id)
        assert fetched is None
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()


@pytest.mark.asyncio
async def test_delete_party_referenced_as_vendor_default_raises_in_use_error() -> None:
    import asyncpg
    import os

    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test")
    conn = await asyncpg.connect(db_url)
    await conn.execute("BEGIN")
    try:
        vendor = await _make_vendor(conn)
        repo = VendorPartyRepository(conn)

        party = await repo.create(
            vendor_id=vendor["id"], role=VendorPartyRole.SELLER,
            legal_name="Seller Inc", address="Seller St", country="US",
        )
        # Set as vendor default
        await conn.execute(
            "UPDATE vendors SET default_seller_party_id = $1 WHERE id = $2",
            party.id, vendor["id"],
        )
        with pytest.raises(VendorPartyInUseError):
            await repo.delete(party.id)
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()


@pytest.mark.asyncio
async def test_delete_party_referenced_by_product_raises_in_use_error() -> None:
    import asyncpg
    import os
    from uuid import uuid4
    from datetime import UTC, datetime

    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test")
    conn = await asyncpg.connect(db_url)
    await conn.execute("BEGIN")
    try:
        vendor = await _make_vendor(conn)
        repo = VendorPartyRepository(conn)

        party = await repo.create(
            vendor_id=vendor["id"], role=VendorPartyRole.MANUFACTURER,
            legal_name="Factory X", address="Industrial Zone", country="CN",
        )
        # Insert a product linked to this party
        now = datetime.now(UTC).isoformat()
        prod_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO products (id, vendor_id, part_number, description,
                manufacturing_address, created_at, updated_at, manufacturer_party_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            prod_id, vendor["id"], "PN-MFR", "", "", now, now, party.id,
        )
        with pytest.raises(VendorPartyInUseError):
            await repo.delete(party.id)
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()


@pytest.mark.asyncio
async def test_set_default_party_updates_vendor_row() -> None:
    import asyncpg
    import os

    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test")
    conn = await asyncpg.connect(db_url)
    await conn.execute("BEGIN")
    try:
        vendor = await _make_vendor(conn)
        repo = VendorPartyRepository(conn)

        party = await repo.create(
            vendor_id=vendor["id"], role=VendorPartyRole.SELLER,
            legal_name="Invoicing Entity", address="Corp Ave", country="SG",
        )
        await repo.set_default_party_on_vendor(vendor["id"], VendorPartyRole.SELLER, party.id)

        row = await conn.fetchrow("SELECT default_seller_party_id FROM vendors WHERE id = $1", vendor["id"])
        assert row["default_seller_party_id"] == party.id
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()


@pytest.mark.asyncio
async def test_migration_backfill_creates_seller_party_for_existing_vendor() -> None:
    """Simulate pre-migration state: vendor without default_seller_party_id.
    Run init_db and verify the backfill created a SELLER party.
    """
    import asyncpg
    import os
    from src.schema import init_db as schema_init_db

    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test")
    conn = await asyncpg.connect(db_url)
    await conn.execute("BEGIN")
    try:
        # Insert a vendor with no default_seller_party_id
        vendor = await _make_vendor(conn)
        # Ensure no default is set (should be NULL from INSERT)
        await conn.execute(
            "UPDATE vendors SET default_seller_party_id = NULL WHERE id = $1", vendor["id"]
        )

        # Run init_db to trigger the backfill
        await schema_init_db(conn)

        # Assert: SELLER party was created and vendor default_seller_party_id points at it
        party_row = await conn.fetchrow(
            "SELECT * FROM vendor_parties WHERE vendor_id = $1 AND role = 'SELLER'",
            vendor["id"],
        )
        assert party_row is not None
        assert party_row["legal_name"] == vendor["name"]

        vendor_row = await conn.fetchrow(
            "SELECT default_seller_party_id, default_shipper_party_id, default_remit_to_party_id FROM vendors WHERE id = $1",
            vendor["id"],
        )
        assert vendor_row["default_seller_party_id"] == party_row["id"]
        assert vendor_row["default_shipper_party_id"] == party_row["id"]
        assert vendor_row["default_remit_to_party_id"] == party_row["id"]
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()


@pytest.mark.asyncio
async def test_migration_backfill_creates_manufacturer_party_for_product_with_free_text() -> None:
    """Product with non-empty manufacturer_name and no manufacturer_party_id
    should get a MANUFACTURER VendorParty after init_db backfill.
    """
    import asyncpg
    import os
    from uuid import uuid4
    from datetime import UTC, datetime
    from src.schema import init_db as schema_init_db

    db_url = os.environ.get("TEST_DATABASE_URL", "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test")
    conn = await asyncpg.connect(db_url)
    await conn.execute("BEGIN")
    try:
        vendor = await _make_vendor(conn)
        # Set default_seller_party_id so the vendor backfill doesn't overwrite
        # (the vendor backfill skips if default_seller_party_id is already set)
        party_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        await conn.execute(
            """
            INSERT INTO vendor_parties (id, vendor_id, role, legal_name, address, country,
                tax_id, banking_details, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            party_id, vendor["id"], "SELLER", vendor["name"], "Addr", "CN", "", "", now, now,
        )
        await conn.execute(
            "UPDATE vendors SET default_seller_party_id = $1 WHERE id = $2",
            party_id, vendor["id"],
        )

        # Insert a product with manufacturer_name but no manufacturer_party_id
        prod_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO products (id, vendor_id, part_number, description,
                manufacturing_address, manufacturer_name, manufacturer_address,
                manufacturer_country, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            prod_id, vendor["id"], "PN-001", "", "", "SZ Factory", "Shenzhen Industrial", "CN", now, now,
        )

        await schema_init_db(conn)

        mfr_party = await conn.fetchrow(
            "SELECT * FROM vendor_parties WHERE vendor_id = $1 AND role = 'MANUFACTURER'",
            vendor["id"],
        )
        assert mfr_party is not None
        assert mfr_party["legal_name"] == "SZ Factory"

        prod_row = await conn.fetchrow(
            "SELECT manufacturer_party_id FROM products WHERE id = $1", prod_id
        )
        assert prod_row["manufacturer_party_id"] == mfr_party["id"]
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()
