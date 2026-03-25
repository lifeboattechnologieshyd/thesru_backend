from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings

from utils.storage import StoreS3Storage


#
# def generate_shipping_invoice(order):
#     """
#     Generates shipping invoice PDF using Playwright
#     and uploads it using Django default_storage (S3 / MinIO / local)
#
#     Returns:
#         file_url (string) → to be stored in order.shipping_slip
#     """
#
#     # 1️⃣ Render HTML
#     html_content = render_to_string(
#         "store/shipping_invoice.html",
#         {
#             "order": order,
#             "address": order.address,
#             "store": order.store,
#             "items": order.items.select_related("product"),
#         }
#     )
#
#
#
#     # 2️⃣ Create temp files
#     with tempfile.TemporaryDirectory() as tmpdir:
#         html_path = Path(tmpdir) / "invoice.html"
#         pdf_path = Path(tmpdir) / f"invoice_{order.id}.pdf"
#
#         html_path.write_text(html_content, encoding="utf-8")
#
#         # 3️⃣ Generate PDF using Playwright
#         with sync_playwright() as p:
#             browser = p.chromium.launch(
#                 args=["--no-sandbox", "--disable-dev-shm-usage"]
#             )
#             page = browser.new_page()
#             page.goto(f"file://{html_path}", wait_until="networkidle")
#
#             page.pdf(
#                 path=str(pdf_path),
#                 format="A4",
#                 print_background=True,
#                 margin={
#                     "top": "10mm",
#                     "bottom": "10mm",
#                     "left": "10mm",
#                     "right": "10mm",
#                 },
#             )
#
#             browser.close()
#
#         # 4️⃣ Upload exactly like FileUploadView
#         storage_path = f"shipping/invoice_{order.id}.pdf"
#
#         with open(pdf_path, "rb") as f:
#             saved_path = default_storage.save(
#                 storage_path,
#                 ContentFile(f.read())
#             )
#
#         file_url = settings.MEDIA_URL + saved_path
#
#     # 5️⃣ Return URL (store in DB)
#     return file_url
# def generate_shipping_invoice(order):
#     """
#     Generates shipping invoice PDF using Playwright
#     and uploads it using Django default_storage (S3 / MinIO / local)
#     """
#
#     # ✅ PREPARE ITEMS (IMPORTANT)
#     items = []
#     for item in order.items.select_related("product"):
#         items.append({
#             "name": item.product.name,
#             "qty": item.qty,
#             "unit_price": item.selling_price,
#             "total_price": item.selling_price * item.qty,
#         })
#
#     # 1️⃣ Render HTML
#     html_content = render_to_string(
#         "store/shipping_invoice.html",
#         {
#             "order": order,
#             "address": order.address,
#             "store": order.store,
#             "items": items,
#         }
#     )
#
#     # 2️⃣ Create temp files
#     with tempfile.TemporaryDirectory() as tmpdir:
#         html_path = Path(tmpdir) / "invoice.html"
#         pdf_path = Path(tmpdir) / f"invoice_{order.id}.pdf"
#
#         html_path.write_text(html_content, encoding="utf-8")
#
#         # 3️⃣ Generate PDF
#         with sync_playwright() as p:
#             browser = p.chromium.launch(
#                 args=["--no-sandbox", "--disable-dev-shm-usage"]
#             )
#             page = browser.new_page()
#             page.goto(f"file://{html_path}", wait_until="networkidle")
#
#             page.pdf(
#                 path=str(pdf_path),
#                 format="A4",
#                 print_background=True,
#                 margin={
#                     "top": "10mm",
#                     "bottom": "10mm",
#                     "left": "10mm",
#                     "right": "10mm",
#                 },
#             )
#
#             browser.close()
#
#         # 4️⃣ Upload
#         storage_path = f"shipping/invoice_{order.id}.pdf"
#
#         with open(pdf_path, "rb") as f:
#             saved_path = default_storage.save(
#                 storage_path,
#                 ContentFile(f.read())
#             )
#
#         file_url = settings.MEDIA_URL + saved_path
#
#     return file_url

