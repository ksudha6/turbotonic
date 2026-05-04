from __future__ import annotations

import itertools

import pytest
from httpx import AsyncClient

from src.domain.user import User, UserRole, UserStatus

_brand_counter = itertools.count(1)

pytestmark = pytest.mark.asyncio


# Test data. The fake email service records calls as tuples of
# (to_list, template_name, context_dict); tests assert on to_list and
# template_name, not SMTP bytes.
_LINE_ITEM: dict = {
    "part_number": "PN-001",
    "description": "Widget A",
    "quantity": 10,
    "uom": "EA",
    "unit_price": "5.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_LINE_ITEM_2: dict = {
    "part_number": "PN-002",
    "description": "Widget B",
    "quantity": 5,
    "uom": "EA",
    "unit_price": "3.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_PO_PAYLOAD: dict = {
    "vendor_id": "placeholder",
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
    "line_items": [_LINE_ITEM, _LINE_ITEM_2],
}

_ADVANCE_PO_PAYLOAD: dict = {**_PO_PAYLOAD, "payment_terms": "100_PCT_ADVANCE"}

_VENDOR_EMAIL = "vendor-acme@acme.example"
_SM_EMAIL = "sm-test@turbotonic.example"


async def _create_po_with_vendor_user(
    client: AsyncClient, payload: dict | None = None
) -> tuple[dict, str]:
    # Vendor row + one VENDOR user with an email so vendor-scoped recipient
    # resolution returns at least one address. Returns (po_json, vendor_id).
    p = dict(payload or _PO_PAYLOAD)
    vendor_resp = await client.post(
        "/api/v1/vendors/",
        json={"name": "Acme Test", "country": "US", "vendor_type": "PROCUREMENT"},
    )
    assert vendor_resp.status_code == 201
    vendor_id = vendor_resp.json()["id"]
    p["vendor_id"] = vendor_id

    # Create brand and link vendor.
    brand_n = next(_brand_counter)
    brand_resp = await client.post(
        "/api/v1/brands/",
        json={"name": f"NotifBrand-{brand_n}", "legal_name": "Notif Brand LLC", "address": "1 Notif Ave", "country": "US"},
    )
    assert brand_resp.status_code == 201
    brand_id = brand_resp.json()["id"]
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor_id})
    p["brand_id"] = brand_id

    # Seed a VENDOR user directly via the shared test connection so the
    # dispatcher's recipient resolver has a row to match against.
    from tests.conftest import TEST_DATABASE_URL  # noqa: PLC0415
    import asyncpg  # noqa: PLC0415
    from src.routers.purchase_order import get_activity_repo as po_get_activity_repo  # noqa: PLC0415
    from src.main import app as _app  # noqa: PLC0415

    # The test connection is the one bound behind every override; recover it via
    # the activity-repo override (any connection-holding dep works).
    override = _app.dependency_overrides[po_get_activity_repo]
    assert override is not None
    async for repo in override():
        conn = repo._conn
        break
    from src.user_repository import UserRepository  # noqa: PLC0415
    vendor_user = User.create(
        username=f"vendor-{vendor_id[:8]}",
        display_name="Vendor User",
        role=UserRole.VENDOR,
        vendor_id=vendor_id,
        email=_VENDOR_EMAIL,
    )
    await UserRepository(conn).save(vendor_user)

    # Also seed a non-admin SM user with email so SM-targeted events have a
    # concrete recipient distinct from the authenticated test-admin.
    sm_user = User.create(
        username=f"sm-{vendor_id[:8]}",
        display_name="SM User",
        role=UserRole.SM,
        email=_SM_EMAIL,
    )
    await UserRepository(conn).save(sm_user)

    # Create the PO itself.
    resp = await client.post("/api/v1/po/", json=p)
    assert resp.status_code == 201
    return resp.json(), vendor_id


async def _submit_and_accept(client: AsyncClient, po_id: str) -> dict:
    r1 = await client.post(f"/api/v1/po/{po_id}/submit")
    assert r1.status_code == 200
    r2 = await client.post(f"/api/v1/po/{po_id}/accept")
    assert r2.status_code == 200
    return r2.json()


# ---------------------------------------------------------------------------
# Integration: dispatcher wired through the routers
# ---------------------------------------------------------------------------


