from __future__ import annotations

import io

import pytest

from src.domain.certificate import CertificateStatus

pytestmark = pytest.mark.asyncio

CERT_NUMBER = "CERT-2024-001"
ISSUER = "Bureau Veritas"
TARGET_MARKET = "EU"
ISSUE_DATE = "2024-01-01T00:00:00+00:00"
EXPIRY_DATE_FUTURE = "2099-12-31T00:00:00+00:00"
EXPIRY_DATE_PAST = "2020-01-01T00:00:00+00:00"


async def _create_vendor(client) -> str:
    resp = await client.post(
        "/api/v1/vendors/",
        json={"name": "Test Vendor", "country": "CN", "vendor_type": "PROCUREMENT"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_product(client, vendor_id: str) -> str:
    resp = await client.post(
        "/api/v1/products/",
        json={
            "vendor_id": vendor_id,
            "part_number": "PART-001",
            "description": "Test Product",
            "requires_certification": False,
            "manufacturing_address": "",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_qualification_type(client) -> str:
    resp = await client.post(
        "/api/v1/qualification-types",
        json={
            "name": "CE Mark",
            "description": "European conformity",
            "target_market": "EU",
            "applies_to_category": "",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_cert(client, product_id: str, qt_id: str, **overrides):
    payload = {
        "product_id": product_id,
        "qualification_type_id": qt_id,
        "cert_number": CERT_NUMBER,
        "issuer": ISSUER,
        "issue_date": ISSUE_DATE,
        "target_market": TARGET_MARKET,
    }
    payload.update(overrides)
    return await client.post("/api/v1/certificates/", json=payload)


async def test_create_returns_201(authenticated_client):
    vendor_id = await _create_vendor(authenticated_client)
    product_id = await _create_product(authenticated_client, vendor_id)
    qt_id = await _create_qualification_type(authenticated_client)

    resp = await _create_cert(authenticated_client, product_id, qt_id)
    assert resp.status_code == 201
    body = resp.json()
    expected = {
        "product_id": product_id,
        "qualification_type_id": qt_id,
        "cert_number": CERT_NUMBER,
        "issuer": ISSUER,
        "target_market": TARGET_MARKET,
        "status": CertificateStatus.PENDING.value,
        "document_id": None,
        "testing_lab": "",
        "test_date": None,
        "expiry_date": None,
    }
    for key, value in expected.items():
        assert body[key] == value, f"body[{key!r}] = {body[key]!r}, want {value!r}"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_nonexistent_product_returns_404(authenticated_client):
    qt_id = await _create_qualification_type(authenticated_client)
    resp = await _create_cert(authenticated_client, "nonexistent-product", qt_id)
    assert resp.status_code == 404


async def test_create_nonexistent_qualification_type_returns_404(authenticated_client):
    vendor_id = await _create_vendor(authenticated_client)
    product_id = await _create_product(authenticated_client, vendor_id)
    resp = await _create_cert(authenticated_client, product_id, "nonexistent-qt")
    assert resp.status_code == 404


async def test_list_by_product_id(authenticated_client):
    vendor_id = await _create_vendor(authenticated_client)
    product_id = await _create_product(authenticated_client, vendor_id)
    qt_id = await _create_qualification_type(authenticated_client)

    await _create_cert(authenticated_client, product_id, qt_id, cert_number="CERT-001")
    await _create_cert(authenticated_client, product_id, qt_id, cert_number="CERT-002")

    resp = await authenticated_client.get(
        "/api/v1/certificates/", params={"product_id": product_id}
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    cert_numbers = {item["cert_number"] for item in items}
    assert cert_numbers == {"CERT-001", "CERT-002"}


async def test_get_by_id_includes_computed_status(authenticated_client):
    vendor_id = await _create_vendor(authenticated_client)
    product_id = await _create_product(authenticated_client, vendor_id)
    qt_id = await _create_qualification_type(authenticated_client)

    create_resp = await _create_cert(authenticated_client, product_id, qt_id)
    cert_id = create_resp.json()["id"]

    resp = await authenticated_client.get(f"/api/v1/certificates/{cert_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == cert_id
    assert body["status"] == CertificateStatus.PENDING.value


async def test_get_nonexistent_returns_404(authenticated_client):
    resp = await authenticated_client.get("/api/v1/certificates/nonexistent-id")
    assert resp.status_code == 404


async def test_update_cert_number(authenticated_client):
    vendor_id = await _create_vendor(authenticated_client)
    product_id = await _create_product(authenticated_client, vendor_id)
    qt_id = await _create_qualification_type(authenticated_client)

    create_resp = await _create_cert(authenticated_client, product_id, qt_id)
    cert_id = create_resp.json()["id"]
    original_updated_at = create_resp.json()["updated_at"]

    new_cert_number = "CERT-UPDATED-999"
    resp = await authenticated_client.patch(
        f"/api/v1/certificates/{cert_id}",
        json={"cert_number": new_cert_number},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cert_number"] == new_cert_number
    assert body["issuer"] == ISSUER
    assert body["updated_at"] >= original_updated_at


async def test_mark_valid_via_patch(authenticated_client):
    vendor_id = await _create_vendor(authenticated_client)
    product_id = await _create_product(authenticated_client, vendor_id)
    qt_id = await _create_qualification_type(authenticated_client)

    create_resp = await _create_cert(authenticated_client, product_id, qt_id)
    cert_id = create_resp.json()["id"]

    resp = await authenticated_client.patch(
        f"/api/v1/certificates/{cert_id}",
        json={"status": "VALID"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == CertificateStatus.VALID.value


async def test_expired_cert_shows_expired_status(authenticated_client):
    vendor_id = await _create_vendor(authenticated_client)
    product_id = await _create_product(authenticated_client, vendor_id)
    qt_id = await _create_qualification_type(authenticated_client)

    resp = await _create_cert(
        authenticated_client, product_id, qt_id, expiry_date=EXPIRY_DATE_PAST
    )
    assert resp.status_code == 201
    cert_id = resp.json()["id"]

    get_resp = await authenticated_client.get(f"/api/v1/certificates/{cert_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "EXPIRED"


async def test_upload_document_to_certificate(authenticated_client):
    vendor_id = await _create_vendor(authenticated_client)
    product_id = await _create_product(authenticated_client, vendor_id)
    qt_id = await _create_qualification_type(authenticated_client)

    create_resp = await _create_cert(authenticated_client, product_id, qt_id)
    cert_id = create_resp.json()["id"]
    assert create_resp.json()["document_id"] is None

    pdf_content = b"%PDF-1.4 test content"
    resp = await authenticated_client.post(
        f"/api/v1/certificates/{cert_id}/document",
        files={"file": ("cert.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] is not None
    assert body["id"] == cert_id
