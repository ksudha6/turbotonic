from __future__ import annotations

import io
import re

import pytest
from httpx import AsyncClient
from pypdf import PdfReader

from src.domain.shipment import ShipmentStatus


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF given its raw bytes."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)

pytestmark = pytest.mark.asyncio

SHIPMENT_NUMBER_RE = re.compile(r"^SHP-\d{8}-[0-9A-F]{4}$")

# --- PO payload helpers ---

_LINE_ITEM_A: dict[str, object] = {
    "part_number": "PART-A",
    "description": "Widget A",
    "quantity": 100,
    "uom": "PCS",
    "unit_price": "10.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_LINE_ITEM_B: dict[str, object] = {
    "part_number": "PART-B",
    "description": "Widget B",
    "quantity": 50,
    "uom": "PCS",
    "unit_price": "5.00",
    "hs_code": "8471.30",
    "country_of_origin": "US",
}

_PO_BASE: dict[str, object] = {
    "buyer_name": "TurboTonic Ltd",
    "buyer_country": "US",
    "ship_to_address": "123 Main St",
    "payment_terms": "TT",
    "currency": "USD",
    "issued_date": "2026-03-16T00:00:00Z",
    "required_delivery_date": "2026-04-01T00:00:00Z",
    "terms_and_conditions": "",
    "incoterm": "FOB",
    "port_of_loading": "USLAX",
    "port_of_discharge": "CNSHA",
    "country_of_origin": "US",
    "country_of_destination": "CN",
    "marketplace": "AMZ",
}


