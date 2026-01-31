import os
import sys
import csv

# ==================================================
# 1️⃣ ADD PROJECT ROOT TO PYTHON PATH (FIRST!)
# ==================================================
CURRENT_FILE = os.path.abspath(__file__)
SCRIPTS_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)

sys.path.insert(0, PROJECT_ROOT)

# Debug (optional)
print("PROJECT_ROOT:", PROJECT_ROOT)
print("sys.path[0]:", sys.path[0])

# ==================================================
# 2️⃣ DJANGO SETUP (AFTER sys.path fix)
# ==================================================
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.production"
)

import django
django.setup()

# ==================================================
# 3️⃣ DJANGO IMPORTS (AFTER setup)
# ==================================================
from db.models import PinCode
from django.db import transaction

CSV_FILE_PATH = os.path.join(PROJECT_ROOT, "data", "PINCODES.csv")


from django.db import transaction, IntegrityError

def import_pincodes():
    print("🚀 Starting pincode import...")
    print("📂 CSV FILE:", CSV_FILE_PATH)

    created = 0
    skipped = 0


    with open(CSV_FILE_PATH, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            try:
                pin_raw = row.get("pincode")
                if not pin_raw:
                    raise ValueError("Missing pincode")

                pin = int(pin_raw)

                # ✅ savepoint per row
                with transaction.atomic():
                    PinCode.objects.create(
                        pin=pin,
                        city=row.get("officename", "").strip(),
                        area=row.get("district", "").strip(),
                        state=row.get("statename", "").strip(),
                        country="India",
                    )

                created += 1

            except Exception as e:
                skipped += 1
                # optional: log first few errors only
                if skipped < 10:
                    print(f"❌ Skipped pin {row.get('pincode')}: {e}")

    print(f"✅ Import completed | Created: {created}, Skipped: {skipped}")
if __name__ == "__main__":
    import_pincodes()