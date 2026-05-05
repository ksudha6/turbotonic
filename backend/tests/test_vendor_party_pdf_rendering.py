"""Iter 113: PDF rendering priority chain tests."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.purchase_order import PurchaseOrder
from src.domain.shipment import Shipment, ShipmentLineItem, ShipmentStatus
from src.domain.vendor_party import VendorParty, VendorPartyRole
from src.services.packing_list_pdf import generate_packing_list_pdf, resolve_shipper_party
from src.services.commercial_invoice_pdf import generate_commercial_invoice_pdf, resolve_seller_party


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_party(
    *,
    vendor_id: str = "vendor-1",
    role: VendorPartyRole = VendorPartyRole.SELLER,
    legal_name: str = "Test Party Co",
    address: str = "Party Address",
    country: str = "SG",
    tax_id: str = "",
) -> VendorParty:
    return VendorParty.create(
        vendor_id=vendor_id,
        role=role,
        legal_name=legal_name,
        address=address,
        country=country,
        tax_id=tax_id,
    )


def _make_shipment(*, shipper_party_id: str | None = None) -> Shipment:
    from src.domain.shipment import ShipmentStatus
    now = datetime.now(UTC)
    item = ShipmentLineItem(
        part_number="PN-001",
        product_id=None,
        description="Widget",
        quantity=10,
        uom="EA",
    )
    shipment = Shipment(
        id=str(uuid4()),
        po_id="po-1",
        shipment_number="SHP-20260413-AAAA",
        marketplace="US",
        status=ShipmentStatus.DRAFT,
        line_items=[item],
        created_at=now,
        updated_at=now,
        pallet_count=2,
        export_reason="Sale",
        shipper_party_id=shipper_party_id,
    )
    return shipment


def _make_po() -> PurchaseOrder:
    from src.domain.purchase_order import POStatus, POType, LineItem, LineItemStatus
    now = datetime.now(UTC)
    li = LineItem(
        part_number="PN-001",
        description="Widget",
        quantity=10,
        uom="EA",
        unit_price=Decimal("5.00"),
        hs_code="8471.30",
        country_of_origin="CN",
        status=LineItemStatus.ACCEPTED,
    )
    return PurchaseOrder(
        id="po-1",
        po_number="PO-001",
        status=POStatus.ACCEPTED,
        po_type=POType.PROCUREMENT,
        vendor_id="vendor-1",
        buyer_name="Buyer Co",
        buyer_country="US",
        ship_to_address="123 Buyer St",
        payment_terms="TT",
        currency="USD",
        issued_date=now,
        required_delivery_date=now,
        terms_and_conditions="",
        incoterm="FOB",
        port_of_loading="CNSHA",
        port_of_discharge="USLAX",
        country_of_origin="CN",
        country_of_destination="US",
        line_items=[li],
        rejection_history=[],
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Shipper block tests
# ---------------------------------------------------------------------------

def test_resolve_shipper_party_prefers_shipment_override() -> None:
    shipment_party_id = "party-ship"
    default_party_id = "party-default"
    party = _make_party(role=VendorPartyRole.SHIPPER, legal_name="Shipment Shipper")
    default_party = _make_party(role=VendorPartyRole.SHIPPER, legal_name="Default Shipper")

    # Build party_index with fake IDs
    party_index = {shipment_party_id: party, default_party_id: default_party}
    result = resolve_shipper_party(shipment_party_id, default_party_id, party_index)
    assert result is not None
    assert result.legal_name == "Shipment Shipper"


def test_resolve_shipper_party_falls_back_to_vendor_default() -> None:
    default_party_id = "party-default"
    party = _make_party(role=VendorPartyRole.SHIPPER, legal_name="Default Shipper")
    result = resolve_shipper_party(None, default_party_id, {default_party_id: party})
    assert result is not None
    assert result.legal_name == "Default Shipper"


def test_resolve_shipper_party_returns_none_when_no_parties() -> None:
    result = resolve_shipper_party(None, None, {})
    assert result is None


def test_packing_list_renders_shipper_from_shipment_party() -> None:
    shipper_party = _make_party(
        role=VendorPartyRole.SHIPPER, legal_name="Per-Shipment Shipper", country="SG"
    )
    party_id = shipper_party.id
    shipment = _make_shipment(shipper_party_id=party_id)
    po = _make_po()

    pdf_bytes = generate_packing_list_pdf(
        shipment=shipment,
        po=po,
        vendor_name="Flat Vendor",
        vendor_address="Flat Vendor Addr",
        buyer_name="Buyer",
        buyer_address="Buyer Addr",
        vendor_country="CN",
        party_lookup={party_id: shipper_party},
    )

    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Per-Shipment Shipper" in text
    assert "Flat Vendor" not in text


def test_packing_list_falls_back_to_vendor_default_shipper() -> None:
    default_shipper = _make_party(
        role=VendorPartyRole.SHIPPER, legal_name="Vendor Default Shipper", country="CN"
    )
    default_party_id = default_shipper.id
    shipment = _make_shipment(shipper_party_id=None)  # no per-shipment override
    po = _make_po()

    pdf_bytes = generate_packing_list_pdf(
        shipment=shipment,
        po=po,
        vendor_name="Flat Vendor",
        vendor_address="Flat Vendor Addr",
        buyer_name="Buyer",
        buyer_address="Buyer Addr",
        vendor_country="CN",
        party_lookup={default_party_id: default_shipper},
        vendor_default_shipper_party_id=default_party_id,
    )

    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Vendor Default Shipper" in text


def test_packing_list_falls_back_to_flat_vendor_when_no_shipper_party() -> None:
    shipment = _make_shipment(shipper_party_id=None)
    po = _make_po()

    pdf_bytes = generate_packing_list_pdf(
        shipment=shipment,
        po=po,
        vendor_name="Legacy Flat Vendor",
        vendor_address="Legacy Address",
        buyer_name="Buyer",
        buyer_address="Buyer Addr",
        vendor_country="CN",
    )

    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Legacy Flat Vendor" in text


def test_packing_list_falls_back_to_free_text_manufacturer() -> None:
    """When manufacturer_party_id is None and free-text manufacturer_name is set, use free-text."""
    shipment = _make_shipment()
    po = _make_po()

    pdf_bytes = generate_packing_list_pdf(
        shipment=shipment,
        po=po,
        vendor_name="Vendor",
        vendor_address="Vendor Addr",
        buyer_name="Buyer",
        buyer_address="Buyer Addr",
        vendor_country="CN",
        manufacturer_lookup={"PN-001": {"name": "Free-Text Mfr", "address": "Mfr Addr", "country": "CN"}},
    )

    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Free-Text Mfr" in text


# ---------------------------------------------------------------------------
# Seller block tests (CI)
# ---------------------------------------------------------------------------

def test_resolve_seller_party_prefers_po_override() -> None:
    po_party_id = "party-po"
    default_party_id = "party-default"
    po_party = _make_party(role=VendorPartyRole.SELLER, legal_name="PO Seller")
    default_party = _make_party(role=VendorPartyRole.SELLER, legal_name="Default Seller")
    party_index = {po_party_id: po_party, default_party_id: default_party}
    result = resolve_seller_party(po_party_id, default_party_id, party_index)
    assert result is not None
    assert result.legal_name == "PO Seller"


def test_resolve_seller_party_falls_back_to_vendor_default() -> None:
    default_party_id = "party-default"
    party = _make_party(role=VendorPartyRole.SELLER, legal_name="Default Seller")
    result = resolve_seller_party(None, default_party_id, {default_party_id: party})
    assert result is not None
    assert result.legal_name == "Default Seller"


def test_commercial_invoice_renders_seller_party() -> None:
    seller_party = _make_party(
        role=VendorPartyRole.SELLER, legal_name="HK Trading Co", country="HK", tax_id="HK-T-001"
    )
    party_id = seller_party.id
    shipment = _make_shipment()
    po = _make_po()

    pdf_bytes = generate_commercial_invoice_pdf(
        shipment=shipment,
        po=po,
        vendor_name="Flat Vendor Name",
        vendor_address="Flat Vendor Addr",
        buyer_name="Buyer",
        buyer_address="Buyer Addr",
        vendor_country="CN",
        party_lookup={party_id: seller_party},
        po_seller_party_id=party_id,
    )

    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "HK Trading Co" in text
    assert "HK-T-001" in text
    assert "Flat Vendor Name" not in text


def test_commercial_invoice_falls_back_to_vendor_default_seller() -> None:
    default_seller = _make_party(
        role=VendorPartyRole.SELLER, legal_name="Vendor Default Seller", country="US"
    )
    default_party_id = default_seller.id
    shipment = _make_shipment()
    po = _make_po()

    pdf_bytes = generate_commercial_invoice_pdf(
        shipment=shipment,
        po=po,
        vendor_name="Flat Vendor",
        vendor_address="Flat Addr",
        buyer_name="Buyer",
        buyer_address="Buyer Addr",
        vendor_country="CN",
        party_lookup={default_party_id: default_seller},
        vendor_default_seller_party_id=default_party_id,
    )

    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Vendor Default Seller" in text


def test_commercial_invoice_falls_back_to_vendor_tax_id_when_no_seller_party() -> None:
    shipment = _make_shipment()
    po = _make_po()

    pdf_bytes = generate_commercial_invoice_pdf(
        shipment=shipment,
        po=po,
        vendor_name="Flat Vendor",
        vendor_address="Flat Addr",
        buyer_name="Buyer",
        buyer_address="Buyer Addr",
        vendor_country="CN",
        vendor_tax_id="LEGACY-TAX-123",
    )

    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "LEGACY-TAX-123" in text


def test_commercial_invoice_omits_tax_id_line_when_all_empty() -> None:
    shipment = _make_shipment()
    po = _make_po()

    pdf_bytes = generate_commercial_invoice_pdf(
        shipment=shipment,
        po=po,
        vendor_name="No Tax Vendor",
        vendor_address="Addr",
        buyer_name="Buyer",
        buyer_address="Buyer Addr",
        vendor_country="CN",
        vendor_tax_id="",
    )

    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Tax ID:" not in text
