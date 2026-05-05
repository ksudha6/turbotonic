from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

from src.domain.purchase_order import LineItemStatus, PurchaseOrder
from src.domain.shipment import Shipment
from src.domain.reference_labels import country_label, port_label
from src.domain.vendor_party import VendorParty

# Page margins — match po_pdf.py and invoice_pdf.py
_LEFT_MARGIN = 0.75 * inch
_RIGHT_MARGIN = 0.75 * inch
_TOP_MARGIN = 0.75 * inch
_BOTTOM_MARGIN = 0.75 * inch

# Usable page width on Letter (8.5in) minus margins
_PAGE_WIDTH = letter[0] - _LEFT_MARGIN - _RIGHT_MARGIN


def _date_str(dt) -> str:
    return dt.strftime("%Y-%m-%d")


def _fmt_decimal(value: Decimal | None) -> str:
    # None fields display as "-" per spec
    if value is None:
        return "-"
    return f"{value:.3f}"


def _fmt_int(value: int | None) -> str:
    if value is None:
        return "-"
    return str(value)


def _fmt_str(value: str | None) -> str:
    if value is None or not value.strip():
        return "-"
    return value


def resolve_shipper_party(
    shipment_shipper_party_id: str | None,
    vendor_default_shipper_party_id: str | None,
    party_index: dict[str, VendorParty],
) -> VendorParty | None:
    """Return the shipper VendorParty to render.

    Priority: per-shipment override, then vendor default, then None (fall back to flat vendor).
    party_index maps party_id to VendorParty object.
    """
    for party_id in (shipment_shipper_party_id, vendor_default_shipper_party_id):
        if party_id and party_id in party_index:
            return party_index[party_id]
    return None


