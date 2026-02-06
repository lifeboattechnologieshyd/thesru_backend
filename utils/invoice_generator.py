


import os
from io import BytesIO
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


# def generate_shipping_invoice(order):
#     """
#     Generates shipping invoice PDF and saves it to:
#     shipping/<order_number>.pdf
#     """
#
#     buffer = BytesIO()
#     p = canvas.Canvas(buffer, pagesize=A4)
#
#     width, height = A4
#     y = height - 40
#
#     store = order.store
#     address = order.address
#
#     # -------------------------
#     # STORE DETAILS
#     # -------------------------
#     p.setFont("Helvetica-Bold", 14)
#     p.drawString(40, y, store.name)
#     y -= 20
#
#     p.setFont("Helvetica", 10)
#     p.drawString(40, y, f"Address: {store.address}")
#     y -= 15
#     p.drawString(40, y, f"Phone: {store.mobile}")
#     y -= 15
#
#     if store.gst_number:
#         p.drawString(40, y, f"GST: {store.gst_number}")
#         y -= 20
#
#     # -------------------------
#     # INVOICE HEADER
#     # -------------------------
#     p.setFont("Helvetica-Bold", 12)
#     p.drawString(40, y, "SHIPPING INVOICE")
#     y -= 25
#
#     p.setFont("Helvetica", 10)
#     p.drawString(40, y, f"Order Number: {order.order_number}")
#     y -= 15
#     p.drawString(40, y, f"Order Date: {order.created_at.strftime('%d-%m-%Y')}")
#     y -= 25
#
#     # -------------------------
#     # CUSTOMER DETAILS
#     # -------------------------
#     p.setFont("Helvetica-Bold", 11)
#     p.drawString(40, y, "Shipping Address")
#     y -= 15
#
#     p.setFont("Helvetica", 10)
#     p.drawString(40, y, address.get("name", ""))
#     y -= 15
#     p.drawString(40, y, address.get("mobile", ""))
#     y -= 15
#     p.drawString(40, y, address.get("address", ""))
#     y -= 15
#     p.drawString(
#         40,
#         y,
#         f"{address.get('city', '')} - {address.get('pincode', '')}",
#     )
#     y -= 15
#     p.drawString(40, y, address.get("state", ""))
#     y -= 25
#
#     # -------------------------
#     # PAYMENT SUMMARY
#     # -------------------------
#     p.setFont("Helvetica-Bold", 11)
#     p.drawString(40, y, "Payment Summary")
#     y -= 15
#
#     p.setFont("Helvetica", 10)
#     p.drawString(40, y, f"MRP: ₹{order.mrp}")
#     y -= 15
#     p.drawString(40, y, f"Selling Price: ₹{order.selling_price}")
#     y -= 15
#     p.drawString(40, y, f"Coupon Discount: ₹{order.coupon_discount}")
#     y -= 15
#     p.drawString(40, y, f"Total Amount: ₹{order.amount}")
#     y -= 25
#
#     # -------------------------
#     # FOOTER
#     # -------------------------
#     p.setFont("Helvetica", 9)
#     p.drawString(40, 40, "This is a system generated invoice.")
#
#     p.showPage()
#     p.save()
#
#     buffer.seek(0)
#
#     # -------------------------
#     # SAVE FILE
#     # -------------------------
#
#     filename = f"{order.order_number}.pdf"
#     file_path = f"shipping/{filename}"
#
#     saved_path = default_storage.save(
#         file_path,
#         ContentFile(buffer.read())
#     )
#
#     file_url = settings.MEDIA_URL + saved_path
#
#     # Save to order
#     order.shipping_slip = saved_path
#     order.save(update_fields=["shipping_slip"])
#
#     return file_url




from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings


def draw_box(c, x, y, w, h):
    c.rect(x, y, w, h)


