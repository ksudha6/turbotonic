from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_vendor(client: AsyncClient, name: str = "Test Vendor", country: str = "CN") -> dict:
    resp = await client.post("/api/v1/vendors/", json={"name": name, "country": country})
    assert resp.status_code == 201
    return resp.json()


async def _create_po(
    client: AsyncClient,
    vendor_id: str,
    currency: str = "USD",
    line_items: list[dict] | None = None,
) -> dict:
    if line_items is None:
        line_items = [
            {
                "part_number": "P1",
                "description": "Part",
                "quantity": 10,
                "uom": "PCS",
                "unit_price": "100.00",
                "hs_code": "8471",
                "country_of_origin": "CN",
            }
        ]
    body = {
        "vendor_id": vendor_id,
        "buyer_name": "TurboTonic Ltd",
        "buyer_country": "US",
        "ship_to_address": "123 Main St",
        "payment_terms": "TT",
        "currency": currency,
        "issued_date": "2026-03-24T00:00:00+00:00",
        "required_delivery_date": "2026-04-24T00:00:00+00:00",
        "terms_and_conditions": "Standard terms",
        "incoterm": "FOB",
        "port_of_loading": "CNSHA",
        "port_of_discharge": "USLAX",
        "country_of_origin": "CN",
        "country_of_destination": "US",
        "line_items": line_items,
    }
    resp = await client.post("/api/v1/po/", json=body)
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_dashboard_empty_state(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["po_summary"] == []
    assert data["vendor_summary"] == {"active": 0, "inactive": 0}
    assert data["recent_pos"] == []


@pytest.mark.asyncio
async def test_dashboard_po_counts_by_status(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    vendor_id = vendor["id"]

    # Create 2 DRAFT POs
    await _create_po(client, vendor_id)
    await _create_po(client, vendor_id)

    # Create 1 PENDING PO (submit it)
    po = await _create_po(client, vendor_id)
    submit_resp = await client.post(f"/api/v1/po/{po['id']}/submit")
    assert submit_resp.status_code == 200

    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()

    summary_by_status = {item["status"]: item for item in data["po_summary"]}
    assert "DRAFT" in summary_by_status
    assert summary_by_status["DRAFT"]["count"] == 2
    assert "PENDING" in summary_by_status
    assert summary_by_status["PENDING"]["count"] == 1


@pytest.mark.asyncio
async def test_dashboard_usd_conversion(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    vendor_id = vendor["id"]

    # 10 units at 100.00 EUR = 1000 EUR total
    line_items = [
        {
            "part_number": "P1",
            "description": "Part",
            "quantity": 10,
            "uom": "PCS",
            "unit_price": "100.00",
            "hs_code": "8471",
            "country_of_origin": "CN",
        }
    ]
    await _create_po(client, vendor_id, currency="EUR", line_items=line_items)

    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()

    summary_by_status = {item["status"]: item for item in data["po_summary"]}
    # 1000 EUR * 1.08 = 1080.00 USD
    assert summary_by_status["DRAFT"]["total_usd"] == "1080.00"


@pytest.mark.asyncio
async def test_dashboard_multi_currency_same_status(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    vendor_id = vendor["id"]

    # USD PO: 5 units at 100.00 = 500 USD
    usd_items = [
        {
            "part_number": "P1",
            "description": "Part",
            "quantity": 5,
            "uom": "PCS",
            "unit_price": "100.00",
            "hs_code": "8471",
            "country_of_origin": "CN",
        }
    ]
    await _create_po(client, vendor_id, currency="USD", line_items=usd_items)

    # EUR PO: 10 units at 100.00 = 1000 EUR
    eur_items = [
        {
            "part_number": "P2",
            "description": "Part",
            "quantity": 10,
            "uom": "PCS",
            "unit_price": "100.00",
            "hs_code": "8471",
            "country_of_origin": "CN",
        }
    ]
    await _create_po(client, vendor_id, currency="EUR", line_items=eur_items)

    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()

    summary_by_status = {item["status"]: item for item in data["po_summary"]}
    # 500 * 1.0 + 1000 * 1.08 = 500 + 1080 = 1580.00 USD
    assert summary_by_status["DRAFT"]["total_usd"] == "1580.00"


@pytest.mark.asyncio
async def test_dashboard_vendor_counts(client: AsyncClient) -> None:
    # Create 2 active vendors
    v1 = await _create_vendor(client, name="Vendor One")
    v2 = await _create_vendor(client, name="Vendor Two")

    # Deactivate one vendor
    deactivate_resp = await client.post(f"/api/v1/vendors/{v2['id']}/deactivate")
    assert deactivate_resp.status_code == 200

    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["vendor_summary"]["active"] == 1
    assert data["vendor_summary"]["inactive"] == 1


@pytest.mark.asyncio
async def test_dashboard_recent_pos_limit(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    vendor_id = vendor["id"]

    # Create 12 POs
    for _ in range(12):
        await _create_po(client, vendor_id)

    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["recent_pos"]) == 10


@pytest.mark.asyncio
async def test_dashboard_recent_pos_order(client: AsyncClient) -> None:
    vendor = await _create_vendor(client)
    vendor_id = vendor["id"]

    po1 = await _create_po(client, vendor_id)
    po2 = await _create_po(client, vendor_id)

    # Submit po2 to update its updated_at timestamp more recently
    submit_resp = await client.post(f"/api/v1/po/{po2['id']}/submit")
    assert submit_resp.status_code == 200

    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()

    recent_ids = [item["id"] for item in data["recent_pos"]]
    # po2 was updated most recently, so it should come first
    assert recent_ids[0] == po2["id"]


@pytest.mark.asyncio
async def test_dashboard_recent_pos_has_vendor_name(client: AsyncClient) -> None:
    vendor_name = "Acme Corp"
    vendor = await _create_vendor(client, name=vendor_name)
    vendor_id = vendor["id"]

    await _create_po(client, vendor_id)

    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["recent_pos"]) == 1
    assert data["recent_pos"][0]["vendor_name"] == vendor_name