async def _make_vendor(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/vendors/",
        json={"name": "ShipTest Vendor", "country": "CN", "vendor_type": "PROCUREMENT"},
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _make_accepted_po(
    client: AsyncClient,
    vendor_id: str,
    line_items: list[dict[str, object]] | None = None,
    decisions: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Create, submit, and drive a PO through the iter 056 negotiation flow.

    Each `decisions` entry has a `part_number` and a `status` in {ACCEPTED, REMOVED}
    (REJECTED is no longer a line status). The helper hits modify/accept/remove per-line
    and then submit-response to converge. Returns the final PO dict.
    """
    items = line_items or [_LINE_ITEM_A]
    payload = {**_PO_BASE, "vendor_id": vendor_id, "line_items": items}
    r = await client.post("/api/v1/po/", json=payload)
    assert r.status_code == 201
    po_id: str = r.json()["id"]

    r2 = await client.post(f"/api/v1/po/{po_id}/submit")
    assert r2.status_code == 200

    # Default: accept every line. Callers may pass REMOVED to test rejected-line paths.
    default_decisions: list[dict[str, str]] = [
        {"part_number": str(item["part_number"]), "status": "ACCEPTED"} for item in items
    ]
    final_decisions = decisions or default_decisions
    # Translate legacy "REJECTED" decisions onto the new REMOVED status so tests
    # written before iter 056 continue to exercise the rejected-line path.
    for decision in final_decisions:
        action = "remove" if decision["status"] in ("REMOVED", "REJECTED") else "accept"
        resp = await client.post(
            f"/api/v1/po/{po_id}/lines/{decision['part_number']}/{action}",
            json={},
        )
        assert resp.status_code == 200, resp.json()

    r_submit = await client.post(f"/api/v1/po/{po_id}/submit-response", json={})
    assert r_submit.status_code == 200, r_submit.json()
    return r_submit.json()


# --- Create shipment ---

async def test_create_shipment_returns_201(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)
    po_id: str = po["id"]

    r = await authenticated_client.post(
        "/api/v1/shipments/",
        json={
            "po_id": po_id,
            "line_items": [{"part_number": "PART-A", "quantity": 40, "uom": "PCS"}],
        },
    )
    assert r.status_code == 201
    body = r.json()
    expected_keys = {"id", "po_id", "shipment_number", "marketplace", "status", "line_items", "created_at", "updated_at"}
    assert expected_keys == set(body.keys())
    assert body["po_id"] == po_id
    assert body["marketplace"] == "AMZ"
    assert body["status"] == ShipmentStatus.DRAFT.value
    assert SHIPMENT_NUMBER_RE.match(body["shipment_number"]), f"bad format: {body['shipment_number']}"
    assert len(body["line_items"]) == 1
    assert body["line_items"][0]["part_number"] == "PART-A"
    assert body["line_items"][0]["quantity"] == 40


async def test_create_shipment_marketplace_inherited_from_po(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)
    r = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 1, "uom": "PCS"}]},
    )
    assert r.status_code == 201
    assert r.json()["marketplace"] == "AMZ"


async def test_create_shipment_nonexistent_po_returns_404(authenticated_client: AsyncClient) -> None:
    r = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": "nonexistent", "line_items": [{"part_number": "PART-A", "quantity": 1, "uom": "PCS"}]},
    )
    assert r.status_code == 404


async def test_create_shipment_non_accepted_po_returns_409(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    # Draft PO only -- not submitted/accepted
    payload = {**_PO_BASE, "vendor_id": vendor_id, "line_items": [_LINE_ITEM_A]}
    r = await authenticated_client.post("/api/v1/po/", json=payload)
    assert r.status_code == 201
    po_id: str = r.json()["id"]

    r2 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 1, "uom": "PCS"}]},
    )
    assert r2.status_code == 409


async def test_create_shipment_exceeding_accepted_qty_returns_422(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)  # PART-A qty=100

    r = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 101, "uom": "PCS"}]},
    )
    assert r.status_code == 422
    assert "PART-A" in r.json()["detail"]


async def test_create_shipment_removed_line_item_returns_422(authenticated_client: AsyncClient) -> None:
    # Iter 056: line-level rejection is now called REMOVED; attempting to ship
    # a REMOVED line must return 422 with that status in the error detail.
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(
        authenticated_client,
        vendor_id,
        line_items=[_LINE_ITEM_A, _LINE_ITEM_B],
        decisions=[
            {"part_number": "PART-A", "status": "ACCEPTED"},
            {"part_number": "PART-B", "status": "REMOVED"},
        ],
    )
    r = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-B", "quantity": 10, "uom": "PCS"}]},
    )
    assert r.status_code == 422
    assert "REMOVED" in r.json()["detail"]


async def test_create_shipment_empty_line_items_returns_422(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)
    r = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": []},
    )
    assert r.status_code == 422


async def test_create_two_shipments_second_uses_remaining(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)  # PART-A qty=100
    po_id: str = po["id"]

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 60, "uom": "PCS"}]},
    )
    assert r1.status_code == 201

    r2 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 40, "uom": "PCS"}]},
    )
    assert r2.status_code == 201


async def test_create_shipment_cumulative_over_ship_returns_422(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)  # PART-A qty=100
    po_id: str = po["id"]

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 80, "uom": "PCS"}]},
    )
    assert r1.status_code == 201

    r2 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 21, "uom": "PCS"}]},
    )
    assert r2.status_code == 422


# --- Remaining quantities ---

async def test_remaining_quantities_no_shipments(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)  # PART-A qty=100
    po_id: str = po["id"]

    r = await authenticated_client.get(f"/api/v1/shipments/remaining-quantities/{po_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["po_id"] == po_id
    items = {item["part_number"]: item for item in body["items"]}
    assert "PART-A" in items
    assert items["PART-A"] == {
        "part_number": "PART-A",
        "po_quantity": 100,
        "shipped_quantity": 0,
        "remaining_quantity": 100,
    }


async def test_remaining_quantities_after_one_shipment(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)
    po_id: str = po["id"]

    await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 30, "uom": "PCS"}]},
    )

    r = await authenticated_client.get(f"/api/v1/shipments/remaining-quantities/{po_id}")
    assert r.status_code == 200
    items = {item["part_number"]: item for item in r.json()["items"]}
    assert items["PART-A"] == {
        "part_number": "PART-A",
        "po_quantity": 100,
        "shipped_quantity": 30,
        "remaining_quantity": 70,
    }


async def test_remaining_quantities_after_two_shipments(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)
    po_id: str = po["id"]

    await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 30, "uom": "PCS"}]},
    )
    await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 20, "uom": "PCS"}]},
    )

    r = await authenticated_client.get(f"/api/v1/shipments/remaining-quantities/{po_id}")
    assert r.status_code == 200
    items = {item["part_number"]: item for item in r.json()["items"]}
    assert items["PART-A"] == {
        "part_number": "PART-A",
        "po_quantity": 100,
        "shipped_quantity": 50,
        "remaining_quantity": 50,
    }


async def test_remaining_quantities_excludes_removed_lines(authenticated_client: AsyncClient) -> None:
    # Iter 056: REMOVED replaces REJECTED at the line level; remaining quantities
    # must still exclude non-ACCEPTED lines.
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(
        authenticated_client,
        vendor_id,
        line_items=[_LINE_ITEM_A, _LINE_ITEM_B],
        decisions=[
            {"part_number": "PART-A", "status": "ACCEPTED"},
            {"part_number": "PART-B", "status": "REMOVED"},
        ],
    )
    r = await authenticated_client.get(f"/api/v1/shipments/remaining-quantities/{po['id']}")
    assert r.status_code == 200
    part_numbers = {item["part_number"] for item in r.json()["items"]}
    assert "PART-B" not in part_numbers
    assert "PART-A" in part_numbers


async def test_remaining_quantities_nonexistent_po_returns_404(authenticated_client: AsyncClient) -> None:
    r = await authenticated_client.get("/api/v1/shipments/remaining-quantities/nonexistent")
    assert r.status_code == 404


# --- Submit for documents ---

async def test_submit_for_documents_transitions_to_documents_pending(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/submit-for-documents")
    assert r2.status_code == 200
    assert r2.json()["status"] == ShipmentStatus.DOCUMENTS_PENDING.value


async def test_submit_for_documents_non_draft_returns_409(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    shipment_id: str = r1.json()["id"]

    await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/submit-for-documents")
    # Second call should fail -- already DOCUMENTS_PENDING
    r3 = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/submit-for-documents")
    assert r3.status_code == 409


# --- List and get ---

async def test_list_shipments_by_po_id(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)
    po_id: str = po["id"]

    await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 5, "uom": "PCS"}]},
    )

    r = await authenticated_client.get("/api/v1/shipments/", params={"po_id": po_id})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert all(s["po_id"] == po_id for s in items)


async def test_get_shipment_by_id_returns_correct_shipment(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 25, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    created = r1.json()
    shipment_id: str = created["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["id"] == shipment_id
    assert body["po_id"] == po["id"]
    assert len(body["line_items"]) == 1
    assert body["line_items"][0]["quantity"] == 25


async def test_get_nonexistent_shipment_returns_404(authenticated_client: AsyncClient) -> None:
    r = await authenticated_client.get("/api/v1/shipments/nonexistent-id")
    assert r.status_code == 404


# --- PATCH line item weights/dimensions (iter 044) ---

_PATCH_LINE_ITEM: dict[str, object] = {
    "part_number": "PART-A",
    "net_weight": "5.500",
    "gross_weight": "6.200",
    "package_count": 2,
    "dimensions": "40x30x20 cm",
    "country_of_origin": "CN",
}


async def test_patch_shipment_persists_weights_and_returns_them(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}",
        json={"line_items": [_PATCH_LINE_ITEM]},
    )
    assert r2.status_code == 200
    body = r2.json()
    li = body["line_items"][0]
    assert li["part_number"] == "PART-A"
    assert li["net_weight"] == "5.500"
    assert li["gross_weight"] == "6.200"
    assert li["package_count"] == 2
    assert li["dimensions"] == "40x30x20 cm"
    assert li["country_of_origin"] == "CN"


async def test_patch_shipment_unknown_part_number_returns_422(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}",
        json={"line_items": [{"part_number": "UNKNOWN-PN", "net_weight": "1.0"}]},
    )
    assert r2.status_code == 422
    assert "UNKNOWN-PN" in r2.json()["detail"]


async def test_patch_shipment_ready_to_ship_returns_409(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    # Advance to READY_TO_SHIP via DOCUMENTS_PENDING
    r_sub = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/submit-for-documents")
    assert r_sub.status_code == 200
    r_ready = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/mark-ready")
    assert r_ready.status_code == 200

    r2 = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}",
        json={"line_items": [{"part_number": "PART-A", "net_weight": "1.0"}]},
    )
    assert r2.status_code == 409


async def test_patch_shipment_draft_works(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]
    assert r1.json()["status"] == ShipmentStatus.DRAFT.value

    r2 = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}",
        json={"line_items": [{"part_number": "PART-A", "net_weight": "3.0"}]},
    )
    assert r2.status_code == 200


async def test_patch_shipment_documents_pending_works(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r_sub = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/submit-for-documents")
    assert r_sub.status_code == 200
    assert r_sub.json()["status"] == ShipmentStatus.DOCUMENTS_PENDING.value

    r2 = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}",
        json={"line_items": [{"part_number": "PART-A", "net_weight": "4.5"}]},
    )
    assert r2.status_code == 200


# --- Packing list PDF (iter 044) ---


async def test_packing_list_returns_200_pdf(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert r2.status_code == 200
    assert r2.headers["content-type"] == "application/pdf"
    assert len(r2.content) > 0


async def test_packing_list_nonexistent_shipment_returns_404(authenticated_client: AsyncClient) -> None:
    r = await authenticated_client.get("/api/v1/shipments/nonexistent-id/packing-list")
    assert r.status_code == 404


async def test_packing_list_contains_shipment_and_po_numbers(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id)
    po_number: str = po["po_number"]

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_number: str = r1.json()["shipment_number"]
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert shipment_number in pdf_text
    assert po_number in pdf_text


async def test_packing_list_summary_totals_computed_correctly(authenticated_client: AsyncClient) -> None:
    vendor_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(
        authenticated_client,
        vendor_id,
        line_items=[_LINE_ITEM_A, _LINE_ITEM_B],
    )

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={
            "po_id": po["id"],
            "line_items": [
                {"part_number": "PART-A", "quantity": 10, "uom": "PCS"},
                {"part_number": "PART-B", "quantity": 5, "uom": "PCS"},
            ],
        },
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    # Patch both line items with weights
    net_a = "3.000"
    net_b = "2.000"
    gross_a = "3.500"
    gross_b = "2.500"
    pkg_a = 2
    pkg_b = 1

    r2 = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}",
        json={
            "line_items": [
                {
                    "part_number": "PART-A",
                    "net_weight": net_a,
                    "gross_weight": gross_a,
                    "package_count": pkg_a,
                },
                {
                    "part_number": "PART-B",
                    "net_weight": net_b,
                    "gross_weight": gross_b,
                    "package_count": pkg_b,
                },
            ]
        },
    )
    assert r2.status_code == 200

    # Verify via GET that fields are persisted
    body = r2.json()
    items_by_pn = {li["part_number"]: li for li in body["line_items"]}
    assert items_by_pn["PART-A"]["net_weight"] == net_a
    assert items_by_pn["PART-B"]["net_weight"] == net_b
    assert items_by_pn["PART-A"]["package_count"] == pkg_a
    assert items_by_pn["PART-B"]["package_count"] == pkg_b

    # PDF must generate without error (totals computed inside packing_list_pdf)
    r3 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert r3.status_code == 200
    assert len(r3.content) > 0
