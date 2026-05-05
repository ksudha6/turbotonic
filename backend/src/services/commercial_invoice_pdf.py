from __future__ import annotations

import io
from datetime import UTC, datetime
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
from src.domain.reference_labels import (
    currency_label,
    country_label,
    incoterm_label,
    payment_terms_label,
    port_label,
)

# Page margins — match po_pdf.py
_LEFT_MARGIN = 0.75 * inch
_RIGHT_MARGIN = 0.75 * inch
_TOP_MARGIN = 0.75 * inch
_BOTTOM_MARGIN = 0.75 * inch

# Usable page width on Letter (8.5in) minus margins
_PAGE_WIDTH = letter[0] - _LEFT_MARGIN - _RIGHT_MARGIN


def generate_ci_number(shipment_number: str) -> str:
    """Deterministic CI number derived from shipment number.

    Format: CI-{shipment_number}, e.g. CI-SHP-20260414-A3F2.
    """
    return f"CI-{shipment_number}"


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _weight_str(value: Decimal | None) -> str:
    # None weight fields render as dash per spec
    if value is None:
        return "-"
    return f"{value:.3f}"


def generate_commercial_invoice_pdf(
    shipment: Shipment,
    po: PurchaseOrder,
    vendor_name: str,
    vendor_address: str,
    buyer_name: str,
    buyer_address: str,
    vendor_country: str = "",
    buyer_country: str = "",
    buyer_tax_id: str = "",
    vendor_tax_id: str = "",
) -> bytes:
    """Build a commercial invoice PDF for the given Shipment and PurchaseOrder.

    Returns the PDF as raw bytes. Signatory details (iter 106) are read from the
    Shipment aggregate when present; CI renders "[unsigned]" when absent.
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

    title_style = ParagraphStyle(
        "CITitle",
        parent=normal,
        fontSize=18,
        fontName="Helvetica-Bold",
        alignment=1,  # center
        spaceAfter=12,
    )
    body_style = ParagraphStyle(
        "CIBody",
        parent=normal,
        fontSize=9,
        leading=13,
    )
    heading_style = ParagraphStyle(
        "CISectionHeading",
        parent=normal,
        fontSize=10,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "CICell",
        parent=normal,
        fontSize=8,
        leading=11,
    )
    cell_bold = ParagraphStyle(
        "CICellBold",
        parent=cell_style,
        fontName="Helvetica-Bold",
    )

    story: list = []

    # -------------------------------------------------------------------------
    # 1. Title
    # -------------------------------------------------------------------------
    story.append(Paragraph("COMMERCIAL INVOICE", title_style))

    # -------------------------------------------------------------------------
    # 2. Header rows
    # -------------------------------------------------------------------------
    ci_number = generate_ci_number(shipment.shipment_number)
    today = _date_str(datetime.now(UTC))
    pol_label = port_label(po.port_of_loading) if po.port_of_loading else "-"
    pod_label = port_label(po.port_of_discharge) if po.port_of_discharge else "-"

    header_data = [
        [
            Paragraph(f"<b>CI Number:</b> {ci_number}", body_style),
            Paragraph(f"<b>Date:</b> {today}", body_style),
        ],
        [
            Paragraph(f"<b>PO Number:</b> {po.po_number}", body_style),
            Paragraph(f"<b>Shipment Number:</b> {shipment.shipment_number}", body_style),
        ],
        [
            Paragraph(f"<b>Marketplace:</b> {shipment.marketplace}", body_style),
            Paragraph("", body_style),
        ],
        [
            Paragraph(f"<b>Port of Loading:</b> {pol_label}", body_style),
            Paragraph(f"<b>Port of Discharge:</b> {pod_label}", body_style),
        ],
    ]
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

    # -------------------------------------------------------------------------
    # 3. Trade terms and currency
    # -------------------------------------------------------------------------
    terms_data = [
        [
            Paragraph(
                f"<b>Incoterm:</b> {po.incoterm} - {incoterm_label(po.incoterm)}",
                body_style,
            ),
            Paragraph(
                f"<b>Payment Terms:</b> {po.payment_terms} - {payment_terms_label(po.payment_terms)}",
                body_style,
            ),
        ],
        [
            Paragraph(
                f"<b>Currency:</b> {po.currency} - {currency_label(po.currency)}",
                body_style,
            ),
            Paragraph("", body_style),
        ],
    ]
    terms_table = Table(terms_data, colWidths=[_PAGE_WIDTH / 2, _PAGE_WIDTH / 2])
    terms_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(terms_table)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------------------
    # 4. Parties: Seller (left) / Buyer + Consignee (right)
    # -------------------------------------------------------------------------
    story.append(Paragraph("Parties", heading_style))

    vendor_country_display = country_label(vendor_country) if vendor_country else ""
    seller_content: list = [
        Paragraph("<b>Seller</b>", cell_bold),
        Paragraph(vendor_name, cell_style),
        Paragraph(vendor_address, cell_style),
        Paragraph(vendor_country_display, cell_style),
    ]
    if vendor_tax_id:
        seller_content.append(Paragraph(f"Tax ID: {vendor_tax_id}", cell_style))
    buyer_country_display = country_label(buyer_country) if buyer_country else country_label(po.buyer_country)
    buyer_content: list = [
        Paragraph("<b>Buyer</b>", cell_bold),
        Paragraph(buyer_name, cell_style),
        Paragraph(buyer_address, cell_style),
        Paragraph(buyer_country_display, cell_style),
    ]
    if buyer_tax_id:
        buyer_content.append(Paragraph(f"Tax ID: {buyer_tax_id}", cell_style))
    buyer_content += [
        Paragraph("", cell_style),
        Paragraph("<b>Consignee</b>", cell_bold),
        Paragraph(po.ship_to_address, cell_style),
    ]

    parties_data = [[seller_content, buyer_content]]
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
    # 5. Line items table
    # -------------------------------------------------------------------------
    story.append(Paragraph("Line Items", heading_style))

    # Build lookup: part_number -> PO line item (for HS code and unit price)
    po_line_map = {
        li.part_number: li
        for li in po.line_items
        if li.status is LineItemStatus.ACCEPTED
    }

    # Column widths to fit on Letter page
    col_widths = [
        0.25 * inch,   # #
        1.50 * inch,   # Description
        0.65 * inch,   # HS Code
        0.45 * inch,   # Qty
        0.35 * inch,   # UOM
        0.70 * inch,   # Unit Price
        0.70 * inch,   # Net Weight
        0.70 * inch,   # Gross Weight
        0.80 * inch,   # Country of Origin
        0.70 * inch,   # Line Value
    ]

    header_row = [
        Paragraph("<b>#</b>", cell_bold),
        Paragraph("<b>Description</b>", cell_bold),
        Paragraph("<b>HS Code</b>", cell_bold),
        Paragraph("<b>Qty</b>", cell_bold),
        Paragraph("<b>UOM</b>", cell_bold),
        Paragraph("<b>Unit Price</b>", cell_bold),
        Paragraph("<b>Net Wt</b>", cell_bold),
        Paragraph("<b>Gross Wt</b>", cell_bold),
        Paragraph("<b>Origin</b>", cell_bold),
        Paragraph("<b>Line Value</b>", cell_bold),
    ]

    line_rows: list = []
    total_quantity: int = 0
    total_value = Decimal("0")
    total_net_weight: Decimal | None = None
    total_gross_weight: Decimal | None = None
    total_packages: int = 0

    for idx, sli in enumerate(shipment.line_items, start=1):
        po_li = po_line_map.get(sli.part_number)
        hs_code = po_li.hs_code if po_li is not None else ""
        unit_price = po_li.unit_price if po_li is not None else Decimal("0")
        coo = getattr(sli, "country_of_origin", None) or (
            po_li.country_of_origin if po_li is not None else ""
        )
        net_weight = getattr(sli, "net_weight", None)
        gross_weight = getattr(sli, "gross_weight", None)
        package_count = getattr(sli, "package_count", None) or 0

        line_value = sli.quantity * unit_price
        total_quantity += sli.quantity
        total_value += line_value

        # Accumulate weights: if any line has a value, the total is non-None
        if net_weight is not None:
            total_net_weight = (total_net_weight or Decimal("0")) + net_weight
        if gross_weight is not None:
            total_gross_weight = (total_gross_weight or Decimal("0")) + gross_weight
        total_packages += package_count

        line_rows.append([
            Paragraph(str(idx), cell_style),
            Paragraph(sli.description, cell_style),
            Paragraph(hs_code, cell_style),
            Paragraph(str(sli.quantity), cell_style),
            Paragraph(sli.uom, cell_style),
            Paragraph(_money(unit_price), cell_style),
            Paragraph(_weight_str(net_weight), cell_style),
            Paragraph(_weight_str(gross_weight), cell_style),
            Paragraph(country_label(coo) if coo else "-", cell_style),
            Paragraph(_money(line_value), cell_style),
        ])

    num_data_rows = len(line_rows)

    items_table = Table([header_row] + line_rows, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.85, 0.85)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ROWBACKGROUNDS", (0, 1), (-1, num_data_rows), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),   # Qty
            ("ALIGN", (5, 0), (5, -1), "RIGHT"),   # Unit Price
            ("ALIGN", (6, 0), (6, -1), "RIGHT"),   # Net Wt
            ("ALIGN", (7, 0), (7, -1), "RIGHT"),   # Gross Wt
            ("ALIGN", (9, 0), (9, -1), "RIGHT"),   # Line Value
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(items_table)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------------------
    # 6. Summary
    # -------------------------------------------------------------------------
    story.append(Paragraph("Summary", heading_style))

    label_width = 1.80 * inch
    value_width = _PAGE_WIDTH - label_width

    # Iter 110: export_reason defaults to "Sale" on render when empty.
    export_reason_display = shipment.export_reason if shipment.export_reason else "Sale"

    summary_rows = [
        ["Total Quantity", str(total_quantity)],
        ["Total Value", f"{_money(total_value)} {po.currency}"],
        ["Total Net Weight", _weight_str(total_net_weight)],
        ["Total Gross Weight", _weight_str(total_gross_weight)],
        ["Total Packages", str(total_packages)],
        ["Marks and Numbers", shipment.shipment_number],
        ["Reason for Export", export_reason_display],
    ]

    summary_data = [
        [
            Paragraph(f"<b>{label}</b>", cell_style),
            Paragraph(value, cell_style),
        ]
        for label, value in summary_rows
    ]

    summary_table = Table(summary_data, colWidths=[label_width, value_width])
    summary_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.Color(0.96, 0.96, 0.96)]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ])
    )
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # -------------------------------------------------------------------------
    # 7. Declaration
    # Standard shipper's declaration for customs acceptance (iter 104).
    # Iter 106: signatory name, title, and declaration date rendered when present.
    # Falls back to "[unsigned]" / "[undated]" when not yet declared.
    # -------------------------------------------------------------------------
    _DECLARATION_TEXT = (
        "I declare that the information on this invoice is true and correct."
    )
    declaration_style = ParagraphStyle(
        "CIDeclaration",
        parent=normal,
        fontSize=8,
        leading=12,
        borderPad=6,
        borderColor=colors.lightgrey,
        borderWidth=0.5,
        backColor=colors.Color(0.97, 0.97, 0.97),
    )
    story.append(Paragraph(_DECLARATION_TEXT, declaration_style))

    # Signatory block — iter 106
    signatory_name = shipment.signatory_name or "[unsigned]"
    signatory_title = shipment.signatory_title or ""
    declared_at_str = _date_str(shipment.declared_at) if shipment.declared_at else "[undated]"

    signatory_parts = [signatory_name]
    if signatory_title:
        signatory_parts.append(signatory_title)
    signatory_parts.append(declared_at_str)

    signatory_text = " | ".join(signatory_parts)
    story.append(Spacer(1, 6))
    story.append(Paragraph(signatory_text, declaration_style))

    doc.build(story)
    return buf.getvalue()
