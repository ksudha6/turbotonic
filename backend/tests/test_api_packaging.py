from __future__ import annotations

import pytest

from src.domain.packaging import PackagingSpecStatus
from src.domain.product import Product
from src.domain.vendor import Vendor, VendorStatus, VendorType
from src.product_repository import ProductRepository
from src.vendor_repository import VendorRepository

pytestmark = pytest.mark.asyncio

MARKETPLACE = "AMAZON"
SPEC_NAME = "FNSKU Label"
DESCRIPTION = "Label requirements for FNSKU"
REQUIREMENTS_TEXT = "300 DPI, 1x2 inch, PDF format"


async def _create_vendor_and_product(client) -> tuple[str, str]:
    """Create a vendor and product; return (vendor_id, product_id)."""
    vendor_resp = await client.post(
        "/api/v1/vendors/",
        json={
            "name": "Test Vendor",
            "country": "US",
            "vendor_type": "PROCUREMENT",
            "address": "123 Main St",
            "account_details": "",
        },
    )
    assert vendor_resp.status_code == 201
    vendor_id = vendor_resp.json()["id"]

    product_resp = await client.post(
        "/api/v1/products/",
        json={
            "vendor_id": vendor_id,
            "part_number": "PART-001",
            "description": "Test Product",
            "requires_certification": False,
            "manufacturing_address": "",
        },
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]
    return vendor_id, product_id


async def _create_spec(client, product_id: str, marketplace: str = MARKETPLACE, spec_name: str = SPEC_NAME):
    return await client.post(
        "/api/v1/packaging-specs/",
        json={
            "product_id": product_id,
            "marketplace": marketplace,
            "spec_name": spec_name,
            "description": DESCRIPTION,
            "requirements_text": REQUIREMENTS_TEXT,
        },
    )


