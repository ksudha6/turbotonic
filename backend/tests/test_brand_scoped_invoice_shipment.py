"""Iter 111: brand-scoped invoice and shipment list/detail filtering."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.user import UserRole
from tests.conftest import make_test_brand, make_test_po

pytestmark = pytest.mark.asyncio


async def _accept_po(client: AsyncClient, po_id: str) -> None:
    """Submit then accept a PO so invoices and shipments can be created."""
    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert submit_resp.status_code == 200, submit_resp.text
    accept_resp = await client.post(f"/api/v1/po/{po_id}/accept")
    assert accept_resp.status_code == 200, accept_resp.text


async def _create_invoice(client: AsyncClient, po_id: str) -> dict:
    resp = await client.post(
        "/api/v1/invoices/",
        json={"po_id": po_id, "payment_terms": "TT", "currency": "USD"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_shipment(client: AsyncClient, po_id: str) -> dict:
    # PO line items use part_number "PN-001" (from _PO_BASE_PAYLOAD in conftest).
    resp = await client.post(
        "/api/v1/shipments/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": "PN-001", "quantity": 1, "uom": "EA"}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_scoped_sm_invoice_list_filters_to_brand(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_a = await make_test_brand(authenticated_client, name="Brand-Inv-A")
    brand_b = await make_test_brand(authenticated_client, name="Brand-Inv-B")

    po_a = await make_test_po(authenticated_client, brand_id=brand_a["id"])
    po_b = await make_test_po(authenticated_client, brand_id=brand_b["id"])
    await _accept_po(authenticated_client, po_a["id"])
    await _accept_po(authenticated_client, po_b["id"])

    inv_a = await _create_invoice(authenticated_client, po_a["id"])
    inv_b = await _create_invoice(authenticated_client, po_b["id"])

    user_id = await make_active_scoped_user(
        "inv-sm-a", UserRole.SM, brand_ids=[brand_a["id"]]
    )
    async with make_scoped_client(user_id) as sc:
        list_resp = await sc.get("/api/v1/invoices/")
    assert list_resp.status_code == 200
    ids = {item["id"] for item in list_resp.json()["items"]}
    assert inv_a["id"] in ids
    assert inv_b["id"] not in ids


async def test_scoped_sm_invoice_detail_other_brand_404(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_a = await make_test_brand(authenticated_client, name="Brand-InvDet-A")
    brand_b = await make_test_brand(authenticated_client, name="Brand-InvDet-B")

    po_b = await make_test_po(authenticated_client, brand_id=brand_b["id"])
    await _accept_po(authenticated_client, po_b["id"])
    inv_b = await _create_invoice(authenticated_client, po_b["id"])

    user_id = await make_active_scoped_user(
        "inv-det-sm", UserRole.SM, brand_ids=[brand_a["id"]]
    )
    async with make_scoped_client(user_id) as sc:
        resp = await sc.get(f"/api/v1/invoices/{inv_b['id']}")
    assert resp.status_code == 404


async def test_scoped_freight_manager_shipment_list_filters_to_brand(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_a = await make_test_brand(authenticated_client, name="Brand-Shp-A")
    brand_b = await make_test_brand(authenticated_client, name="Brand-Shp-B")

    po_a = await make_test_po(authenticated_client, brand_id=brand_a["id"])
    po_b = await make_test_po(authenticated_client, brand_id=brand_b["id"])
    await _accept_po(authenticated_client, po_a["id"])
    await _accept_po(authenticated_client, po_b["id"])

    shp_a = await _create_shipment(authenticated_client, po_a["id"])
    shp_b = await _create_shipment(authenticated_client, po_b["id"])

    user_id = await make_active_scoped_user(
        "shp-fm-a", UserRole.FREIGHT_MANAGER, brand_ids=[brand_a["id"]]
    )
    async with make_scoped_client(user_id) as sc:
        list_resp = await sc.get("/api/v1/shipments/")
    assert list_resp.status_code == 200
    ids = {s["id"] for s in list_resp.json()}
    assert shp_a["id"] in ids
    assert shp_b["id"] not in ids


async def test_scoped_freight_manager_shipment_detail_other_brand_404(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_a = await make_test_brand(authenticated_client, name="Brand-ShpDet-A")
    brand_b = await make_test_brand(authenticated_client, name="Brand-ShpDet-B")

    po_b = await make_test_po(authenticated_client, brand_id=brand_b["id"])
    await _accept_po(authenticated_client, po_b["id"])
    shp_b = await _create_shipment(authenticated_client, po_b["id"])

    user_id = await make_active_scoped_user(
        "shp-det-fm", UserRole.FREIGHT_MANAGER, brand_ids=[brand_a["id"]]
    )
    async with make_scoped_client(user_id) as sc:
        resp = await sc.get(f"/api/v1/shipments/{shp_b['id']}")
    assert resp.status_code == 404
