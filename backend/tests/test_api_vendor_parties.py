"""Iter 113: /api/v1/vendors/{id}/parties API tests."""
from __future__ import annotations

import pytest

from tests.conftest import make_test_vendor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_vendor_party(
    client,
    vendor_id: str,
    *,
    role: str = "SELLER",
    legal_name: str = "Test Seller",
    address: str = "Corp Ave, Singapore",
    country: str = "SG",
    tax_id: str = "",
    banking_details: str = "",
) -> dict:
    resp = await client.post(
        f"/api/v1/vendors/{vendor_id}/parties",
        json={
            "role": role,
            "legal_name": legal_name,
            "address": address,
            "country": country,
            "tax_id": tax_id,
            "banking_details": banking_details,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_vendor_party_admin_succeeds(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    vendor_id = vendor["id"]

    resp = await authenticated_client.post(
        f"/api/v1/vendors/{vendor_id}/parties",
        json={
            "role": "SELLER",
            "legal_name": "ACME Seller Ltd",
            "address": "100 Trade Blvd",
            "country": "HK",
            "tax_id": "HK-000123",
            "banking_details": "",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    expected_keys = {
        "id", "vendor_id", "role", "legal_name", "address",
        "country", "tax_id", "banking_details", "created_at", "updated_at",
    }
    assert set(data.keys()) == expected_keys
    assert data["vendor_id"] == vendor_id
    assert data["role"] == "SELLER"
    assert data["legal_name"] == "ACME Seller Ltd"
    assert data["country"] == "HK"
    assert data["tax_id"] == "HK-000123"


@pytest.mark.asyncio
async def test_create_vendor_party_rejects_invalid_country(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/vendors/{vendor['id']}/parties",
        json={
            "role": "SELLER",
            "legal_name": "Bad Co",
            "address": "Somewhere",
            "country": "ZZ",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_vendor_party_rejects_empty_legal_name(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    resp = await authenticated_client.post(
        f"/api/v1/vendors/{vendor['id']}/parties",
        json={
            "role": "SELLER",
            "legal_name": "  ",
            "address": "Somewhere",
            "country": "US",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_vendor_parties_admin_succeeds(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    vendor_id = vendor["id"]

    await _make_vendor_party(authenticated_client, vendor_id, role="SELLER", legal_name="Seller A", address="Addr A", country="US")
    await _make_vendor_party(authenticated_client, vendor_id, role="SHIPPER", legal_name="Shipper B", address="Addr B", country="CN")

    resp = await authenticated_client.get(f"/api/v1/vendors/{vendor_id}/parties")
    assert resp.status_code == 200
    parties = resp.json()
    assert len(parties) >= 2
    roles = {p["role"] for p in parties}
    assert "SELLER" in roles
    assert "SHIPPER" in roles


@pytest.mark.asyncio
async def test_patch_vendor_party_updates_fields(authenticated_client) -> None:
    import time
    vendor = await make_test_vendor(authenticated_client)
    vendor_id = vendor["id"]

    party = await _make_vendor_party(
        authenticated_client, vendor_id, role="SELLER",
        legal_name="Old Name", address="Old Addr", country="US",
    )
    party_id = party["id"]
    original_updated_at = party["updated_at"]

    time.sleep(0.02)
    resp = await authenticated_client.patch(
        f"/api/v1/vendors/{vendor_id}/parties/{party_id}",
        json={"legal_name": "New Name", "tax_id": "US-EIN-999"},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["legal_name"] == "New Name"
    assert updated["tax_id"] == "US-EIN-999"
    assert updated["updated_at"] > original_updated_at


@pytest.mark.asyncio
async def test_delete_unlinked_vendor_party_succeeds(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    party = await _make_vendor_party(
        authenticated_client, vendor["id"], role="REMIT_TO",
        legal_name="Factoring Ltd", address="Finance Ave", country="SG",
    )
    party_id = party["id"]

    resp = await authenticated_client.delete(
        f"/api/v1/vendors/{vendor['id']}/parties/{party_id}"
    )
    assert resp.status_code == 204

    # Confirm it's gone
    resp2 = await authenticated_client.get(
        f"/api/v1/vendors/{vendor['id']}/parties/{party_id}"
    )
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_referenced_vendor_party_returns_409(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    vendor_id = vendor["id"]

    party = await _make_vendor_party(
        authenticated_client, vendor_id, role="SELLER",
        legal_name="Linked Seller", address="Linked Ave", country="US",
    )
    party_id = party["id"]

    # Set as vendor default (links the party)
    resp = await authenticated_client.patch(
        f"/api/v1/vendors/{vendor_id}",
        json={"default_seller_party_id": party_id},
    )
    assert resp.status_code == 200, resp.text

    # Now delete should 409
    resp2 = await authenticated_client.delete(
        f"/api/v1/vendors/{vendor_id}/parties/{party_id}"
    )
    assert resp2.status_code == 409
    assert "referenced" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_vendor_sets_default_seller_party_id(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    vendor_id = vendor["id"]

    party = await _make_vendor_party(
        authenticated_client, vendor_id, role="SELLER",
        legal_name="Default Seller", address="Main St", country="US",
    )

    resp = await authenticated_client.patch(
        f"/api/v1/vendors/{vendor_id}",
        json={"default_seller_party_id": party["id"]},
    )
    assert resp.status_code == 200
    vendor_data = resp.json()
    assert vendor_data["default_seller_party_id"] == party["id"]


@pytest.mark.asyncio
async def test_patch_vendor_rejects_wrong_role_for_default(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    vendor_id = vendor["id"]

    # Create a MANUFACTURER party
    party = await _make_vendor_party(
        authenticated_client, vendor_id, role="MANUFACTURER",
        legal_name="Factory", address="Industrial Rd", country="CN",
    )

    # Try to set it as default_seller_party_id (wrong role)
    resp = await authenticated_client.patch(
        f"/api/v1/vendors/{vendor_id}",
        json={"default_seller_party_id": party["id"]},
    )
    assert resp.status_code == 422
    assert "role" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_vendor_rejects_party_from_other_vendor(authenticated_client) -> None:
    vendor_a = await make_test_vendor(authenticated_client, name="Vendor A")
    vendor_b = await make_test_vendor(authenticated_client, name="Vendor B", country="SG")

    # Party belongs to vendor_a
    party = await _make_vendor_party(
        authenticated_client, vendor_a["id"], role="SELLER",
        legal_name="A's Seller", address="Addr A", country="US",
    )

    # Try to assign to vendor_b
    resp = await authenticated_client.patch(
        f"/api/v1/vendors/{vendor_b['id']}",
        json={"default_seller_party_id": party["id"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_vendor_party_returns_404_for_unknown_vendor(authenticated_client) -> None:
    resp = await authenticated_client.post(
        "/api/v1/vendors/nonexistent-id/parties",
        json={"role": "SELLER", "legal_name": "Co", "address": "Addr", "country": "US"},
    )
    assert resp.status_code == 404