async def test_create_returns_201(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    resp = await _create_spec(authenticated_client, product_id)
    assert resp.status_code == 201
    body = resp.json()
    expected = {
        "product_id": product_id,
        "marketplace": MARKETPLACE,
        "spec_name": SPEC_NAME,
        "description": DESCRIPTION,
        "requirements_text": REQUIREMENTS_TEXT,
        "status": PackagingSpecStatus.PENDING.value,
    }
    for key, value in expected.items():
        assert body[key] == value, f"body[{key!r}] = {body[key]!r}, want {value!r}"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_empty_product_id_returns_422(authenticated_client):
    resp = await authenticated_client.post(
        "/api/v1/packaging-specs/",
        json={"product_id": "", "marketplace": MARKETPLACE, "spec_name": SPEC_NAME},
    )
    assert resp.status_code == 422


async def test_create_whitespace_product_id_returns_422(authenticated_client):
    resp = await authenticated_client.post(
        "/api/v1/packaging-specs/",
        json={"product_id": "   ", "marketplace": MARKETPLACE, "spec_name": SPEC_NAME},
    )
    assert resp.status_code == 422


async def test_create_empty_marketplace_returns_422(authenticated_client):
    resp = await authenticated_client.post(
        "/api/v1/packaging-specs/",
        json={"product_id": "prod-1", "marketplace": "", "spec_name": SPEC_NAME},
    )
    assert resp.status_code == 422


async def test_create_empty_spec_name_returns_422(authenticated_client):
    resp = await authenticated_client.post(
        "/api/v1/packaging-specs/",
        json={"product_id": "prod-1", "marketplace": MARKETPLACE, "spec_name": ""},
    )
    assert resp.status_code == 422


async def test_create_whitespace_spec_name_returns_422(authenticated_client):
    resp = await authenticated_client.post(
        "/api/v1/packaging-specs/",
        json={"product_id": "prod-1", "marketplace": MARKETPLACE, "spec_name": "   "},
    )
    assert resp.status_code == 422


async def test_create_nonexistent_product_returns_404(authenticated_client):
    resp = await authenticated_client.post(
        "/api/v1/packaging-specs/",
        json={
            "product_id": "nonexistent-product",
            "marketplace": MARKETPLACE,
            "spec_name": SPEC_NAME,
        },
    )
    assert resp.status_code == 404


async def test_create_duplicate_returns_409(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    resp1 = await _create_spec(authenticated_client, product_id)
    assert resp1.status_code == 201

    resp2 = await _create_spec(authenticated_client, product_id)
    assert resp2.status_code == 409


async def test_list_by_product_id(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    await _create_spec(authenticated_client, product_id, marketplace="AMAZON", spec_name="FNSKU Label")
    await _create_spec(authenticated_client, product_id, marketplace="DIRECT", spec_name="Suffocation Warning")

    resp = await authenticated_client.get(
        "/api/v1/packaging-specs/", params={"product_id": product_id}
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    spec_names = {item["spec_name"] for item in items}
    assert spec_names == {"FNSKU Label", "Suffocation Warning"}


async def test_list_by_product_id_and_marketplace(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    await _create_spec(authenticated_client, product_id, marketplace="AMAZON", spec_name="FNSKU Label")
    await _create_spec(authenticated_client, product_id, marketplace="DIRECT", spec_name="Suffocation Warning")

    resp = await authenticated_client.get(
        "/api/v1/packaging-specs/",
        params={"product_id": product_id, "marketplace": "AMAZON"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["spec_name"] == "FNSKU Label"
    assert items[0]["marketplace"] == "AMAZON"


async def test_list_without_product_id_returns_422(authenticated_client):
    resp = await authenticated_client.get("/api/v1/packaging-specs/")
    assert resp.status_code == 422


async def test_get_by_id(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    create_resp = await _create_spec(authenticated_client, product_id)
    spec_id = create_resp.json()["id"]

    resp = await authenticated_client.get(f"/api/v1/packaging-specs/{spec_id}")
    assert resp.status_code == 200
    body = resp.json()
    expected = {
        "id": spec_id,
        "product_id": product_id,
        "marketplace": MARKETPLACE,
        "spec_name": SPEC_NAME,
        "description": DESCRIPTION,
        "requirements_text": REQUIREMENTS_TEXT,
        "status": PackagingSpecStatus.PENDING.value,
    }
    for key, value in expected.items():
        assert body[key] == value, f"body[{key!r}] = {body[key]!r}, want {value!r}"
    assert "created_at" in body
    assert "updated_at" in body


async def test_get_nonexistent_returns_404(authenticated_client):
    resp = await authenticated_client.get("/api/v1/packaging-specs/nonexistent-id")
    assert resp.status_code == 404


async def test_update_changes_fields(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    create_resp = await _create_spec(authenticated_client, product_id)
    spec_id = create_resp.json()["id"]
    original_updated_at = create_resp.json()["updated_at"]

    new_spec_name = "Updated Label"
    new_description = "Updated description"
    new_requirements = "New requirements"

    resp = await authenticated_client.patch(
        f"/api/v1/packaging-specs/{spec_id}",
        json={
            "spec_name": new_spec_name,
            "description": new_description,
            "requirements_text": new_requirements,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["spec_name"] == new_spec_name
    assert body["description"] == new_description
    assert body["requirements_text"] == new_requirements
    # unchanged fields stay
    assert body["product_id"] == product_id
    assert body["marketplace"] == MARKETPLACE
    assert body["status"] == PackagingSpecStatus.PENDING.value
    assert body["updated_at"] >= original_updated_at


async def test_update_partial_leaves_others_unchanged(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    create_resp = await _create_spec(authenticated_client, product_id)
    spec_id = create_resp.json()["id"]

    resp = await authenticated_client.patch(
        f"/api/v1/packaging-specs/{spec_id}",
        json={"description": "only description changed"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["spec_name"] == SPEC_NAME
    assert body["requirements_text"] == REQUIREMENTS_TEXT
    assert body["description"] == "only description changed"


async def test_delete_pending_returns_204(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    create_resp = await _create_spec(authenticated_client, product_id)
    spec_id = create_resp.json()["id"]

    del_resp = await authenticated_client.delete(f"/api/v1/packaging-specs/{spec_id}")
    assert del_resp.status_code == 204

    get_resp = await authenticated_client.get(f"/api/v1/packaging-specs/{spec_id}")
    assert get_resp.status_code == 404


async def test_delete_nonexistent_returns_404(authenticated_client):
    resp = await authenticated_client.delete("/api/v1/packaging-specs/nonexistent-id")
    assert resp.status_code == 404


PDF_CONTENT = b"%PDF-1.4 test packaging file content"


async def _upload_file(client, spec_id: str, content: bytes = PDF_CONTENT, filename: str = "packaging.pdf"):
    return await client.post(
        f"/api/v1/packaging-specs/{spec_id}/upload",
        files={"file": (filename, content, "application/pdf")},
    )


async def test_upload_file_transitions_to_collected(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    create_resp = await _create_spec(authenticated_client, product_id)
    spec_id = create_resp.json()["id"]

    resp = await _upload_file(authenticated_client, spec_id)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == PackagingSpecStatus.COLLECTED.value
    assert body["document_id"] is not None
    assert body["id"] == spec_id


async def test_upload_file_already_collected_replaces_document(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    create_resp = await _create_spec(authenticated_client, product_id)
    spec_id = create_resp.json()["id"]

    first_resp = await _upload_file(authenticated_client, spec_id, filename="first.pdf")
    assert first_resp.status_code == 200
    first_doc_id = first_resp.json()["document_id"]

    second_resp = await _upload_file(authenticated_client, spec_id, filename="second.pdf")
    assert second_resp.status_code == 200
    body = second_resp.json()
    assert body["status"] == PackagingSpecStatus.COLLECTED.value
    assert body["document_id"] is not None
    assert body["document_id"] != first_doc_id


async def test_upload_file_nonexistent_spec_returns_404(authenticated_client):
    resp = await _upload_file(authenticated_client, "nonexistent-spec-id")
    assert resp.status_code == 404


async def test_delete_collected_spec_returns_409(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    create_resp = await _create_spec(authenticated_client, product_id)
    spec_id = create_resp.json()["id"]

    upload_resp = await _upload_file(authenticated_client, spec_id)
    assert upload_resp.status_code == 200
    assert upload_resp.json()["status"] == PackagingSpecStatus.COLLECTED.value

    del_resp = await authenticated_client.delete(f"/api/v1/packaging-specs/{spec_id}")
    assert del_resp.status_code == 409


async def test_upload_activity_event_recorded(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    create_resp = await _create_spec(authenticated_client, product_id)
    spec_id = create_resp.json()["id"]

    upload_resp = await _upload_file(authenticated_client, spec_id)
    assert upload_resp.status_code == 200

    activity_resp = await authenticated_client.get(
        "/api/v1/activity/", params={"entity_type": "PACKAGING", "entity_id": spec_id}
    )
    assert activity_resp.status_code == 200
    events = activity_resp.json()
    event_names = [e["event"] for e in events]
    assert "PACKAGING_COLLECTED" in event_names


async def test_packaging_readiness_all_collected(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    create_resp = await _create_spec(authenticated_client, product_id, spec_name="Label A")
    spec_id = create_resp.json()["id"]
    await _upload_file(authenticated_client, spec_id)

    resp = await authenticated_client.get(
        f"/api/v1/products/{product_id}/packaging-readiness",
        params={"marketplace": MARKETPLACE},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["product_id"] == product_id
    assert body["marketplace"] == MARKETPLACE
    assert body["total_specs"] == 1
    assert body["collected_specs"] == 1
    assert body["is_ready"] is True
    assert len(body["specs"]) == 1
    assert body["specs"][0]["status"] == PackagingSpecStatus.COLLECTED.value


async def test_packaging_readiness_some_missing(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    spec1_resp = await _create_spec(authenticated_client, product_id, spec_name="Label A")
    spec1_id = spec1_resp.json()["id"]
    await _upload_file(authenticated_client, spec1_id)

    await _create_spec(authenticated_client, product_id, spec_name="Label B")

    resp = await authenticated_client.get(
        f"/api/v1/products/{product_id}/packaging-readiness",
        params={"marketplace": MARKETPLACE},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_specs"] == 2
    assert body["collected_specs"] == 1
    assert body["is_ready"] is False


async def test_packaging_readiness_no_specs(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)

    resp = await authenticated_client.get(
        f"/api/v1/products/{product_id}/packaging-readiness",
        params={"marketplace": MARKETPLACE},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_specs"] == 0
    assert body["collected_specs"] == 0
    assert body["is_ready"] is False


async def test_packaging_readiness_missing_marketplace_param_returns_422(authenticated_client):
    _, product_id = await _create_vendor_and_product(authenticated_client)
    resp = await authenticated_client.get(
        f"/api/v1/products/{product_id}/packaging-readiness"
    )
    assert resp.status_code == 422
