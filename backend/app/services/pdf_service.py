from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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

    # =========================================================
    # Helpers
    # =========================================================

    def fmt_money(value):
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return "0.00"

    def fmt_number(value):
        try:
            number = float(value)

            if number.is_integer():
                return f"{int(number):,}"

            return f"{number:,.2f}"

        except (TypeError, ValueError):
            return "0"

    def fit_size_keep_ratio(img_src, max_w, max_h):
        iw, ih = ImageReader(img_src).getSize()

        scale = min(
            max_w / float(iw),
            max_h / float(ih)
        )

        return (
            iw * scale,
            ih * scale
        )

    # =========================================================
    # Document
    # =========================================================

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=70 * mm,
    )

    w = doc.width

    # =========================================================
    # Colors
    # =========================================================

    brand = colors.HexColor("#009be5")
    brand_dark = colors.HexColor("#146e98")
    text = colors.HexColor("#2f3b48")
    muted = colors.HexColor("#5b6572")
    border = colors.HexColor("#d8e0e8")
    header_bg = colors.HexColor("#eef7fc")
    summary_bg = colors.HexColor("#eef2f8")

    # =========================================================
    # Styles
    # =========================================================

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15.5,
        leading=16.5,
        textColor=brand_dark,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    )

    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.4,
        leading=10.0,
        textColor=muted,
        alignment=TA_LEFT,
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
        alignment=TA_LEFT,
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
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=4,
    )

    block_text_style = ParagraphStyle(
        "BlockText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.0,
        leading=9.6,
        textColor=text,
        alignment=TA_LEFT,
        splitLongWords=True,
    )

    inv_heading_right_style = ParagraphStyle(
        "InvHeadingRight",
        parent=block_heading_style,
        alignment=TA_RIGHT,
    )

    inv_text_right_style = ParagraphStyle(
        "InvTextRight",
        parent=block_text_style,
        fontSize=7.8,
        leading=9.3,
        alignment=TA_RIGHT,
    )

    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.3,
        leading=8.6,
        textColor=text,
        alignment=TA_LEFT,
        splitLongWords=True,
    )

    cell_center_style = ParagraphStyle(
        "CellCenter",
        parent=cell_style,
        alignment=TA_CENTER,
    )

    cell_right_style = ParagraphStyle(
        "CellRight",
        parent=cell_style,
        alignment=TA_RIGHT,
    )

    # =========================================================
    # Elements
    # =========================================================

    elements = []

    # =========================================================
    # HEADER
    # =========================================================

    seller_meta = (
        f"{data['seller_address']}<br/>"
        f"<b>NTN/CNIC: {data['seller_ntn']}</b>"
    )

    if data.get("seller_strn"):
        seller_meta += (
            f"<br/><b>STRN: {data['seller_strn']}</b>"
        )

    seller_meta += (
        f"<br/><b>Province: {data['province']}</b>"
    )

    left_header = Table(
        [
            [
                Paragraph(
                    data["seller_name"],
                    title_style
                )
            ],
            [
                Paragraph(
                    seller_meta,
                    meta_style
                )
            ],
        ],
        colWidths=[w * 0.78],
    )

    left_header.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),

            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),

            ("BOTTOMPADDING", (0, 0), (0, 0), 2.5),
        ])
    )

    qr_w, qr_h = fit_size_keep_ratio(
        data["qr"],
        max_w=58,
        max_h=58,
    )

    qr_img = Image(
        data["qr"],
        width=qr_w,
        height=qr_h,
    )

    header = Table(
        [
            [
                left_header,
                qr_img,
            ]
        ],
        colWidths=[
            w * 0.78,
            w * 0.22,
        ],
    )

    header.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            # Seller side
            ("ALIGN", (0, 0), (0, 0), "LEFT"),

            # QR side
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),

            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    elements.append(header)
    elements.append(Spacer(1, 10))

    # =========================================================
    # INVOICE TITLE
    # =========================================================

    heading_tbl = Table(
        [
            [
                Paragraph(
                    "SALES TAX INVOICE",
                    invoice_heading_style
                )
            ]
        ],
        colWidths=[w],
    )

    heading_tbl.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    elements.append(heading_tbl)
    elements.append(Spacer(1, 5))

    # =========================================================
    # TITLE LINE
    # =========================================================

    line_tbl = Table(
        [[""]],
        colWidths=[w],
        rowHeights=[1.6],
    )

    line_tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), brand),

            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    elements.append(line_tbl)
    elements.append(Spacer(1, 14))

    # =========================================================
    # BUYER + INVOICE SUMMARY
    # =========================================================

    buyer_text = (
        f"<b>NAME:</b> {data['buyer_name']}<br/>"
        f"<b>ADDRESS:</b> {data['buyer_address']}<br/>"
        f"<b>NTN/CNIC:</b> {data['buyer_ntn']}<br/>"
    )

    if data.get("buyer_strn"):
        buyer_text += (
            f"<b>STRN:</b> {data['buyer_strn']}<br/>"
        )

    inv_text = (
        f"<b>Inv #:</b>&nbsp;{data['invoice_no']}<br/>"
        f"<b>Date:</b> {data['date']}<br/>"
        f"<b>Sale Type:</b> {data['sale_type']}"
    )

    buyer_block = Table(
        [
            [
                Paragraph(
                    "BUYER DETAIL",
                    block_heading_style
                )
            ],
            [
                Paragraph(
                    buyer_text,
                    block_text_style
                )
            ],
        ],
        colWidths=[w * 0.63],
    )

    buyer_block.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),

            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    inv_block = Table(
        [
            [
                Paragraph(
                    "INVOICE SUMMARY",
                    inv_heading_right_style
                )
            ],
            [
                Paragraph(
                    inv_text,
                    inv_text_right_style
                )
            ],
        ],
        colWidths=[w * 0.37],
    )

    inv_block.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),

            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    info = Table(
        [
            [
                buyer_block,
                inv_block,
            ]
        ],
        colWidths=[
            w * 0.63,
            w * 0.37,
        ],
    )

    info.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),

            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    elements.append(info)
    elements.append(Spacer(1, 24))

    # =========================================================
    # ITEMS TABLE
    # =========================================================

    table_data = [
        [
            "HS Code",
            "Description",
            "Sale Type",
            "UOM",
            "Qty",
            "Rate",
            "S.T Rate",
            "SRO",
            "SRO Item",
            "Sales Value",
        ]
    ]

    for item in data["items"]:

        table_data.append([
            Paragraph(
                str(item.get("hs_code", "")),
                cell_style
            ),

            Paragraph(
                str(item.get("description", "")),
                cell_style
            ),

            Paragraph(
                str(item.get("sale_type", "")),
                cell_style
            ),

            Paragraph(
                str(item.get("uom", "")),
                cell_center_style
            ),

            Paragraph(
                fmt_number(item.get("quantity", 0)),
                cell_right_style
            ),

            Paragraph(
                fmt_money(item.get("item_rate", 0)),
                cell_right_style
            ),

            Paragraph(
                str(item.get("rate", "")),
                cell_right_style
            ),

            Paragraph(
                str(item.get("sro", "")),
                cell_style
            ),

            Paragraph(
                str(item.get("sro_item", "")),
                cell_style
            ),

            Paragraph(
                fmt_money(item.get("value_excl", 0)),
                cell_right_style
            ),
        ])

    # =========================================================
    # TABLE WIDTHS
    #
    # Total = 100% of available width
    # =========================================================

    col_widths = [
        w * 0.09,   # HS Code
        w * 0.17,   # Description
        w * 0.17,   # Sale Type
        w * 0.06,   # UOM
        w * 0.06,   # Qty
        w * 0.08,   # Rate
        w * 0.08,   # S.T Rate
        w * 0.07,   # SRO
        w * 0.08,   # SRO Item
        w * 0.14,   # Sales Value
    ]

    items = Table(
        table_data,
        repeatRows=1,
        colWidths=col_widths,
        hAlign="LEFT",
    )

    items.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef7fc")),
        ("TEXTCOLOR", (0, 0), (-1, 0), brand_dark),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.0),

        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 7.8),

        # Outer border
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#aeb8c2")),

        # Vertical borders
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c8d0d8")),

        # Header bottom border
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, brand),

        # Alignment
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (1, 0), (2, -1), "LEFT"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("ALIGN", (4, 0), (4, -1), "CENTER"),

        # Rate
        ("ALIGN", (5, 0), (5, 0), "CENTER"),
        ("ALIGN", (5, 1), (5, -1), "RIGHT"),

        # ST Rate
        ("ALIGN", (6, 0), (6, 0), "CENTER"),
        ("ALIGN", (6, 1), (6, -1), "RIGHT"),

        # SRO
        ("ALIGN", (7, 0), (8, -1), "CENTER"),

        # Sales Value
        ("ALIGN", (9, 0), (9, -1), "RIGHT"),

        # Vertical alignment
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Padding   
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(items)
    elements.append(Spacer(1, 10))
    # =========================================================
    # SUMMARY
    # =========================================================
    summary_rows = []
    if float(data.get("sales_tax", 0)) > 0:
        summary_rows.append([
            "Sales Tax",
            fmt_money(data["sales_tax"]),
        ])

    if float(data.get("further_tax", 0)) > 0:
        summary_rows.append([
            "Further Tax",
            fmt_money(data["further_tax"]),
        ])

    if float(data.get("extra_tax", 0)) > 0:
        summary_rows.append([
            "Extra Tax",
            fmt_money(data["extra_tax"]),
        ])

    if float(data.get("fed", 0)) > 0:
        summary_rows.append([
            "FED",
            fmt_money(data["fed"]),
        ])

    if float(data.get("tax236H", 0)) > 0:

        rates = data.get("tax236HRates", [])

        if rates:
            rate_text = ", ".join(
                f"{r:g}%"
                for r in rates
            )

            label = f"236H Tax ({rate_text})"

        else:
            label = "236H Tax"

        summary_rows.append([
            label,
            fmt_money(data["tax236H"]),
        ])

    if float(data.get("discount", 0)) > 0:
        summary_rows.append([
            "Discount",
            f"-{fmt_money(data['discount'])}",
        ])

    if float(data.get("retail_price", 0)) > 0:
        summary_rows.append([
            "Retail Price",
            fmt_money(data["retail_price"]),
        ])

    if float(data.get("st_wh", 0)) > 0:
        summary_rows.append([
            "Sales Tax WH",
            f"-{fmt_money(data['st_wh'])}",
        ])

    # Grand Total
    summary_rows.append([
        "Grand Total",
        f"Rs. {fmt_money(data['grand_total'])}",
    ])

    summary_tbl = Table(
        summary_rows,
        colWidths=[
            w * 0.22,
            w * 0.16,
        ],
        hAlign="RIGHT",
    )

    summary_style = [

        # Background
        ("BACKGROUND", (0, 0), (-1, -1), summary_bg),

        # Alignment
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),

        # Normal rows
        ("FONTSIZE", (0, 0), (-1, -2), 8.2),

        # Grand total
        ("FONTSIZE", (0, -1), (-1, -1), 10.0),
        ("TEXTCOLOR", (0, -1), (-1, -1), brand_dark),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),

        # Grand total separator
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, brand),

        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

        # Vertical
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    try:
        summary_tbl.setStyle(
            TableStyle(
                summary_style + [
                    (
                        "ROUNDEDCORNERS",
                        (0, 0),
                        (-1, -1),
                        6,
                    )
                ]
            )
        )
    except Exception:
        summary_tbl.setStyle(
            TableStyle(summary_style)
        )

    # Summary occupies right side
    summary_wrap = Table(
        [
            [
                "",
                summary_tbl,
            ]
        ],
        colWidths=[
            w * 0.60,
            w * 0.40,
        ],
    )

    summary_wrap.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),

            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    elements.append(
        KeepTogether(summary_wrap)
    )

    # =========================================================
    # FOOTER
    # =========================================================

    def draw_footer(canvas, _doc):

        canvas.saveState()

        page_w, _ = A4

        logo_w, logo_h = fit_size_keep_ratio(
            data["logo"],
            max_w=56 * mm,
            max_h=15 * mm,
        )

        logo_x = (
            page_w - logo_w
        ) / 2

        logo_y = 55 * mm

        canvas.drawImage(
            ImageReader(data["logo"]),
            logo_x,
            logo_y,
            width=logo_w,
            height=logo_h,
            mask="auto",
        )

        canvas.setFont(
            "Helvetica",
            8.2
        )

        canvas.setFillColor(
            colors.HexColor("#6b7280")
        )

        canvas.drawCentredString(
            page_w / 2,
            50 * mm,
            "System Generated - FBR Digital Invoicing Compliant",
        )

        canvas.restoreState()

    # =========================================================
    # BUILD PDF
    # =========================================================

    doc.build(
        elements,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )

    buffer.seek(0)

    pdf = buffer.getvalue()

    buffer.close()

    return pdf