def generate_shipping_invoice():
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    margin = 15
    y = height - margin

    # =========================================================
    # SHIP TO
    # =========================================================
    box_height = 95
    draw_box(c, margin, y - box_height, width - 2 * margin, box_height)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(20, y - 20, "Ship To")

    c.setFont("Helvetica", 10)
    ship_lines = [
        "Nusrath Syed",
        "20-4-510-1 kota mitta, meclines road, near rehmatia masjid",
        "Nellore, Andhra Pradesh, India",
        "524001",
        "9666215779",
    ]

    ty = y - 38
    for line in ship_lines:
        c.drawString(20, ty, line)
        ty -= 14

    y -= box_height + 8

    # =========================================================
    # ORDER DETAILS + BARCODE
    # =========================================================
    box_height = 120
    draw_box(c, margin, y - box_height, width - 2 * margin, box_height)

    left_lines = [
        "Dimensions: 21x31x2",
        "Payment: PREPAID",
        "Order Total: ₹398",
        "Weight: 0.5 kg",
        "EWaybill No:",
        "Routing code: NA",
        "RTO Routing code: NA",
    ]

    ty = y - 22
    for line in left_lines:
        c.drawString(20, ty, line)
        ty -= 14

    c.drawRightString(width - 25, y - 22, "DTDC Surface")
    c.drawRightString(width - 25, y - 38, "AWB: 7D124748548")

    awb_barcode = code128.Code128(
        "7D124748548",
        barHeight=45,
        barWidth=1.2
    )
    awb_barcode.drawOn(c, width - 240, y - 100)

    y -= box_height + 8

    # =========================================================
    # SHIPPED BY
    # =========================================================
    box_height = 160
    draw_box(c, margin, y - box_height, width - 2 * margin, box_height)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(20, y - 22, "Shipped By (if undelivered, return to)")

    c.setFont("Helvetica", 10)
    shipped_lines = [
        "Ishu’s Store",
        "Ishu's Store 3rd floor, GMR & GS Complex",
        "Kishanpura, Opp: Police Head Quarters",
        "Hanamkonda",
        "Warangal, Telangana",
        "506001",
        "9182348571",
        "Customer Care: 1800-123-4567",
        "Customer Email: shiprocket@.com",
    ]

    ty = y - 42
    for line in shipped_lines:
        c.drawString(20, ty, line)
        ty -= 14

    c.drawRightString(width - 25, y - 22, "Order#: IS1128")

    order_barcode = code128.Code128(
        "IS1128",
        barHeight=45,
        barWidth=1.2
    )
    order_barcode.drawOn(c, width - 240, y - 105)

    c.drawRightString(width - 25, y - 120, "Invoice No: ISV00067")
    c.drawRightString(width - 25, y - 136, "Invoice Date: 28/01/2026")
    c.drawRightString(width - 25, y - 152, "Order Date: 24/01/2026")
    c.drawRightString(width - 25, y - 168, "GSTIN:")

    y -= box_height + 8

    # =========================================================
    # ITEM TABLE
    # =========================================================
    box_height = 85
    draw_box(c, margin, y - box_height, width - 2 * margin, box_height)

    headers = ["Item", "SKU", "Qty", "Price", "HSN", "Taxable Value", "Total"]
    x_positions = [20, 135, 265, 305, 360, 430, 525]

    c.setFont("Helvetica-Bold", 10)
    for i, h in enumerate(headers):
        c.drawString(x_positions[i], y - 22, h)

    c.setFont("Helvetica", 10)
    values = [
        "ZOYA NIQAB...",
        "4540979216...",
        "1",
        "₹299.00",
        "",
        "₹299.00",
        "₹299.00",
    ]

    for i, v in enumerate(values):
        c.drawString(x_positions[i], y - 42, v)

    c.drawString(20, y - 62, "Platform Fee: ₹0")
    c.drawString(20, y - 76, "Shipping Charges: ₹99")

    c.drawRightString(width - 25, y - 62, "Discount: ₹0")
    c.drawRightString(width - 25, y - 76, "Collectable Amount: ₹0")

    y -= box_height + 8

    # =========================================================
    # FOOTER
    # =========================================================
    box_height = 55
    draw_box(c, margin, y - box_height, width - 2 * margin, box_height)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        20,
        y - 22,
        "All disputes are subject to Haryana Jurisdiction only. Goods once sold will only be taken back or exchanged as per store's exchange and return policy",
    )

    c.setFont("Helvetica", 9)
    c.drawString(
        20,
        y - 40,
        "This is an auto generated label and does not require any signature.",
    )

    # =========================================================
    # SAVE & UPLOAD TO S3
    # =========================================================
    c.save()
    buffer.seek(0)

    filename = "shipping_invoice_static.pdf"
    file_path = f"shipping/{filename}"

    saved_path = default_storage.save(
        file_path,
        ContentFile(buffer.read())
    )

    file_url = settings.MEDIA_URL + saved_path
    return file_url
    # filename = f"{order.order_number}.pdf"
    # file_path = f"shipping/{filename}"
    #
    # saved_path = default_storage.save(
    #     file_path,
    #     ContentFile(buffer.read())
    # )
    #
    # file_url = settings.MEDIA_URL + saved_path
    #
    # order.shipping_slip = saved_path
    # order.save(update_fields=["shipping_slip"])
    #
    # return file_url
