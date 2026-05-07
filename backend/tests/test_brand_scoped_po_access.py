"""Iter 111: brand-scoped PO list and detail filtering."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.user import UserRole
from tests.conftest import make_test_brand, make_test_po

pytestmark = pytest.mark.asyncio


async def test_scoped_sm_po_list_filters_to_assigned_brand(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_a = await make_test_brand(authenticated_client, name="Brand-PO-A")
    brand_b = await make_test_brand(authenticated_client, name="Brand-PO-B")

    po_a = await make_test_po(authenticated_client, brand_id=brand_a["id"])
    po_b = await make_test_po(authenticated_client, brand_id=brand_b["id"])

    user_id = await make_active_scoped_user(
        "scoped-sm-po-list", UserRole.SM, brand_ids=[brand_a["id"]]
    )
    async with make_scoped_client(user_id) as sc:
        list_resp = await sc.get("/api/v1/po/")
    assert list_resp.status_code == 200
    ids = {item["id"] for item in list_resp.json()["items"]}

    assert po_a["id"] in ids
    assert po_b["id"] not in ids


async def test_scoped_sm_po_detail_own_brand_ok(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_a = await make_test_brand(authenticated_client, name="Brand-Detail-A")
    po_a = await make_test_po(authenticated_client, brand_id=brand_a["id"])

    user_id = await make_active_scoped_user(
        "scoped-sm-po-detail", UserRole.SM, brand_ids=[brand_a["id"]]
    )
    async with make_scoped_client(user_id) as sc:
        resp = await sc.get(f"/api/v1/po/{po_a['id']}")
    assert resp.status_code == 200


async def test_scoped_sm_po_detail_other_brand_404(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_a = await make_test_brand(authenticated_client, name="Brand-404-A")
    brand_b = await make_test_brand(authenticated_client, name="Brand-404-B")

    po_b = await make_test_po(authenticated_client, brand_id=brand_b["id"])

    user_id = await make_active_scoped_user(
        "scoped-sm-po-404", UserRole.SM, brand_ids=[brand_a["id"]]
    )
    async with make_scoped_client(user_id) as sc:
        resp = await sc.get(f"/api/v1/po/{po_b['id']}")
    assert resp.status_code == 404


async def test_unscoped_sm_po_list_sees_all_brands(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_a = await make_test_brand(authenticated_client, name="Brand-Unscoped-A")
    brand_b = await make_test_brand(authenticated_client, name="Brand-Unscoped-B")

    po_a = await make_test_po(authenticated_client, brand_id=brand_a["id"])
    po_b = await make_test_po(authenticated_client, brand_id=brand_b["id"])

    # SM with no brands = unscoped (sees all).
    user_id = await make_active_scoped_user("unscoped-sm-po", UserRole.SM)
    async with make_scoped_client(user_id) as sc:
        list_resp = await sc.get("/api/v1/po/")
    assert list_resp.status_code == 200
    ids = {item["id"] for item in list_resp.json()["items"]}
    assert po_a["id"] in ids
    assert po_b["id"] in ids


async def test_admin_po_detail_ignores_brand_scope(authenticated_client: AsyncClient):
    """ADMIN always sees all POs regardless of brand_ids being set."""
    brand_b = await make_test_brand(authenticated_client, name="Brand-Admin-PO")
    po_b = await make_test_po(authenticated_client, brand_id=brand_b["id"])

    # authenticated_client is already the ADMIN
    resp = await authenticated_client.get(f"/api/v1/po/{po_b['id']}")
    assert resp.status_code == 200
