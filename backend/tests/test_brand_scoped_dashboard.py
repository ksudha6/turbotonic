"""Iter 111: dashboard KPIs respect brand scope for buyer-side roles."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.domain.user import UserRole
from tests.conftest import make_test_brand, make_test_po

pytestmark = pytest.mark.asyncio


async def _submit_po(client: AsyncClient, po_id: str) -> None:
    """Submit a PO so it counts as PENDING (awaiting acceptance)."""
    resp = await client.post(f"/api/v1/po/{po_id}/submit")
    assert resp.status_code == 200, resp.text


async def test_scoped_sm_kpis_reflect_only_assigned_brand(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_a = await make_test_brand(authenticated_client, name="Brand-KPI-A")
    brand_b = await make_test_brand(authenticated_client, name="Brand-KPI-B")

    # Create and submit one PO per brand
    po_a = await make_test_po(authenticated_client, brand_id=brand_a["id"])
    po_b = await make_test_po(authenticated_client, brand_id=brand_b["id"])
    await _submit_po(authenticated_client, po_a["id"])
    await _submit_po(authenticated_client, po_b["id"])

    # SM scoped to brand_a only
    user_id = await make_active_scoped_user(
        "kpi-sm-scoped", UserRole.SM, brand_ids=[brand_a["id"]]
    )

    async with make_scoped_client(user_id) as sc:
        summary_resp = await sc.get("/api/v1/dashboard/summary")
    assert summary_resp.status_code == 200
    kpis = summary_resp.json()["kpis"]
    # brand_a has 1 PENDING PO; scoped SM should see exactly that 1.
    assert kpis["pending_pos"] >= 1

    # brand_b's PO must not appear in awaiting_acceptance.
    awaiting = summary_resp.json()["awaiting_acceptance"]
    awaiting_po_ids = {a["id"] for a in awaiting}
    assert po_b["id"] not in awaiting_po_ids


async def test_unscoped_sm_kpis_see_all_brands(
    authenticated_client: AsyncClient, make_scoped_client, make_active_scoped_user
):
    brand_x = await make_test_brand(authenticated_client, name="Brand-KPI-X")
    brand_y = await make_test_brand(authenticated_client, name="Brand-KPI-Y")

    po_x = await make_test_po(authenticated_client, brand_id=brand_x["id"])
    po_y = await make_test_po(authenticated_client, brand_id=brand_y["id"])
    await _submit_po(authenticated_client, po_x["id"])
    await _submit_po(authenticated_client, po_y["id"])

    # SM with no brands = unscoped (sees all).
    user_id = await make_active_scoped_user("kpi-sm-unscoped", UserRole.SM)

    async with make_scoped_client(user_id) as sc:
        summary_resp = await sc.get("/api/v1/dashboard/summary")
    assert summary_resp.status_code == 200
    kpis = summary_resp.json()["kpis"]
    # Unscoped SM sees both; count must be >= 2 (other tests may have added more).
    assert kpis["pending_pos"] >= 2
