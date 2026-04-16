from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_QT_BASE = {
    "name": "CE Mark",
    "description": "EU conformity marking",
    "target_market": "EU",
    "applies_to_category": "ELECTRONICS",
}


async def _create_qt(client: AsyncClient, name: str = "CE Mark", target_market: str = "EU") -> dict:
    resp = await client.post(
        "/api/v1/qualification-types",
        json={"name": name, "target_market": target_market},
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_vendor(client: AsyncClient, name: str = "Test Vendor") -> dict:
    resp = await client.post(
        "/api/v1/vendors/",
        json={"name": name, "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_product(client: AsyncClient, vendor_id: str, part_number: str = "PN-001") -> dict:
    resp = await client.post(
        "/api/v1/products/",
        json={"vendor_id": vendor_id, "part_number": part_number},
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_qualification_type_returns_201(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post("/api/v1/qualification-types", json=_QT_BASE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == _QT_BASE["name"]
    assert data["description"] == _QT_BASE["description"]
    assert data["target_market"] == _QT_BASE["target_market"]
    assert data["applies_to_category"] == _QT_BASE["applies_to_category"]
    assert "id" in data
    assert "created_at" in data


async def test_create_qualification_type_rejects_empty_name(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post(
        "/api/v1/qualification-types",
        json={"name": "", "target_market": "EU"},
    )
    assert resp.status_code == 422


async def test_create_qualification_type_rejects_empty_target_market(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.post(
        "/api/v1/qualification-types",
        json={"name": "CE Mark", "target_market": ""},
    )
    assert resp.status_code == 422


async def test_create_duplicate_name_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    await _create_qt(client, name="Unique Mark")
    resp = await client.post(
        "/api/v1/qualification-types",
        json={"name": "Unique Mark", "target_market": "EU"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


async def test_list_qualification_types(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    await _create_qt(client, name="CE Mark")
    await _create_qt(client, name="FDA 510k", target_market="US")
    resp = await client.get("/api/v1/qualification-types")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = {item["name"] for item in data}
    # CE Mark and FDA 510k must be present (QUALITY_CERTIFICATE may also exist from schema migration)
    assert {"CE Mark", "FDA 510k"}.issubset(names)
    for item in data:
        assert set(item.keys()) == {"id", "name", "target_market", "applies_to_category"}


# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------


async def test_get_qualification_type_by_id(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    created = await _create_qt(client, name="CE Mark")
    resp = await client.get(f"/api/v1/qualification-types/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["name"] == "CE Mark"
    assert "description" in data
    assert "created_at" in data


async def test_get_nonexistent_qualification_type_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.get("/api/v1/qualification-types/fake-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_qualification_type(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    created = await _create_qt(client)
    resp = await client.patch(
        f"/api/v1/qualification-types/{created['id']}",
        json={"name": "CE Mark 2024", "description": "Updated"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "CE Mark 2024"
    assert data["description"] == "Updated"
    assert data["id"] == created["id"]


async def test_update_nonexistent_qualification_type_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.patch(
        "/api/v1/qualification-types/fake-id",
        json={"name": "New Name"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


async def test_delete_qualification_type_returns_204(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    created = await _create_qt(client)
    resp = await client.delete(f"/api/v1/qualification-types/{created['id']}")
    assert resp.status_code == 204
    # Confirm it's gone
    get_resp = await client.get(f"/api/v1/qualification-types/{created['id']}")
    assert get_resp.status_code == 404


async def test_delete_nonexistent_qualification_type_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    resp = await client.delete("/api/v1/qualification-types/fake-id")
    assert resp.status_code == 404


async def test_delete_in_use_qualification_type_returns_409(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    qt = await _create_qt(client)
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])
    # Assign qualification to product
    assign_resp = await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": qt["id"]},
    )
    assert assign_resp.status_code == 201
    # Now delete should fail
    resp = await client.delete(f"/api/v1/qualification-types/{qt['id']}")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Product qualifications sub-resource
# ---------------------------------------------------------------------------


async def test_assign_qualification_to_product(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    qt = await _create_qt(client)
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])

    resp = await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": qt["id"]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["product_id"] == product["id"]
    assert data["qualification_type_id"] == qt["id"]


async def test_list_product_qualifications(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    qt1 = await _create_qt(client, name="CE Mark")
    qt2 = await _create_qt(client, name="FDA 510k", target_market="US")
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])

    await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": qt1["id"]},
    )
    await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": qt2["id"]},
    )

    resp = await client.get(f"/api/v1/products/{product['id']}/qualifications")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    names = {item["name"] for item in data}
    assert names == {"CE Mark", "FDA 510k"}


async def test_remove_qualification_from_product(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    qt = await _create_qt(client)
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])

    await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": qt["id"]},
    )
    resp = await client.delete(f"/api/v1/products/{product['id']}/qualifications/{qt['id']}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/products/{product['id']}/qualifications")
    assert list_resp.json() == []


async def test_assign_same_qualification_twice_is_idempotent(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    qt = await _create_qt(client)
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])

    await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": qt["id"]},
    )
    # Second assign should not error (ON CONFLICT DO NOTHING)
    resp = await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": qt["id"]},
    )
    assert resp.status_code == 201

    list_resp = await client.get(f"/api/v1/products/{product['id']}/qualifications")
    assert len(list_resp.json()) == 1


async def test_product_response_includes_qualifications(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    qt = await _create_qt(client, name="CE Mark")
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])

    await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": qt["id"]},
    )

    resp = await client.get(f"/api/v1/products/{product['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["qualifications"]) == 1
    assert data["qualifications"][0]["name"] == "CE Mark"
    assert data["qualifications"][0]["id"] == qt["id"]


async def test_product_list_includes_qualifications(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    qt = await _create_qt(client, name="CE Mark")
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])

    await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": qt["id"]},
    )

    resp = await client.get("/api/v1/products/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert len(data[0]["qualifications"]) == 1
    assert data[0]["qualifications"][0]["name"] == "CE Mark"


async def test_assign_nonexistent_qualification_returns_404(authenticated_client: AsyncClient) -> None:
    client = authenticated_client
    vendor = await _create_vendor(client)
    product = await _create_product(client, vendor["id"])

    resp = await client.post(
        f"/api/v1/products/{product['id']}/qualifications",
        json={"qualification_type_id": "fake-qt-id"},
    )
    assert resp.status_code == 404