#
# def generate_shipping_invoice(order):
#     """
#     Generates shipping invoice PDF using Playwright
#     and uploads it using Django default_storage (S3 / MinIO / local)
#     """
#
#     #  PREPARE ITEMS (IMPORTANT)
#     # items = []
#     # for item in order.items.select_related("product"):
#     #     items.append({
#     #         "name": item.product.name,
#     #         "qty": item.qty,
#     #         "unit_price": item.selling_price,
#     #         "total_price": item.selling_price * item.qty,
#     #     })
#     from collections import defaultdict
#
#     items_map = defaultdict(lambda: {
#         "name": "",
#         "qty": 0,
#         "unit_price": 0,
#         "total_price": 0,
#     })
#
#     for item in order.items.select_related("product"):
#         key = item.product.id
#
#         items_map[key]["name"] = item.product.name
#         items_map[key]["unit_price"] = item.selling_price
#         items_map[key]["qty"] += item.qty
#         items_map[key]["total_price"] += item.selling_price * item.qty
#
#     # convert to list
#     items = list(items_map.values())
#
#     #  TEMPLATE SELECTION (NEW)
#     template_name = "store/shipping_invoice.html"
#     is_thermal = False
#
#     if order.store and order.store.product_code == "SRU":
#         template_name = "store/shipping_invoice_sru.html"
#         is_thermal = True
#
#     # Render HTML
#     html_content = render_to_string(
#         template_name,
#         {
#             "order": order,
#             "address": order.address,
#             "store": order.store,
#             "items": items,
#         }
#     )
#
#     #  Create temp files
#     with tempfile.TemporaryDirectory() as tmpdir:
#         html_path = Path(tmpdir) / "invoice.html"
#         pdf_path = Path(tmpdir) / f"invoice_{order.id}.pdf"
#
#         html_path.write_text(html_content, encoding="utf-8")
#
#         #  Generate PDF
#         with sync_playwright() as p:
#             browser = p.chromium.launch(
#                 args=["--no-sandbox", "--disable-dev-shm-usage"]
#             )
#             page = browser.new_page()
#             page.goto(f"file://{html_path}", wait_until="networkidle")
#
#             #  PDF CONFIG (NEW)
#             if is_thermal:
#                 page.pdf(
#                     path=str(pdf_path),
#                     width="6in",
#                     height="4in",
#                     print_background=True,
#                 )
#             else:
#                 page.pdf(
#                     path=str(pdf_path),
#                     format="A4",
#                     print_background=True,
#                     margin={
#                         "top": "10mm",
#                         "bottom": "10mm",
#                         "left": "10mm",
#                         "right": "10mm",
#                     },
#                 )
#
#             browser.close()
#
#         #  Upload
#         storage_path = f"shipping/invoice_{order.id}.pdf"
#
#         with open(pdf_path, "rb") as f:
#             saved_path = default_storage.save(
#                 storage_path,
#                 ContentFile(f.read())
#             )
#
#         file_url = settings.MEDIA_URL + saved_path
#
#     return file_url

def generate_shipping_invoice(orders):

    from collections import defaultdict
    import tempfile
    from pathlib import Path
    from playwright.sync_api import sync_playwright
    from django.template.loader import render_to_string
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from django.conf import settings

    # ✅ handle single order
    if not isinstance(orders, (list, tuple)):
        orders = [orders]

    first_order = orders[0]

    # ✅ group items
    items_map = defaultdict(lambda: {
        "name": "",
        "qty": 0,
        "unit_price": 0,
        "total_price": 0,
    })

    for order in orders:
        for item in order.items.select_related("product"):
            key = item.product.id

            items_map[key]["name"] = item.product.name
            items_map[key]["unit_price"] = item.selling_price
            items_map[key]["qty"] += item.qty
            items_map[key]["total_price"] += item.selling_price * item.qty

    items = list(items_map.values())

    # ✅ limit items (max 2)
    display_items = items[:2]
    remaining_count = max(0, len(items) - 2)

    # ✅ template selection
    template_name = "store/shipping_invoice.html"
    is_thermal = False

    if first_order.store and first_order.store.product_code == "SRU":
        template_name = "store/shipping_invoice_sru.html"
        is_thermal = True

    # ✅ render HTML
    html_content = render_to_string(
        template_name,
        {
            "order": first_order,
            "address": first_order.address,
            "store": first_order.store,
            "items": display_items,
            "remaining_count": remaining_count,
        }
    )

    # ✅ DEBUG
    print("HTML OK")

    # ✅ create temp files
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "invoice.html"
        pdf_path = Path(tmpdir) / f"invoice_{first_order.id}.pdf"

        html_path.write_text(html_content, encoding="utf-8")

        # ✅ generate PDF
        with sync_playwright() as p:
            browser = p.chromium.launch(
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page()

            page.goto(f"file://{html_path}", wait_until="networkidle")

            if is_thermal:
                page.pdf(
                    path=str(pdf_path),
                    width="6in",
                    height="4in",
                    print_background=True,
                )
            else:
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

        print("PDF GENERATED:", pdf_path)
        storage = StoreS3Storage(
            bucket_name=first_order.store.aws_bucket_name
        )

        # ✅ upload
        file_key = f"invoices/invoice_{first_order.id}.pdf"

        # storage_path = f"shipping/invoice_{first_order.id}.pdf"

        # with open(pdf_path, "rb") as f:
        #     saved_path = default_storage.save(
        #         storage_path,
        #         ContentFile(f.read())
        #     )
        #
        # file_url = settings.MEDIA_URL + saved_path
        with open(pdf_path, "rb") as f:
            file_path = storage.save(
                file_key,
                ContentFile(f.read())
            )

        # get file URL
        file_url = storage.url(file_path)

    print("UPLOADED:", file_url)

    return file_url