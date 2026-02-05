


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

    # -------------------------
    # STATIC DATA
    # -------------------------
    customer_name = "Nusrath Syed"
    address_line1 = "20-4-510-1 kota mitta, meclines road"
    address_line2 = "Near rehmatia masjid"
    city_state = "Nellore, Andhra Pradesh"
    pincode = "524001"
    phone = "9666215779"

    order_total = "398"
    awb = "7D124748548"

    # -------------------------
    # SHIP TO SECTION
    # -------------------------
    box_height = 95
    draw_box(c, margin, y - box_height, width - 2 * margin, box_height)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(20, y - 20, "Ship To")

    c.setFont("Helvetica", 10)

    ship_lines = [
        customer_name,
        address_line1,
        address_line2,
        city_state,
        pincode,
        phone,
    ]

    ty = y - 35
    for line in ship_lines:
        c.drawString(20, ty, line)
        ty -= 14

    y -= box_height + 10

    # -------------------------
    # ORDER DETAILS
    # -------------------------
    box_height = 110
    draw_box(c, margin, y - box_height, width - 2 * margin, box_height)

    left_lines = [
        "Dimensions: 21x31x2",
        "Payment: PREPAID",
        f"Order Total: ₹{order_total}",
        "Weight: 0.5 kg",
        "EWaybill No:",
        "Routing code: NA",
        "RTO Routing code: NA",
    ]

    ty = y - 20
    for line in left_lines:
        c.drawString(20, ty, line)
        ty -= 14

    c.drawRightString(width - 25, y - 20, "DTDC Surface")
    c.drawRightString(width - 25, y - 35, f"AWB: {awb}")

    barcode = code128.Code128(awb, barHeight=40)
    barcode.drawOn(c, width - 220, y - 90)

    y -= box_height + 10

    # -------------------------
    # FOOTER
    # -------------------------
    draw_box(c, margin, y - 50, width - 2 * margin, 50)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        20,
        y - 20,
        "All disputes are subject to Haryana Jurisdiction only.",
    )

    c.setFont("Helvetica", 9)
    c.drawString(
        20,
        y - 35,
        "This is an auto generated label and does not require any signature.",
    )

    c.save()


    buffer.seek(0)

    # -------------------------
    # SAVE FILE
    # -------------------------

    filename = "shipping_invoice_test.pdf"
    file_path = f"shipping/{filename}"

    saved_path = default_storage.save(
        file_path,
        ContentFile(buffer.read())
    )

    file_url = settings.MEDIA_URL + saved_path

    print("Uploaded to:", file_url)
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
