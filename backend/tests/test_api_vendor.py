from __future__ import annotations

import pytest
import aiosqlite
from httpx import AsyncClient

from src.domain.vendor import VendorStatus
from src.schema import init_db

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

_LINE_ITEM: dict = {
    "part_number": "PN-001",
    "description": "Widget A",
    "quantity": 10,
    "uom": "EA",
    "unit_price": "5.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_PO_BASE: dict = {
    "buyer_name": "TurboTonic Ltd",
    "buyer_country": "US",
    "ship_to_address": "123 Main St",
    "payment_terms": "TT",
    "currency": "USD",
    "issued_date": "2026-03-16T00:00:00Z",
    "required_delivery_date": "2026-04-01T00:00:00Z",
    "terms_and_conditions": "Standard T&C",
    "incoterm": "FOB",
    "port_of_loading": "USLAX",
    "port_of_discharge": "CNSHA",
    "country_of_origin": "US",
    "country_of_destination": "CN",
    "line_items": [_LINE_ITEM],
}


async def _create_vendor(client: AsyncClient, name: str = "Test Vendor", country: str = "US", vendor_type: str = "PROCUREMENT") -> dict:
    resp = await client.post("/api/v1/vendors/", json={"name": name, "country": country, "vendor_type": vendor_type})
    assert resp.status_code == 201
    return resp.json()


async def _create_po(client: AsyncClient, vendor_id: str) -> dict:
    payload = {**_PO_BASE, "vendor_id": vendor_id}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Vendor create
# ---------------------------------------------------------------------------


