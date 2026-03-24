from __future__ import annotations

import io

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

from src.domain.purchase_order import PurchaseOrder
from src.domain.reference_labels import (
    currency_label,
    incoterm_label,
    payment_terms_label,
    country_label,
    port_label,
)

# Page margins
_LEFT_MARGIN = 0.75 * inch
_RIGHT_MARGIN = 0.75 * inch
_TOP_MARGIN = 0.75 * inch
_BOTTOM_MARGIN = 0.75 * inch

# Usable page width on Letter (8.5in) minus margins
_PAGE_WIDTH = letter[0] - _LEFT_MARGIN - _RIGHT_MARGIN


def _date_str(dt) -> str:
    return dt.strftime("%Y-%m-%d")


def _money(value) -> str:
    return f"{value:.2f}"


def generate_po_pdf(
    po: PurchaseOrder,
    vendor_name: str,
    vendor_country: str,
) -> bytes:
    """Build a PDF for the given PurchaseOrder and return it as raw bytes."""
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

    story = []

    # -------------------------------------------------------------------------
    # 1. Header
    # -------------------------------------------------------------------------
    title_style = ParagraphStyle(
        "Title",
        parent=normal,
        fontSize=18,
        fontName="Helvetica-Bold",
        alignment=1,  # center
        spaceAfter=12,
    )
    story.append(Paragraph("PURCHASE ORDER", title_style))

    # PO number (left) and status (right) in a two-cell table
    po_header_data = [
        [
            Paragraph(f"<b>PO Number:</b> {po.po_number}", body_style),
            Paragraph(f"<b>Status:</b> {po.status.value}", body_style),
        ]
    ]
    po_header_table = Table(po_header_data, colWidths=[_PAGE_WIDTH / 2, _PAGE_WIDTH / 2])
    po_header_table.setStyle(
        TableStyle([
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(po_header_table)

    dates_data = [
        [
            Paragraph(f"<b>Issued Date:</b> {_date_str(po.issued_date)}", body_style),
            Paragraph(
                f"<b>Required Delivery:</b> {_date_str(po.required_delivery_date)}",
                body_style,
            ),
        ]
    ]
    dates_table = Table(dates_data, colWidths=[_PAGE_WIDTH / 2, _PAGE_WIDTH / 2])
    dates_table.setStyle(
        TableStyle([
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    story.append(dates_table)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------------------
    # 2. Buyer / Vendor
    # -------------------------------------------------------------------------
    story.append(Paragraph("Parties", heading_style))

    buyer_content = [
        Paragraph("<b>Buyer</b>", cell_bold),
        Paragraph(po.buyer_name, cell_style),
        Paragraph(country_label(po.buyer_country), cell_style),
        Paragraph(po.ship_to_address, cell_style),
    ]
    vendor_content = [
        Paragraph("<b>Vendor</b>", cell_bold),
        Paragraph(vendor_name, cell_style),
        Paragraph(country_label(vendor_country), cell_style),
    ]

    parties_data = [[buyer_content, vendor_content]]
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
    # 3. Trade Details
    # -------------------------------------------------------------------------
    story.append(Paragraph("Trade Details", heading_style))

    trade_rows = [
        ["Incoterm", f"{po.incoterm} - {incoterm_label(po.incoterm)}"],
        ["Payment Terms", f"{po.payment_terms} - {payment_terms_label(po.payment_terms)}"],
        ["Currency", f"{po.currency} - {currency_label(po.currency)}"],
        ["Port of Loading", port_label(po.port_of_loading)],
        ["Port of Discharge", port_label(po.port_of_discharge)],
        ["Country of Origin", country_label(po.country_of_origin)],
        ["Country of Destination", country_label(po.country_of_destination)],
    ]

    label_width = 2.0 * inch
    value_width = _PAGE_WIDTH - label_width

    trade_data = [
        [
            Paragraph(f"<b>{label}</b>", cell_style),
            Paragraph(value, cell_style),
        ]
        for label, value in trade_rows
    ]

    trade_table = Table(trade_data, colWidths=[label_width, value_width])
    trade_table.setStyle(
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
    story.append(trade_table)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------------------
    # 4. Line Items Table
    # -------------------------------------------------------------------------
    story.append(Paragraph("Line Items", heading_style))

    # Column widths: #, Part Number, Description, Qty, UoM, Unit Price, HS Code, Origin, Line Total
    col_widths = [
        0.30 * inch,   # #
        0.90 * inch,   # Part Number
        2.00 * inch,   # Description (most space)
        0.40 * inch,   # Qty
        0.40 * inch,   # UoM
        0.70 * inch,   # Unit Price
        0.65 * inch,   # HS Code
        0.80 * inch,   # Origin
        0.75 * inch,   # Line Total
    ]

    header_row = [
        Paragraph("<b>#</b>", cell_bold),
        Paragraph("<b>Part Number</b>", cell_bold),
        Paragraph("<b>Description</b>", cell_bold),
        Paragraph("<b>Qty</b>", cell_bold),
        Paragraph("<b>UoM</b>", cell_bold),
        Paragraph("<b>Unit Price</b>", cell_bold),
        Paragraph("<b>HS Code</b>", cell_bold),
        Paragraph("<b>Origin</b>", cell_bold),
        Paragraph("<b>Line Total</b>", cell_bold),
    ]

    line_rows = []
    for idx, item in enumerate(po.line_items, start=1):
        line_total = item.quantity * item.unit_price
        line_rows.append([
            Paragraph(str(idx), cell_style),
            Paragraph(item.part_number, cell_style),
            Paragraph(item.description, cell_style),
            Paragraph(str(item.quantity), cell_style),
            Paragraph(item.uom, cell_style),
            Paragraph(_money(item.unit_price), cell_style),
            Paragraph(item.hs_code, cell_style),
            Paragraph(country_label(item.country_of_origin), cell_style),
            Paragraph(_money(line_total), cell_style),
        ])

    # Total row
    total_row = [
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("<b>Total</b>", cell_bold),
        Paragraph(f"<b>{_money(po.total_value)}</b>", cell_bold),
    ]

    items_table_data = [header_row] + line_rows + [total_row]

    items_table = Table(items_table_data, colWidths=col_widths, repeatRows=1)
    num_data_rows = len(line_rows)
    last_row = num_data_rows + 1  # 0-indexed: header=0, data rows 1..N, total row N+1

    items_table.setStyle(
        TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.2)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            # Data rows alternating
            ("ROWBACKGROUNDS", (0, 1), (-1, num_data_rows), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            # Total row
            ("BACKGROUND", (0, last_row), (-1, last_row), colors.Color(0.88, 0.88, 0.88)),
            ("LINEABOVE", (0, last_row), (-1, last_row), 0.75, colors.grey),
            # Alignment: numeric columns right-aligned
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),   # Qty
            ("ALIGN", (5, 0), (5, -1), "RIGHT"),   # Unit Price
            ("ALIGN", (8, 0), (8, -1), "RIGHT"),   # Line Total
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
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------------------
    # 5. Terms & Conditions
    # -------------------------------------------------------------------------
    if po.terms_and_conditions:
        story.append(Paragraph("Terms & Conditions", heading_style))
        story.append(Paragraph(po.terms_and_conditions, body_style))

    doc.build(story)
    return buf.getvalue()