def generate_packing_list_pdf(
    shipment: Shipment,
    po: PurchaseOrder,
    vendor_name: str,
    vendor_address: str,
    buyer_name: str,
    buyer_address: str,
    vendor_country: str = "",
    manufacturer_lookup: dict[str, dict[str, str]] | None = None,
    vendor_tax_id: str = "",
    # Iter 113: structured party lookup maps party_id -> VendorParty for shipper block.
    # vendor_default_shipper_party_id is the vendor-level fallback when no per-shipment override.
    party_lookup: dict[str, VendorParty] | None = None,
    vendor_default_shipper_party_id: str | None = None,
    # Iter 113: per-product manufacturer parties map part_number -> VendorParty.
    manufacturer_party_lookup: dict[str, VendorParty] | None = None,
) -> bytes:
    """Build a packing list PDF for the given Shipment and return it as raw bytes.

    manufacturer_lookup maps part_number → {name, address, country}. Retained as the
    free-text fallback path (iter 106). manufacturer_party_lookup maps part_number to a
    structured VendorParty (iter 113) and takes priority when present.
    Shipper block: uses shipment.shipper_party_id -> vendor default shipper -> flat vendor.
    """
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=_LEFT_MARGIN,
        rightMargin=_RIGHT_MARGIN,
        topMargin=_TOP_MARGIN,
        bottomMargin=_BOTTOM_MARGIN,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    body_style = ParagraphStyle(
        "Body",
        parent=normal,
        fontSize=9,
        leading=13,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=normal,
        fontSize=10,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=normal,
        fontSize=8,
        leading=11,
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=cell_style,
        fontName="Helvetica-Bold",
    )
    title_style = ParagraphStyle(
        "Title",
        parent=normal,
        fontSize=18,
        fontName="Helvetica-Bold",
        alignment=1,  # center
        spaceAfter=12,
    )

    story = []

    # -------------------------------------------------------------------------
    # 1. Title
    # -------------------------------------------------------------------------
    story.append(Paragraph("PACKING LIST", title_style))

    # -------------------------------------------------------------------------
    # 2. Header: shipment number, PO number, date, marketplace, ports, origin,
    #    vessel + voyage (iter 106, when populated post-booking)
    # -------------------------------------------------------------------------
    pol_label = port_label(po.port_of_loading) if po.port_of_loading else "-"
    pod_label = port_label(po.port_of_discharge) if po.port_of_discharge else "-"
    coo_label = country_label(po.country_of_origin) if po.country_of_origin else "-"

    header_data = [
        [
            Paragraph(f"<b>Shipment Number:</b> {shipment.shipment_number}", body_style),
            Paragraph(f"<b>PO Number:</b> {po.po_number}", body_style),
        ],
        [
            Paragraph(f"<b>Date:</b> {_date_str(shipment.created_at)}", body_style),
            Paragraph(f"<b>Marketplace:</b> {shipment.marketplace}", body_style),
        ],
        [
            Paragraph(f"<b>Port of Loading:</b> {pol_label}", body_style),
            Paragraph(f"<b>Port of Discharge:</b> {pod_label}", body_style),
        ],
        [
            Paragraph(f"<b>Country of Origin:</b> {coo_label}", body_style),
            Paragraph("", body_style),
        ],
    ]

    # Vessel + voyage rows only appear when populated (iter 106)
    if shipment.vessel_name or shipment.voyage_number:
        vessel_str = _fmt_str(shipment.vessel_name)
        voyage_str = _fmt_str(shipment.voyage_number)
        header_data.append([
            Paragraph(f"<b>Vessel:</b> {vessel_str}", body_style),
            Paragraph(f"<b>Voyage:</b> {voyage_str}", body_style),
        ])

    # Pallet count row only appears when populated (iter 110)
    if shipment.pallet_count is not None:
        header_data.append([
            Paragraph(f"<b>Pallet Count:</b> {shipment.pallet_count}", body_style),
            Paragraph("", body_style),
        ])
    header_table = Table(header_data, colWidths=[_PAGE_WIDTH / 2, _PAGE_WIDTH / 2])
    header_table.setStyle(
        TableStyle([
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------------------
    # 3. Parties: Shipper/Manufacturer and Consignee (buyer) side-by-side.
    # Iter 113 priority chain for shipper block:
    #   1. shipment.shipper_party_id -> structured VendorParty
    #   2. vendor.default_shipper_party_id -> structured VendorParty
    #   3. fallback to flat vendor address (iter pre-113 behavior)
    # Iter 106 free-text manufacturer_lookup is the fallback for per-line manufacturer.
    # vendor_country resolves from the Vendor aggregate; country_label handles unknown codes.
    # -------------------------------------------------------------------------
    story.append(Paragraph("Parties", heading_style))

    # Determine the shipper / manufacturer block to display.
    # Iter 113: resolve shipper from VendorParty priority chain.
    _party_index = party_lookup or {}
    shipper_party = resolve_shipper_party(
        shipment.shipper_party_id if hasattr(shipment, "shipper_party_id") else None,
        vendor_default_shipper_party_id,
        _party_index,
    )

    if shipper_party is not None:
        # Structured party takes priority over all free-text paths.
        mfr_name = shipper_party.legal_name
        mfr_address = shipper_party.address
        mfr_country = shipper_party.country
    else:
        # Iter 106 / pre-113 fallback: use manufacturer_lookup (free-text) or vendor.
        mfr_name = vendor_name
        mfr_address = vendor_address
        mfr_country = vendor_country
        if manufacturer_lookup:
            mfr_entries = [
                manufacturer_lookup[item.part_number]
                for item in shipment.line_items
                if item.part_number in manufacturer_lookup
                    and manufacturer_lookup[item.part_number].get("name", "").strip()
            ]
            if mfr_entries:
                # Use the first non-empty manufacturer; typical case is one manufacturer per shipment.
                first = mfr_entries[0]
                mfr_name = first.get("name", vendor_name) or vendor_name
                mfr_address = first.get("address", vendor_address) or vendor_address
                mfr_country = first.get("country", vendor_country) or vendor_country

    mfr_country_display = country_label(mfr_country) if mfr_country else ""
    shipper_content = [
        Paragraph("<b>Shipper / Manufacturer</b>", cell_bold),
        Paragraph(mfr_name, cell_style),
        Paragraph(_fmt_str(mfr_address), cell_style),
        Paragraph(mfr_country_display, cell_style),
    ]
    consignee_content = [
        Paragraph("<b>Consignee</b>", cell_bold),
        Paragraph(buyer_name, cell_style),
        Paragraph(_fmt_str(buyer_address), cell_style),
    ]

    parties_data = [[shipper_content, consignee_content]]
    parties_table = Table(
        parties_data,
        colWidths=[_PAGE_WIDTH / 2 - 6, _PAGE_WIDTH / 2 - 6],
        hAlign="LEFT",
    )
    parties_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (0, 0), 0.5, colors.lightgrey),
            ("BOX", (1, 0), (1, 0), 0.5, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(0.97, 0.97, 0.97)),
        ])
    )
    story.append(parties_table)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------------------
    # 4. Line items table
    # Columns: #, Description, HS Code, Quantity, UOM, Package Count,
    #          Net Weight, Gross Weight, Dimensions, Country of Origin
    # HS code sourced from PO ACCEPTED line items keyed by part_number
    # -------------------------------------------------------------------------
    story.append(Paragraph("Line Items", heading_style))

    # Build lookup: part_number -> PO line item (HS code source)
    po_line_map = {
        li.part_number: li
        for li in po.line_items
        if li.status is LineItemStatus.ACCEPTED
    }

    col_widths = [
        0.25 * inch,   # #
        1.00 * inch,   # Description
        0.60 * inch,   # HS Code
        0.40 * inch,   # Qty
        0.35 * inch,   # UOM
        0.50 * inch,   # Pkg Count
        0.60 * inch,   # Net Weight
        0.60 * inch,   # Gross Weight
        0.75 * inch,   # Dimensions
        0.80 * inch,   # Country of Origin
    ]

    header_row = [
        Paragraph("<b>#</b>", cell_bold),
        Paragraph("<b>Description</b>", cell_bold),
        Paragraph("<b>HS Code</b>", cell_bold),
        Paragraph("<b>Qty</b>", cell_bold),
        Paragraph("<b>UOM</b>", cell_bold),
        Paragraph("<b>Pkg Count</b>", cell_bold),
        Paragraph("<b>Net Weight</b>", cell_bold),
        Paragraph("<b>Gross Weight</b>", cell_bold),
        Paragraph("<b>Dimensions</b>", cell_bold),
        Paragraph("<b>Country of Origin</b>", cell_bold),
    ]

    line_rows = []
    for idx, item in enumerate(shipment.line_items, start=1):
        po_li = po_line_map.get(item.part_number)
        hs_code = po_li.hs_code if po_li is not None else ""
        line_rows.append([
            Paragraph(str(idx), cell_style),
            Paragraph(f"{item.part_number}<br/>{item.description}", cell_style),
            Paragraph(_fmt_str(hs_code), cell_style),
            Paragraph(str(item.quantity), cell_style),
            Paragraph(item.uom, cell_style),
            Paragraph(_fmt_int(item.package_count), cell_style),
            Paragraph(_fmt_decimal(item.net_weight), cell_style),
            Paragraph(_fmt_decimal(item.gross_weight), cell_style),
            Paragraph(_fmt_str(item.dimensions), cell_style),
            Paragraph(_fmt_str(item.country_of_origin), cell_style),
        ])

    num_data_rows = len(line_rows)
    last_row = num_data_rows + 1

    # Summary totals: sum package_count and weights where provided; "-" when no data
    total_packages = sum(
        (item.package_count for item in shipment.line_items if item.package_count is not None),
        0,
    )
    net_weights = [item.net_weight for item in shipment.line_items if item.net_weight is not None]
    gross_weights = [item.gross_weight for item in shipment.line_items if item.gross_weight is not None]

    total_net = sum(net_weights, Decimal("0")) if net_weights else None
    total_gross = sum(gross_weights, Decimal("0")) if gross_weights else None
    # Package count total is 0 if no items have it set; treat that as "-"
    has_packages = any(item.package_count is not None for item in shipment.line_items)

    summary_row = [
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph(f"<b>{total_packages}</b>" if has_packages else "<b>-</b>", cell_bold),
        Paragraph(f"<b>{_fmt_decimal(total_net)}</b>", cell_bold),
        Paragraph(f"<b>{_fmt_decimal(total_gross)}</b>", cell_bold),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
    ]

    items_table_data = [header_row] + line_rows + [summary_row]

    items_table = Table(items_table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(
        TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.85, 0.85)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            # Data rows alternating
            ("ROWBACKGROUNDS", (0, 1), (-1, num_data_rows), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            # Summary row
            ("BACKGROUND", (0, last_row), (-1, last_row), colors.Color(0.88, 0.88, 0.88)),
            ("LINEABOVE", (0, last_row), (-1, last_row), 0.75, colors.grey),
            # Grid and padding
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(items_table)

    doc.build(story)
    return buf.getvalue()
