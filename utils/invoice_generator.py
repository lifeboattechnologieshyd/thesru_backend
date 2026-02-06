from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from weasyprint import HTML


def generate_shipping_invoice(order):
    context = {
        "order": order,
    }

    # Render HTML template
    html_string = render_to_string(
        "shipping_invoice.html",
        context
    )

    # Generate PDF
    pdf_bytes = HTML(
        string=html_string,
        base_url=settings.BASE_DIR
    ).write_pdf()

    # Save PDF
    file_path = f"shipping/shipping_invoice_{order.id}.pdf"

    saved_path = default_storage.save(
        file_path,
        ContentFile(pdf_bytes)
    )

    return saved_path
