from __future__ import annotations

import io
import itertools
import re
from decimal import Decimal

import pytest
from httpx import AsyncClient
from pypdf import PdfReader

from src.domain.activity import ActivityEvent, EntityType
from src.domain.shipment import ShipmentStatus
from src.domain.shipment_document_requirement import DocumentRequirementStatus

_brand_counter = itertools.count(1)


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


async def _make_vendor(client: AsyncClient) -> tuple[str, str]:
    """Create a vendor and brand, link them; return (vendor_id, brand_id)."""
    r = await client.post(
        "/api/v1/vendors/",
        json={"name": "ShipTest Vendor", "country": "CN", "vendor_type": "PROCUREMENT"},
    )
    assert r.status_code == 201
    vendor_id = r.json()["id"]
    brand_n = next(_brand_counter)
    brand_r = await client.post(
        "/api/v1/brands/",
        json={"name": f"ShipBrand-{brand_n}", "legal_name": "Ship Brand LLC", "address": "1 Ship Ave", "country": "US"},
    )
    assert brand_r.status_code == 201
    brand_id = brand_r.json()["id"]
    await client.post(f"/api/v1/brands/{brand_id}/vendors", json={"vendor_id": vendor_id})
    return vendor_id, brand_id


async def _make_accepted_po(
    client: AsyncClient,
    vendor_id: str,
    brand_id: str,
    line_items: list[dict[str, object]] | None = None,
    decisions: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Create, submit, and drive a PO through the iter 056 negotiation flow.

    Each `decisions` entry has a `part_number` and a `status` in {ACCEPTED, REMOVED}
    (REJECTED is no longer a line status). The helper hits modify/accept/remove per-line
    and then submit-response to converge. Returns the final PO dict.
    """
    items = line_items or [_LINE_ITEM_A]
    payload = {**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand_id, "line_items": items}
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
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
    expected_keys = {
        "id", "po_id", "shipment_number", "marketplace", "status",
        "line_items", "created_at", "updated_at",
        "carrier", "booking_reference", "pickup_date", "shipped_at",
        # Iter 106: transport + declaration fields (all nullable, present in every response)
        "vessel_name", "voyage_number",
        "signatory_name", "signatory_title", "declared_at",
        # Iter 110: logistics fields
        "pallet_count", "export_reason",
    }
    assert expected_keys == set(body.keys())
    assert body["po_id"] == po_id
    assert body["marketplace"] == "AMZ"
    assert body["status"] == ShipmentStatus.DRAFT.value
    assert SHIPMENT_NUMBER_RE.match(body["shipment_number"]), f"bad format: {body['shipment_number']}"
    assert len(body["line_items"]) == 1
    assert body["line_items"][0]["part_number"] == "PART-A"
    assert body["line_items"][0]["quantity"] == 40


async def test_create_shipment_marketplace_inherited_from_po(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    # Draft PO only -- not submitted/accepted
    payload = {**_PO_BASE, "vendor_id": vendor_id, "brand_id": brand_id, "line_items": [_LINE_ITEM_A]}
    r = await authenticated_client.post("/api/v1/po/", json=payload)
    assert r.status_code == 201
    po_id: str = r.json()["id"]

    r2 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po_id, "line_items": [{"part_number": "PART-A", "quantity": 1, "uom": "PCS"}]},
    )
    assert r2.status_code == 409


async def test_create_shipment_exceeding_accepted_qty_returns_422(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)  # PART-A qty=100

    r = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 101, "uom": "PCS"}]},
    )
    assert r.status_code == 422
    assert "PART-A" in r.json()["detail"]


async def test_create_shipment_removed_line_item_returns_422(authenticated_client: AsyncClient) -> None:
    # Iter 056: line-level rejection is now called REMOVED; attempting to ship
    # a REMOVED line must return 422 with that status in the error detail.
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(
        authenticated_client,
        vendor_id,
        brand_id,
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    r = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": []},
    )
    assert r.status_code == 422


async def test_create_two_shipments_second_uses_remaining(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)  # PART-A qty=100
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)  # PART-A qty=100
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)  # PART-A qty=100
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(
        authenticated_client,
        vendor_id,
        brand_id,
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

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


async def _ready_shipment_id(client: AsyncClient) -> str:
    """Helper: create a shipment, submit for documents, mark ready. Returns its id."""
    vendor_id, brand_id = await _make_vendor(client)
    po = await _make_accepted_po(client, vendor_id, brand_id)
    r1 = await client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]
    r_sub = await client.post(f"/api/v1/shipments/{shipment_id}/submit-for-documents")
    assert r_sub.status_code == 200
    r_ready = await client.post(f"/api/v1/shipments/{shipment_id}/mark-ready")
    assert r_ready.status_code == 200
    return shipment_id


async def test_book_shipment_transitions_to_booked(authenticated_client: AsyncClient) -> None:
    shipment_id = await _ready_shipment_id(authenticated_client)
    r = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/book",
        json={"carrier": "Maersk", "booking_reference": "BK-12345", "pickup_date": "2026-05-15"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "BOOKED"
    assert body["carrier"] == "Maersk"
    assert body["booking_reference"] == "BK-12345"
    assert body["pickup_date"] == "2026-05-15"


async def test_book_shipment_from_draft_returns_409(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    shipment_id: str = r1.json()["id"]
    r = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/book",
        json={"carrier": "DHL", "booking_reference": "BK-1", "pickup_date": "2026-05-15"},
    )
    assert r.status_code == 409


async def test_book_shipment_empty_carrier_returns_422(authenticated_client: AsyncClient) -> None:
    shipment_id = await _ready_shipment_id(authenticated_client)
    r = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/book",
        json={"carrier": "  ", "booking_reference": "BK-1", "pickup_date": "2026-05-15"},
    )
    assert r.status_code == 422


async def test_mark_shipped_transitions_to_shipped(authenticated_client: AsyncClient) -> None:
    shipment_id = await _ready_shipment_id(authenticated_client)
    r_book = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/book",
        json={"carrier": "Maersk", "booking_reference": "BK-1", "pickup_date": "2026-05-15"},
    )
    assert r_book.status_code == 200
    r_ship = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/ship")
    assert r_ship.status_code == 200
    body = r_ship.json()
    assert body["status"] == "SHIPPED"
    assert body["shipped_at"] is not None


async def test_mark_shipped_from_ready_returns_409(authenticated_client: AsyncClient) -> None:
    shipment_id = await _ready_shipment_id(authenticated_client)
    r = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/ship")
    assert r.status_code == 409


async def test_patch_shipment_ready_to_ship_returns_409(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
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
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(
        authenticated_client,
        vendor_id,
        brand_id,
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


# --- Iter 045: Commercial invoice PDF ---


async def test_commercial_invoice_returns_200_pdf(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r2.status_code == 200
    assert r2.headers["content-type"] == "application/pdf"
    assert len(r2.content) > 0


async def test_commercial_invoice_nonexistent_shipment_returns_404(authenticated_client: AsyncClient) -> None:
    r = await authenticated_client.get("/api/v1/shipments/nonexistent-id/commercial-invoice")
    assert r.status_code == 404


async def test_commercial_invoice_ci_number_format(authenticated_client: AsyncClient) -> None:
    from src.services.commercial_invoice_pdf import generate_ci_number

    shipment_number = "SHP-20260424-A3F2"
    expected_ci_number = f"CI-{shipment_number}"
    assert generate_ci_number(shipment_number) == expected_ci_number


async def test_commercial_invoice_contains_identifiers(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    po_number: str = po["po_number"]

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_number: str = r1.json()["shipment_number"]
    shipment_id: str = r1.json()["id"]
    expected_ci_number = f"CI-{shipment_number}"

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert shipment_number in pdf_text
    assert po_number in pdf_text
    assert expected_ci_number in pdf_text


async def test_commercial_invoice_line_value_uses_po_unit_price(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    shipment_quantity = 7
    expected_line_value = shipment_quantity * Decimal(_LINE_ITEM_A["unit_price"])  # 7 * 10.00 = 70.00

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": shipment_quantity, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert f"{expected_line_value:.2f}" in pdf_text


async def test_commercial_invoice_hs_code_from_po(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    expected_hs_code: str = _LINE_ITEM_A["hs_code"]

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert expected_hs_code in pdf_text


async def test_commercial_invoice_summary_totals(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(
        authenticated_client,
        vendor_id,
        brand_id,
        line_items=[_LINE_ITEM_A, _LINE_ITEM_B],
    )

    qty_a = 10
    qty_b = 5
    expected_total_qty = qty_a + qty_b
    expected_total_value = (
        qty_a * Decimal(_LINE_ITEM_A["unit_price"])
        + qty_b * Decimal(_LINE_ITEM_B["unit_price"])
    )

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={
            "po_id": po["id"],
            "line_items": [
                {"part_number": "PART-A", "quantity": qty_a, "uom": "PCS"},
                {"part_number": "PART-B", "quantity": qty_b, "uom": "PCS"},
            ],
        },
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert str(expected_total_qty) in pdf_text
    assert f"{expected_total_value:.2f}" in pdf_text


# ─────────────────────────────────────────────────────────────────────────────
# Iter 046: Shipment document requirements + readiness gate
# ─────────────────────────────────────────────────────────────────────────────

_EXPECTED_REQUIREMENT_KEYS = {
    "id", "shipment_id", "document_type", "is_auto_generated",
    "status", "document_id", "created_at", "updated_at",
}

_EXPECTED_READINESS_KEYS = {
    "documents_ready", "certificates_ready", "packaging_ready",
    "is_ready", "missing_documents", "missing_certificates", "missing_packaging",
}


async def _make_documents_pending_shipment(
    client: AsyncClient,
) -> tuple[str, str]:
    """Create vendor, accepted PO, shipment, then submit-for-documents.

    Returns (shipment_id, shipment_number).
    """
    vendor_id, brand_id = await _make_vendor(client)
    po = await _make_accepted_po(client, vendor_id, brand_id)
    r = await client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r.status_code == 201
    shipment_id: str = r.json()["id"]
    shipment_number: str = r.json()["shipment_number"]
    r2 = await client.post(f"/api/v1/shipments/{shipment_id}/submit-for-documents")
    assert r2.status_code == 200
    return shipment_id, shipment_number


# --- Submit for documents auto-creates default requirements ---


async def test_submit_for_documents_creates_packing_list_and_ci_requirements(
    authenticated_client: AsyncClient,
) -> None:
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    r = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/requirements")
    assert r.status_code == 200
    reqs = r.json()
    assert len(reqs) == 2

    doc_types = {req["document_type"] for req in reqs}
    assert doc_types == {"PACKING_LIST", "COMMERCIAL_INVOICE"}

    for req in reqs:
        assert set(req.keys()) == _EXPECTED_REQUIREMENT_KEYS
        assert req["is_auto_generated"] is True
        assert req["status"] == DocumentRequirementStatus.PENDING.value
        assert req["document_id"] is None
        assert req["shipment_id"] == shipment_id


# --- Add custom requirement ---


async def test_add_custom_requirement_returns_201(
    authenticated_client: AsyncClient,
) -> None:
    document_type = "CERTIFICATE_OF_ORIGIN"
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    r = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/requirements",
        json={"document_type": document_type},
    )
    assert r.status_code == 201
    body = r.json()
    assert set(body.keys()) == _EXPECTED_REQUIREMENT_KEYS
    assert body["document_type"] == document_type
    assert body["is_auto_generated"] is False
    assert body["status"] == DocumentRequirementStatus.PENDING.value
    assert body["shipment_id"] == shipment_id


async def test_add_requirement_on_ready_to_ship_returns_409(
    authenticated_client: AsyncClient,
) -> None:
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    # Advance to READY_TO_SHIP (no products with qualifications so readiness passes)
    r_mark = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/mark-ready")
    assert r_mark.status_code == 200

    r = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/requirements",
        json={"document_type": "BILL_OF_LADING"},
    )
    assert r.status_code == 409


# --- List requirements ---


async def test_list_requirements_returns_all_for_shipment(
    authenticated_client: AsyncClient,
) -> None:
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    # Add a custom requirement
    await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/requirements",
        json={"document_type": "BILL_OF_LADING"},
    )

    r = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/requirements")
    assert r.status_code == 200
    reqs = r.json()
    # 2 auto-generated + 1 custom
    assert len(reqs) == 3
    doc_types = {req["document_type"] for req in reqs}
    assert "PACKING_LIST" in doc_types
    assert "COMMERCIAL_INVOICE" in doc_types
    assert "BILL_OF_LADING" in doc_types


# --- Upload document ---


async def test_upload_document_transitions_requirement_to_collected(
    authenticated_client: AsyncClient,
) -> None:
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    # Add a custom requirement to upload against
    r_add = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/requirements",
        json={"document_type": "BILL_OF_LADING"},
    )
    assert r_add.status_code == 201
    requirement_id: str = r_add.json()["id"]

    file_content = b"test document content"
    r_upload = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/documents/{requirement_id}/upload",
        files={"file": ("test.pdf", file_content, "application/pdf")},
    )
    assert r_upload.status_code == 200
    body = r_upload.json()
    assert body["status"] == DocumentRequirementStatus.COLLECTED.value
    assert body["document_id"] is not None
    assert body["id"] == requirement_id


async def test_upload_against_nonexistent_requirement_returns_404(
    authenticated_client: AsyncClient,
) -> None:
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    r = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/documents/nonexistent-req-id/upload",
        files={"file": ("test.pdf", b"content", "application/pdf")},
    )
    assert r.status_code == 404


async def test_upload_records_document_uploaded_activity(
    authenticated_client: AsyncClient,
) -> None:
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    r_add = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/requirements",
        json={"document_type": "BILL_OF_LADING"},
    )
    assert r_add.status_code == 201
    requirement_id: str = r_add.json()["id"]

    r_upload = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/documents/{requirement_id}/upload",
        files={"file": ("bill.pdf", b"content", "application/pdf")},
    )
    assert r_upload.status_code == 200

    # Check the activity log
    r_activity = await authenticated_client.get(
        "/api/v1/activity/",
        params={"limit": 5},
    )
    assert r_activity.status_code == 200
    events = [e["event"] for e in r_activity.json()]
    assert ActivityEvent.DOCUMENT_UPLOADED.value in events


# --- Readiness check ---


async def test_readiness_with_only_auto_generated_docs_is_ready(
    authenticated_client: AsyncClient,
) -> None:
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    r = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/readiness")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == _EXPECTED_READINESS_KEYS
    # Auto-generated documents always pass; no products with qualifications/packaging
    assert body["documents_ready"] is True
    assert body["certificates_ready"] is True
    assert body["packaging_ready"] is True
    assert body["is_ready"] is True
    assert body["missing_documents"] == []
    assert body["missing_certificates"] == []
    assert body["missing_packaging"] == []


async def test_readiness_with_pending_manual_doc_is_not_ready(
    authenticated_client: AsyncClient,
) -> None:
    doc_type = "BILL_OF_LADING"
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    # Add a custom (non-auto) requirement and leave it PENDING
    await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/requirements",
        json={"document_type": doc_type},
    )

    r = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["documents_ready"] is False
    assert body["is_ready"] is False
    assert doc_type in body["missing_documents"]


async def test_readiness_auto_generated_requirements_always_pass_documents_check(
    authenticated_client: AsyncClient,
) -> None:
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    # Auto-generated PACKING_LIST and COMMERCIAL_INVOICE are PENDING but should
    # not appear in missing_documents
    r = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["documents_ready"] is True
    assert "PACKING_LIST" not in body["missing_documents"]
    assert "COMMERCIAL_INVOICE" not in body["missing_documents"]


# --- Mark ready with readiness gate ---


async def test_mark_ready_when_ready_transitions_to_ready_to_ship(
    authenticated_client: AsyncClient,
) -> None:
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    r = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/mark-ready")
    assert r.status_code == 200
    assert r.json()["status"] == ShipmentStatus.READY_TO_SHIP.value


async def test_mark_ready_when_not_ready_returns_409_with_readiness_details(
    authenticated_client: AsyncClient,
) -> None:
    doc_type = "BILL_OF_LADING"
    shipment_id, _ = await _make_documents_pending_shipment(authenticated_client)

    # Add a pending manual requirement to block mark-ready
    await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/requirements",
        json={"document_type": doc_type},
    )

    r = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/mark-ready")
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["documents_ready"] is False
    assert detail["is_ready"] is False
    assert doc_type in detail["missing_documents"]
    assert set(detail.keys()) == _EXPECTED_READINESS_KEYS


# ─────────────────────────────────────────────────────────────────────────────
# Iter 104: PL/CI customs fields — ports, country of origin, HS code,
#           manufacturer block, marketplace, declaration
# ─────────────────────────────────────────────────────────────────────────────

# Expected resolved labels for the _PO_BASE / _make_vendor fixture data:
#   port_of_loading  "USLAX"  -> "Los Angeles, United States"
#   port_of_discharge "CNSHA" -> "Shanghai, China"
#   country_of_origin "US"    -> "United States"
#   vendor country    "CN"    -> "China"
#   marketplace       "AMZ"   -> "AMZ"
_EXPECTED_POL_LABEL = "Los Angeles"
_EXPECTED_POD_LABEL = "Shanghai"
_EXPECTED_COO_LABEL = "United States"
_EXPECTED_VENDOR_COUNTRY_LABEL = "China"
_EXPECTED_MARKETPLACE = "AMZ"
_EXPECTED_DECLARATION = "I declare that the information on this invoice is true and correct."
_EXPECTED_HS_CODE: str = str(_LINE_ITEM_A["hs_code"])


async def test_packing_list_contains_ports(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert _EXPECTED_POL_LABEL in pdf_text
    assert _EXPECTED_POD_LABEL in pdf_text


async def test_packing_list_contains_country_of_origin_header(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert _EXPECTED_COO_LABEL in pdf_text


async def test_packing_list_contains_hs_code_per_line(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    # HS code from PO line item must appear in PL
    assert _EXPECTED_HS_CODE in pdf_text


async def test_packing_list_contains_manufacturer_block(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    # Vendor acts as manufacturer; vendor name and country appear in the Shipper/Manufacturer block
    assert "ShipTest Vendor" in pdf_text
    assert _EXPECTED_VENDOR_COUNTRY_LABEL in pdf_text


async def test_commercial_invoice_contains_marketplace(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert _EXPECTED_MARKETPLACE in pdf_text


async def test_commercial_invoice_contains_ports(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert _EXPECTED_POL_LABEL in pdf_text
    assert _EXPECTED_POD_LABEL in pdf_text


async def test_commercial_invoice_contains_declaration(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert _EXPECTED_DECLARATION in pdf_text


async def test_commercial_invoice_seller_contains_vendor_country(authenticated_client: AsyncClient) -> None:
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)

    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r2 = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r2.status_code == 200
    pdf_text = _extract_pdf_text(r2.content)
    assert _EXPECTED_VENDOR_COUNTRY_LABEL in pdf_text


# ─────────────────────────────────────────────────────────────────────────────
# Iter 106: vessel/voyage, signatory/declaration, and schema migrations
# ─────────────────────────────────────────────────────────────────────────────

async def _booked_shipment_id(client: AsyncClient) -> str:
    """Create a BOOKED shipment and return its id."""
    shipment_id = await _ready_shipment_id(client)
    r = await client.post(
        f"/api/v1/shipments/{shipment_id}/book",
        json={"carrier": "Maersk", "booking_reference": "BK-99999", "pickup_date": "2026-05-20"},
    )
    assert r.status_code == 200
    return shipment_id


async def test_set_transport_happy_path(authenticated_client: AsyncClient) -> None:
    """PATCH /transport on a BOOKED shipment records vessel + voyage and returns them."""
    shipment_id = await _booked_shipment_id(authenticated_client)
    vessel_name = "MSC GULSUN"
    voyage_number = "031W"

    r = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/transport",
        json={"vessel_name": vessel_name, "voyage_number": voyage_number},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["vessel_name"] == vessel_name
    assert body["voyage_number"] == voyage_number


async def test_set_transport_requires_booked_status(authenticated_client: AsyncClient) -> None:
    """PATCH /transport on a READY_TO_SHIP shipment returns 409."""
    shipment_id = await _ready_shipment_id(authenticated_client)
    r = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/transport",
        json={"vessel_name": "SOME VESSEL", "voyage_number": "001E"},
    )
    assert r.status_code == 409


async def test_set_transport_whitespace_only_vessel_returns_422(authenticated_client: AsyncClient) -> None:
    """PATCH /transport rejects whitespace-only vessel_name."""
    shipment_id = await _booked_shipment_id(authenticated_client)
    r = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/transport",
        json={"vessel_name": "   ", "voyage_number": "001E"},
    )
    assert r.status_code == 422


async def test_set_transport_null_fields_accepted(authenticated_client: AsyncClient) -> None:
    """PATCH /transport accepts null vessel_name + voyage_number (clears previously set values)."""
    shipment_id = await _booked_shipment_id(authenticated_client)
    r = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/transport",
        json={"vessel_name": None, "voyage_number": None},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["vessel_name"] is None
    assert body["voyage_number"] is None


async def test_declare_happy_path(authenticated_client: AsyncClient) -> None:
    """POST /declare on a DOCUMENTS_PENDING shipment records signatory and declared_at."""
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r_sub = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/submit-for-documents")
    assert r_sub.status_code == 200

    signatory_name = "Jane Smith"
    signatory_title = "Export Manager"
    r = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/declare",
        json={"signatory_name": signatory_name, "signatory_title": signatory_title},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["signatory_name"] == signatory_name
    assert body["signatory_title"] == signatory_title
    assert body["declared_at"] is not None


async def test_declare_on_draft_returns_409(authenticated_client: AsyncClient) -> None:
    """POST /declare on a DRAFT shipment returns 409."""
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]
    # DRAFT status — declare should fail
    r = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/declare",
        json={"signatory_name": "Jane Smith", "signatory_title": "Manager"},
    )
    assert r.status_code == 409


async def test_declare_empty_signatory_name_returns_422(authenticated_client: AsyncClient) -> None:
    """POST /declare rejects empty signatory_name."""
    shipment_id = await _ready_shipment_id(authenticated_client)
    r = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/declare",
        json={"signatory_name": "  ", "signatory_title": "Manager"},
    )
    assert r.status_code == 422


async def test_packing_list_contains_vessel_and_voyage(authenticated_client: AsyncClient) -> None:
    """PL PDF contains vessel name and voyage number when set on a BOOKED shipment."""
    shipment_id = await _booked_shipment_id(authenticated_client)
    vessel_name = "MSC GULSUN"
    voyage_number = "031W"

    r_transport = await authenticated_client.patch(
        f"/api/v1/shipments/{shipment_id}/transport",
        json={"vessel_name": vessel_name, "voyage_number": voyage_number},
    )
    assert r_transport.status_code == 200

    r = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert r.status_code == 200
    pdf_text = _extract_pdf_text(r.content)
    assert vessel_name in pdf_text
    assert voyage_number in pdf_text


async def test_packing_list_no_vessel_voyage_when_not_set(authenticated_client: AsyncClient) -> None:
    """PL PDF generates without error when vessel + voyage are not set (pre-booking)."""
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/packing-list")
    assert r.status_code == 200
    assert len(r.content) > 0


async def test_commercial_invoice_contains_signatory_when_declared(authenticated_client: AsyncClient) -> None:
    """CI PDF contains signatory name and title when shipment is declared."""
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r_sub = await authenticated_client.post(f"/api/v1/shipments/{shipment_id}/submit-for-documents")
    assert r_sub.status_code == 200

    signatory_name = "Jane Smith"
    r_declare = await authenticated_client.post(
        f"/api/v1/shipments/{shipment_id}/declare",
        json={"signatory_name": signatory_name, "signatory_title": "Export Manager"},
    )
    assert r_declare.status_code == 200

    r = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r.status_code == 200
    pdf_text = _extract_pdf_text(r.content)
    assert signatory_name in pdf_text


async def test_commercial_invoice_unsigned_when_not_declared(authenticated_client: AsyncClient) -> None:
    """CI PDF contains '[unsigned]' placeholder when signatory has not been declared."""
    vendor_id, brand_id = await _make_vendor(authenticated_client)
    po = await _make_accepted_po(authenticated_client, vendor_id, brand_id)
    r1 = await authenticated_client.post(
        "/api/v1/shipments/",
        json={"po_id": po["id"], "line_items": [{"part_number": "PART-A", "quantity": 10, "uom": "PCS"}]},
    )
    assert r1.status_code == 201
    shipment_id: str = r1.json()["id"]

    r = await authenticated_client.get(f"/api/v1/shipments/{shipment_id}/commercial-invoice")
    assert r.status_code == 200
    pdf_text = _extract_pdf_text(r.content)
    assert "[unsigned]" in pdf_text