async def test_create_vendor_returns_201(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/vendors/", json={"name": "Acme Corp", "country": "US", "vendor_type": "PROCUREMENT"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corp"
    assert data["country"] == "US"
    assert data["status"] == VendorStatus.ACTIVE.value
    assert "id" in data


async def test_create_vendor_rejects_empty_name(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/vendors/", json={"name": "", "country": "US", "vendor_type": "PROCUREMENT"})
    assert resp.status_code == 422


async def test_create_vendor_with_valid_country_code_returns_201(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/vendors/", json={"name": "Valid Country Vendor", "country": "DE", "vendor_type": "PROCUREMENT"})
    assert resp.status_code == 201
    assert resp.json()["country"] == "DE"


async def test_create_vendor_with_invalid_country_code_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/vendors/", json={"name": "Bad Country Vendor", "country": "XX", "vendor_type": "PROCUREMENT"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Vendor list
# ---------------------------------------------------------------------------


async def test_list_vendors_returns_array(client: AsyncClient) -> None:
    await _create_vendor(client, name="Vendor A")
    await _create_vendor(client, name="Vendor B")
    resp = await client.get("/api/v1/vendors/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


async def test_list_vendors_filters_by_status(client: AsyncClient) -> None:
    vendor = await _create_vendor(client, name="Active Vendor")
    inactive_vendor = await _create_vendor(client, name="Inactive Vendor")
    await client.post(f"/api/v1/vendors/{inactive_vendor['id']}/deactivate")

    resp = await client.get("/api/v1/vendors/", params={"status": "ACTIVE"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == vendor["id"]
    assert data[0]["status"] == VendorStatus.ACTIVE.value


# ---------------------------------------------------------------------------
# Vendor detail
# ---------------------------------------------------------------------------


async def test_get_vendor_by_id(client: AsyncClient) -> None:
    created = await _create_vendor(client, name="Detail Vendor", country="DE")
    resp = await client.get(f"/api/v1/vendors/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["name"] == "Detail Vendor"
    assert data["country"] == "DE"


async def test_get_nonexistent_vendor_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/vendors/fake-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Vendor deactivate
# ---------------------------------------------------------------------------


async def test_deactivate_vendor(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    resp = await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == VendorStatus.INACTIVE.value


async def test_deactivate_already_inactive_returns_409(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    resp = await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Vendor reactivate
# ---------------------------------------------------------------------------


async def test_reactivate_vendor(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    resp = await client.post(f"/api/v1/vendors/{vendor['id']}/reactivate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == VendorStatus.ACTIVE.value


async def test_reactivate_already_active_returns_409(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    resp = await client.post(f"/api/v1/vendors/{vendor['id']}/reactivate")
    assert resp.status_code == 409


async def test_reactivate_nonexistent_vendor_returns_404(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/vendors/fake-id/reactivate")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PO creation with vendor validation
# ---------------------------------------------------------------------------


async def test_create_po_with_inactive_vendor_returns_422(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    await client.post(f"/api/v1/vendors/{vendor['id']}/deactivate")
    payload = {**_PO_BASE, "vendor_id": vendor["id"]}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


async def test_create_po_with_nonexistent_vendor_returns_422(client: AsyncClient) -> None:
    payload = {**_PO_BASE, "vendor_id": "nonexistent-vendor-id"}
    resp = await client.post("/api/v1/po/", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PO response includes vendor and buyer fields
# ---------------------------------------------------------------------------


async def test_po_response_includes_buyer_fields(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    po = await _create_po(client, vendor_id=vendor["id"])
    assert po["buyer_name"] == "TurboTonic Ltd"
    assert po["buyer_country"] == "US"


async def test_po_response_includes_vendor_name(client: AsyncClient) -> None:
    vendor = await _create_vendor(client, name="Global Parts Co", country="DE")
    po = await _create_po(client, vendor_id=vendor["id"])
    assert po["vendor_name"] == "Global Parts Co"
    assert po["vendor_country"] == "DE"


async def test_po_list_includes_vendor_name(client: AsyncClient) -> None:
    vendor = await _create_vendor(client, name="List Vendor", country="JP")
    await _create_po(client, vendor_id=vendor["id"])
    resp = await client.get("/api/v1/po/")
    assert resp.status_code == 200
    data = resp.json()
    items = data["items"]
    assert data["total"] == 1
    assert len(items) == 1
    assert items[0]["vendor_name"] == "List Vendor"
    assert items[0]["vendor_country"] == "JP"


# ---------------------------------------------------------------------------
# Vendor migration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_migrate_vendors_creates_records_and_rewrites_po_vendor_ids() -> None:
    acme = "Acme Corp"
    beta = "Beta LLC"

    async with aiosqlite.connect(":memory:") as conn:
        # Create the purchase_orders table without running the full init_db,
        # so we can insert free-text vendor_id values before migration runs.
        await conn.execute(
            """
            CREATE TABLE purchase_orders (
                id                     TEXT PRIMARY KEY,
                po_number              TEXT UNIQUE NOT NULL,
                status                 TEXT NOT NULL,
                vendor_id              TEXT NOT NULL,
                ship_to_address        TEXT,
                payment_terms          TEXT,
                currency               TEXT NOT NULL,
                issued_date            TEXT NOT NULL,
                required_delivery_date TEXT NOT NULL,
                terms_and_conditions   TEXT,
                incoterm               TEXT,
                port_of_loading        TEXT,
                port_of_discharge      TEXT,
                country_of_origin      TEXT,
                country_of_destination TEXT,
                created_at             TEXT NOT NULL,
                updated_at             TEXT NOT NULL
            )
            """
        )
        now = "2026-01-01T00:00:00"
        await conn.executemany(
            """
            INSERT INTO purchase_orders
                (id, po_number, status, vendor_id, currency, issued_date, required_delivery_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("po-1", "PO-0001", "DRAFT", acme, "USD", now, now, now, now),
                ("po-2", "PO-0002", "DRAFT", acme, "USD", now, now, now, now),
                ("po-3", "PO-0003", "DRAFT", beta, "USD", now, now, now, now),
            ],
        )
        await conn.commit()

        # init_db creates remaining tables and runs _migrate_vendors.
        await init_db(conn)

        # Vendors table must have exactly 2 records.
        async with conn.execute("SELECT name FROM vendors ORDER BY name") as cur:
            vendor_rows = await cur.fetchall()
        vendor_names = [r[0] for r in vendor_rows]
        assert vendor_names == [acme, beta], f"expected [{acme!r}, {beta!r}], got {vendor_names!r}"

        # All PO vendor_id values must now be UUIDs (36-char strings).
        async with conn.execute("SELECT id, vendor_id FROM purchase_orders ORDER BY id") as cur:
            po_rows = await cur.fetchall()
        po_map = {row[0]: row[1] for row in po_rows}
        for po_id, vendor_id in po_map.items():
            assert len(vendor_id) == 36, f"PO {po_id} vendor_id is not a UUID: {vendor_id!r}"

        # Both Acme POs must share the same vendor UUID.
        assert po_map["po-1"] == po_map["po-2"], (
            f"po-1 and po-2 should share a vendor UUID; got {po_map['po-1']!r} and {po_map['po-2']!r}"
        )

        # Acme and Beta POs must have different vendor UUIDs.
        assert po_map["po-1"] != po_map["po-3"], (
            "Acme and Beta should have distinct vendor UUIDs"
        )


# ---------------------------------------------------------------------------
# Reference data endpoint
# ---------------------------------------------------------------------------


async def test_reference_data_returns_all_sets(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reference-data/")
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {"currencies", "incoterms", "payment_terms", "countries", "ports", "vendor_types", "po_types"}
    assert set(data.keys()) == expected_keys
    for key in expected_keys:
        assert len(data[key]) > 0
        first = data[key][0]
        assert "code" in first
        assert "label" in first