async def test_submit_response_convergence_triggers_po_accepted_email_to_vendor(
    authenticated_client: AsyncClient,
    fake_email_service,
) -> None:
    # Walk a PO through the negotiation loop until convergence to ACCEPTED:
    # modify one line, accept it, submit-response. The dispatcher must fire
    # po_accepted to the vendor-scoped recipient set on convergence.
    client = authenticated_client
    po, _vendor_id = await _create_po_with_vendor_user(client)
    po_id = po["id"]

    await client.post(f"/api/v1/po/{po_id}/submit")

    # Vendor (via admin session acting as SM here is the simplest path; the
    # convergence handler dispatches regardless of who accepts). Accept each
    # line, then submit-response to close the negotiation.
    fake_email_service.calls.clear()
    for line in (_LINE_ITEM, _LINE_ITEM_2):
        r = await client.post(
            f"/api/v1/po/{po_id}/lines/{line['part_number']}/accept", json={}
        )
        assert r.status_code == 200

    resp = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"

    # Exactly one po_accepted email should be on the wire; recipient is the
    # vendor user we seeded.
    accepted_calls = [c for c in fake_email_service.calls if c[1] == "po_accepted"]
    assert len(accepted_calls) == 1, (
        f"expected one po_accepted email, got {[c[1] for c in fake_email_service.calls]}"
    )
    to_list, template_name, _ctx = accepted_calls[0]
    assert template_name == "po_accepted"
    assert to_list == [_VENDOR_EMAIL], (
        f"po_accepted must target vendor users; got {to_list}"
    )


async def test_submit_response_midround_triggers_po_modified_email_to_counterparty(
    authenticated_client: AsyncClient,
    fake_email_service,
) -> None:
    # SM modifies one line at round 0, submit-response; PO stays MODIFIED
    # (round 1) and the dispatcher mails the VENDOR side.
    client = authenticated_client
    po, _vendor_id = await _create_po_with_vendor_user(client)
    po_id = po["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")

    fake_email_service.calls.clear()

    mod_resp = await client.post(
        f"/api/v1/po/{po_id}/lines/PN-001/modify",
        json={"fields": {"quantity": 20}},
    )
    assert mod_resp.status_code == 200

    submit_resp = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "MODIFIED"

    # Two emails: one po_line_modified (hand-off per line edit) and one
    # po_modified (round hand-off). Both target the vendor side because the
    # authenticated admin acts as SM.
    templates_sent = [c[1] for c in fake_email_service.calls]
    assert "po_modified" in templates_sent, (
        f"po_modified template must fire on submit-response hand-off; got {templates_sent}"
    )
    modified_calls = [c for c in fake_email_service.calls if c[1] == "po_modified"]
    assert len(modified_calls) == 1
    to_list, _template, _ctx = modified_calls[0]
    assert to_list == [_VENDOR_EMAIL], (
        f"po_modified must target the counterparty (vendor); got {to_list}"
    )


async def test_modify_line_triggers_po_line_modified_email_with_field_delta(
    authenticated_client: AsyncClient,
    fake_email_service,
) -> None:
    # modify_line alone should emit a po_line_modified email carrying the
    # field delta in the rendered body. Recipient is the counterparty.
    client = authenticated_client
    po, _vendor_id = await _create_po_with_vendor_user(client)
    po_id = po["id"]
    await client.post(f"/api/v1/po/{po_id}/submit")

    fake_email_service.calls.clear()

    resp = await client.post(
        f"/api/v1/po/{po_id}/lines/PN-002/modify",
        json={"fields": {"quantity": 7, "description": "Widget B revised"}},
    )
    assert resp.status_code == 200

    line_calls = [c for c in fake_email_service.calls if c[1] == "po_line_modified"]
    assert len(line_calls) == 1, (
        f"expected one po_line_modified email, got {[c[1] for c in fake_email_service.calls]}"
    )
    to_list, _template, ctx = line_calls[0]
    assert to_list == [_VENDOR_EMAIL], (
        f"po_line_modified must target the counterparty (vendor); got {to_list}"
    )
    # Field delta is carried in the rendered text body. The router builds
    # `part_number: field1, field2` in sorted order — assert on that signal.
    rendered_text = ctx["body_text"]
    assert "PN-002" in rendered_text
    # Sorted field names appear in the line_detail segment.
    assert "quantity" in rendered_text
    assert "description" in rendered_text


async def test_mark_advance_paid_triggers_po_advance_paid_email_to_vendor(
    authenticated_client: AsyncClient,
    fake_email_service,
) -> None:
    client = authenticated_client
    po, _vendor_id = await _create_po_with_vendor_user(client, _ADVANCE_PO_PAYLOAD)
    po_id = po["id"]
    await _submit_and_accept(client, po_id)

    fake_email_service.calls.clear()

    resp = await client.post(f"/api/v1/po/{po_id}/mark-advance-paid", json={})
    assert resp.status_code == 200

    advance_calls = [c for c in fake_email_service.calls if c[1] == "po_advance_paid"]
    assert len(advance_calls) == 1, (
        f"expected one po_advance_paid email, got {[c[1] for c in fake_email_service.calls]}"
    )
    to_list, _template, _ctx = advance_calls[0]
    assert to_list == [_VENDOR_EMAIL], (
        f"po_advance_paid must target vendor users; got {to_list}"
    )

    # Idempotent second call should NOT emit another email.
    fake_email_service.calls.clear()
    resp2 = await client.post(f"/api/v1/po/{po_id}/mark-advance-paid", json={})
    assert resp2.status_code == 200
    assert not fake_email_service.calls, (
        f"second mark-advance-paid is idempotent; no email should fire, got "
        f"{fake_email_service.calls}"
    )
