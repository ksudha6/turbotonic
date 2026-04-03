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
    PageBreak,
)

from src.domain.invoice import Invoice, InvoiceStatus
from src.domain.purchase_order import PurchaseOrder
from src.domain.reference_labels import currency_label, payment_terms_label

# Page margins — match po_pdf.py
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


def _build_invoice_story(
    invoice: Invoice,
    po: PurchaseOrder,
    vendor_name: str,
    vendor_country: str,
    styles,
) -> list:
    """Build the ReportLab story elements for one invoice page."""
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
    # 1. Header
    # -------------------------------------------------------------------------
    story.append(Paragraph("INVOICE", title_style))

    inv_header_data = [
        [
            Paragraph(f"<b>Invoice Number:</b> {invoice.invoice_number}", body_style),
            Paragraph(f"<b>Status:</b> {invoice.status.value}", body_style),
        ],
        [
            Paragraph(f"<b>PO Number:</b> {po.po_number}", body_style),
            Paragraph(f"<b>Created:</b> {_date_str(invoice.created_at)}", body_style),
        ],
        [
            Paragraph(
                f"<b>Payment Terms:</b> {invoice.payment_terms} - {payment_terms_label(invoice.payment_terms)}",
                body_style,
            ),
            Paragraph(
                f"<b>Currency:</b> {invoice.currency} - {currency_label(invoice.currency)}",
                body_style,
            ),
        ],
    ]
    inv_header_table = Table(inv_header_data, colWidths=[_PAGE_WIDTH / 2, _PAGE_WIDTH / 2])
    inv_header_table.setStyle(
        TableStyle([
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(inv_header_table)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------------------
    # 2. Parties
    # -------------------------------------------------------------------------
    story.append(Paragraph("Parties", heading_style))

    buyer_content = [
        Paragraph("<b>Buyer</b>", cell_bold),
        Paragraph(po.buyer_name, cell_style),
    ]
    vendor_content = [
        Paragraph("<b>Vendor</b>", cell_bold),
        Paragraph(vendor_name, cell_style),
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
    # 3. Line Items Table
    # -------------------------------------------------------------------------
    story.append(Paragraph("Line Items", heading_style))

    # Column widths: #, Part Number, Description, Qty, UoM, Unit Price, Line Total
    col_widths = [
        0.30 * inch,   # #
        0.90 * inch,   # Part Number
        2.60 * inch,   # Description
        0.45 * inch,   # Qty
        0.45 * inch,   # UoM
        0.90 * inch,   # Unit Price
        0.90 * inch,   # Line Total
    ]

    header_row = [
        Paragraph("<b>#</b>", cell_bold),
        Paragraph("<b>Part Number</b>", cell_bold),
        Paragraph("<b>Description</b>", cell_bold),
        Paragraph("<b>Qty</b>", cell_bold),
        Paragraph("<b>UoM</b>", cell_bold),
        Paragraph("<b>Unit Price</b>", cell_bold),
        Paragraph("<b>Line Total</b>", cell_bold),
    ]

    line_rows = []
    for idx, item in enumerate(invoice.line_items, start=1):
        line_total = item.quantity * item.unit_price
        line_rows.append([
            Paragraph(str(idx), cell_style),
            Paragraph(item.part_number, cell_style),
            Paragraph(item.description, cell_style),
            Paragraph(str(item.quantity), cell_style),
            Paragraph(item.uom, cell_style),
            Paragraph(f"{_money(item.unit_price)} {invoice.currency}", cell_style),
            Paragraph(f"{_money(line_total)} {invoice.currency}", cell_style),
        ])

    num_data_rows = len(line_rows)
    last_row = num_data_rows + 1  # 0-indexed: header=0, data rows 1..N, subtotal row N+1

    subtotal_row = [
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("", cell_style),
        Paragraph("<b>Subtotal</b>", cell_bold),
        Paragraph(f"<b>{_money(invoice.subtotal)} {invoice.currency}</b>", cell_bold),
    ]

    items_table_data = [header_row] + line_rows + [subtotal_row]

    items_table = Table(items_table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(
        TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.85, 0.85)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            # Data rows alternating
            ("ROWBACKGROUNDS", (0, 1), (-1, num_data_rows), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            # Subtotal row
            ("BACKGROUND", (0, last_row), (-1, last_row), colors.Color(0.88, 0.88, 0.88)),
            ("LINEABOVE", (0, last_row), (-1, last_row), 0.75, colors.grey),
            # Alignment: numeric columns right-aligned
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),   # Qty
            ("ALIGN", (5, 0), (5, -1), "RIGHT"),   # Unit Price
            ("ALIGN", (6, 0), (6, -1), "RIGHT"),   # Line Total
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

    # -------------------------------------------------------------------------
    # 4. Dispute Reason (only for DISPUTED invoices)
    # -------------------------------------------------------------------------
    if invoice.status is InvoiceStatus.DISPUTED and invoice.dispute_reason:
        story.append(Spacer(1, 14))
        story.append(Paragraph("Dispute Reason", heading_style))
        story.append(Paragraph(invoice.dispute_reason, body_style))

    return story


def generate_invoice_pdf(
    invoice: Invoice,
    po: PurchaseOrder,
    vendor_name: str,
    vendor_country: str,
) -> bytes:
    """Build a PDF for the given Invoice and return it as raw bytes."""
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
    story = _build_invoice_story(invoice, po, vendor_name, vendor_country, styles)

    doc.build(story)
    return buf.getvalue()


def generate_bulk_invoice_pdf(
    invoices_with_context: list[tuple[Invoice, PurchaseOrder, str, str]],
) -> bytes:
    """Build a single PDF with one invoice per page and return it as raw bytes."""
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
    story = []

    for idx, (invoice, po, vendor_name, vendor_country) in enumerate(invoices_with_context):
        if idx > 0:
            story.append(PageBreak())
        story.extend(_build_invoice_story(invoice, po, vendor_name, vendor_country, styles))

    doc.build(story)
    return buf.getvalue()
