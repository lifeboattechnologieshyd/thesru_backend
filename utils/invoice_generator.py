


import os
from io import BytesIO
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def generate_shipping_invoice(order):
    """
    Generates shipping invoice PDF and saves it to:
    shipping/<order_number>.pdf
    """

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 40

    store = order.store
    address = order.address

    # -------------------------
    # STORE DETAILS
    # -------------------------
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, store.name)
    y -= 20

    p.setFont("Helvetica", 10)
    p.drawString(40, y, f"Address: {store.address}")
    y -= 15
    p.drawString(40, y, f"Phone: {store.mobile}")
    y -= 15

    if store.gst_number:
        p.drawString(40, y, f"GST: {store.gst_number}")
        y -= 20

    # -------------------------
    # INVOICE HEADER
    # -------------------------
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "SHIPPING INVOICE")
    y -= 25

    p.setFont("Helvetica", 10)
    p.drawString(40, y, f"Order Number: {order.order_number}")
    y -= 15
    p.drawString(40, y, f"Order Date: {order.created_at.strftime('%d-%m-%Y')}")
    y -= 25

    # -------------------------
    # CUSTOMER DETAILS
    # -------------------------
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y, "Shipping Address")
    y -= 15

    p.setFont("Helvetica", 10)
    p.drawString(40, y, address.get("name", ""))
    y -= 15
    p.drawString(40, y, address.get("mobile", ""))
    y -= 15
    p.drawString(40, y, address.get("address", ""))
    y -= 15
    p.drawString(
        40,
        y,
        f"{address.get('city', '')} - {address.get('pincode', '')}",
    )
    y -= 15
    p.drawString(40, y, address.get("state", ""))
    y -= 25

    # -------------------------
    # PAYMENT SUMMARY
    # -------------------------
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y, "Payment Summary")
    y -= 15

    p.setFont("Helvetica", 10)
    p.drawString(40, y, f"MRP: ₹{order.mrp}")
    y -= 15
    p.drawString(40, y, f"Selling Price: ₹{order.selling_price}")
    y -= 15
    p.drawString(40, y, f"Coupon Discount: ₹{order.coupon_discount}")
    y -= 15
    p.drawString(40, y, f"Total Amount: ₹{order.amount}")
    y -= 25

    # -------------------------
    # FOOTER
    # -------------------------
    p.setFont("Helvetica", 9)
    p.drawString(40, 40, "This is a system generated invoice.")

    p.showPage()
    p.save()

    buffer.seek(0)

    # -------------------------
    # SAVE FILE
    # -------------------------
    file_path = f"shipping/{order.order_number}.pdf"

    saved_path = default_storage.save(
        file_path,
        ContentFile(buffer.read())
    )

    return saved_path
