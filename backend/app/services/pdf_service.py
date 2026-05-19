from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)

def generate_invoice_pdf_rl(data: dict) -> bytes:
    def fmt_money(v):
        try:
            return f"{float(v):,.2f}"
        except Exception:
            return str(v)

    def fit_size_keep_ratio(img_src, max_w, max_h):
        iw, ih = ImageReader(img_src).getSize()
        scale = min(max_w / float(iw), max_h / float(ih))
        return iw * scale, ih * scale

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=70 * mm,  # keeps footer print-safe
    )

    w = doc.width
    brand = colors.HexColor("#009be5")
    brand_dark = colors.HexColor("#146e98")
    text = colors.HexColor("#2f3b48")
    muted = colors.HexColor("#5b6572")
    styles = getSampleStyleSheet()

    # Styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15.5,
        leading=16.5,
        textColor=brand_dark,
        spaceBefore=0,
        spaceAfter=0,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=8.4,
        leading=10.0,
        textColor=muted,
        spaceBefore=0,
        spaceAfter=0,
    )
    invoice_heading_style = ParagraphStyle(
        "InvoiceHeading",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11.5,
        leading=13.0,
        textColor=brand,
        leftIndent=0,
        firstLineIndent=0,
        spaceBefore=0,
        spaceAfter=0,
    )
    block_heading_style = ParagraphStyle(
        "BlockHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.0,
        leading=10.2,
        textColor=brand_dark,
        spaceBefore=0,
        spaceAfter=4,
    )
    block_text_style = ParagraphStyle(
        "BlockText",
        parent=styles["Normal"],
        fontSize=8.0,
        leading=9.6,
        textColor=text,
        splitLongWords=True,
    )
    # Right-aligned details for invoice number/date/sale type
    inv_text_right_style = ParagraphStyle(
        "InvTextRight",
        parent=block_text_style,
        fontSize=7.8,
        leading=9.3,
        alignment=TA_RIGHT,
    )
    inv_heading_right_style = ParagraphStyle(
        "InvHeadingRight",
        parent=block_heading_style,
        alignment=TA_RIGHT,
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontSize=8.0,
        leading=9.3,
        textColor=text,
        splitLongWords=True,
    )
    uom_style = ParagraphStyle(
        "UOMCell",
        parent=cell_style,
        alignment=1,  # center
    )

    elements = []

    # Header
    left_header = Table(
        [
            [Paragraph(data["seller_name"], title_style)],
            [Paragraph(
                f"{data['seller_address']}<br/>"
                f"NTN/CNIC: {data['seller_ntn']} | Province: {data['province']}",
                meta_style,
            )],
        ],
        colWidths=[w * 0.78],
    )
    left_header.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2.5),
    ]))

    qr_w, qr_h = fit_size_keep_ratio(data["qr"], max_w=58, max_h=58)
    qr_img = Image(data["qr"], width=qr_w, height=qr_h)

    header = Table([[left_header, qr_img]], colWidths=[w * 0.78, w * 0.22])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header)

    elements.append(Spacer(1, 10))

    heading_tbl = Table([[Paragraph("SALES TAX INVOICE", invoice_heading_style)]], colWidths=[w])
    heading_tbl.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(heading_tbl)
    elements.append(Spacer(1, 5))

    line_tbl = Table([[""]], colWidths=[w], rowHeights=[1.6])
    line_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), brand),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(line_tbl)
    elements.append(Spacer(1, 14))

    # Buyer + Invoice Summary
    buyer_text = (
        f"<b>NAME:</b> {data['buyer_name']}<br/>"
        f"<b>ADDRESS:</b> {data['buyer_address']}<br/>"
        f"<b>NTN/CNIC:</b> {data['buyer_ntn']}"
    )
    inv_text = (
        f"<b>Inv #:</b>&nbsp;{data['invoice_no']}<br/>"
        f"<b>Date:</b> {data['date']}<br/>"
        f"<b>Sale Type:</b> {data['sale_type']}"
    )

    buyer_block = Table(
        [[Paragraph("BUYER DETAIL", block_heading_style)],
         [Paragraph(buyer_text, block_text_style)]],
        colWidths=[w * 0.63],
    )
    buyer_block.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    inv_block = Table(
        [[Paragraph("INVOICE SUMMARY", inv_heading_right_style)],
         [Paragraph(inv_text, inv_text_right_style)]],
        colWidths=[w * 0.37],
    )
    inv_block.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    info = Table([[buyer_block, inv_block]], colWidths=[w * 0.63, w * 0.37])
    info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),  # right column anchored to boundary
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info)

    # Extra space before items table
    elements.append(Spacer(1, 18))

    # Items table
    table_data = [[
        "HS Code", "Description", "Sale Type", "Qty", "UOM", "Rate", "SRO", "SRO Item", "Sales Value"
    ]]

    for item in data["items"]:
        table_data.append([
            Paragraph(str(item.get("hs_code", "")), cell_style),
            Paragraph(str(item.get("description", "")), cell_style),
            Paragraph(str(item.get("sale_type", "")), cell_style),
            fmt_money(item.get("quantity", 0)),
            Paragraph(str(item.get("uom", "")), uom_style),
            str(item.get("rate", "")),
            Paragraph(str(item.get("sro", "")), cell_style),
            Paragraph(str(item.get("sro_item", "")), cell_style),
            fmt_money(item.get("value_excl", 0)),
        ])

    col_widths = [w * 0.10, w * 0.12, w * 0.27, w * 0.09, w * 0.09, w * 0.06, w * 0.07, w * 0.08, w * 0.12]
    items = Table(table_data, repeatRows=1, colWidths=col_widths)

    items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef7fc")),
        ("TEXTCOLOR", (0, 0), (-1, 0), brand_dark),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.2),
        ("FONTSIZE", (0, 1), (-1, -1), 8.0),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, brand),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#d8e0e8")),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("ALIGN", (4, 0), (4, -1), "CENTER"),
        ("ALIGN", (5, 1), (5, -1), "RIGHT"),
        ("ALIGN", (8, 1), (8, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(items)
    elements.append(Spacer(1, 10))

    # Summary
    summary_rows = [
        ["Sales Tax", fmt_money(data["sales_tax"])],
        ["Further Tax", fmt_money(data["further_tax"])],
        ["Extra Tax", fmt_money(data["extra_tax"])],
        ["FED", fmt_money(data["fed"])],
        ["Discount", f"-{fmt_money(data['discount'])}"],
        ["Retail Price", fmt_money(data["retail_price"])],
        ["Sales Tax WH", f"-{fmt_money(data['st_wh'])}"],
        ["Grand Total", f"Rs. {fmt_money(data['grand_total'])}"],
    ]

    summary_tbl = Table(summary_rows, colWidths=[w * 0.26, w * 0.21])
    summary_style = [
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef2f8")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -2), 8.2),
        ("FONTSIZE", (0, -1), (-1, -1), 10.0),
        ("TEXTCOLOR", (0, -1), (-1, -1), brand_dark),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, brand),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    try:
        summary_tbl.setStyle(TableStyle(summary_style + [("ROUNDEDCORNERS", (0, 0), (-1, -1), 6)]))
    except Exception:
        summary_tbl.setStyle(TableStyle(summary_style))

    summary_wrap = Table([["", summary_tbl]], colWidths=[w * 0.53, w * 0.47])
    summary_wrap.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(KeepTogether(summary_wrap))

    # Footer
    def draw_footer(canvas, _doc):
        canvas.saveState()
        page_w, _ = A4

        logo_w, logo_h = fit_size_keep_ratio(data["logo"], max_w=56 * mm, max_h=15 * mm)
        logo_x = (page_w - logo_w) / 2
        logo_y = 55 * mm

        canvas.drawImage(
            ImageReader(data["logo"]),
            logo_x,
            logo_y,
            width=logo_w,
            height=logo_h,
            mask="auto",
        )

        canvas.setFont("Helvetica", 8.2)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawCentredString(page_w / 2, 50 * mm, "System Generated - FBR Digital Invoicing Compliant")
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)

    buffer.seek(0)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf