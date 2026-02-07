from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings


def generate_shipping_invoice(order):
    """
    Generates shipping invoice PDF using Playwright
    and uploads it using Django default_storage (S3 / MinIO / local)

    Returns:
        file_url (string) → to be stored in order.shipping_slip
    """

    # 1️⃣ Render HTML
    html_content = render_to_string(
        "store/shipping_invoice.html",
        {
            "order": order,
            "address": order.address,
            "store": order.store,
            "items": order.items.select_related("product"),
        }
    )



    # 2️⃣ Create temp files
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "invoice.html"
        pdf_path = Path(tmpdir) / f"invoice_{order.id}.pdf"

        html_path.write_text(html_content, encoding="utf-8")

        # 3️⃣ Generate PDF using Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page()
            page.goto(f"file://{html_path}", wait_until="networkidle")

            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={
                    "top": "10mm",
                    "bottom": "10mm",
                    "left": "10mm",
                    "right": "10mm",
                },
            )

            browser.close()

        # 4️⃣ Upload exactly like FileUploadView
        storage_path = f"shipping/invoice_{order.id}.pdf"

        with open(pdf_path, "rb") as f:
            saved_path = default_storage.save(
                storage_path,
                ContentFile(f.read())
            )

        file_url = settings.MEDIA_URL + saved_path

    # 5️⃣ Return URL (store in DB)
    return file_url
