from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright, PdfMargins
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def generate_shipping_invoice(order):
    """
    Generates shipping invoice PDF using Playwright
    and saves it to configured Django storage (S3/MinIO/local).

    Returns: file path (string) to store in order.shipping_slip
    """

    # 1️⃣ Render HTML from Django template
    html_content = render_to_string(
        "shipping_invoice.html",
        {"order": order},
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

            margins: PdfMargins = {
                "top": "10mm",
                "bottom": "10mm",
                "left": "10mm",
                "right": "10mm",
            }

            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin=margins,
            )

            browser.close()

        # 4️⃣ Save to Django storage
        storage_path = f"shipping/invoice_{order.id}.pdf"

        with open(pdf_path, "rb") as f:
            saved_path = default_storage.save(
                storage_path,
                ContentFile(f.read()),
            )

    # 5️⃣ Return storage path
    return saved_path
