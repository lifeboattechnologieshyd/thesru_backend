import string
import time
import random

from db.models import Order, StoreSequence


# def generate_order_id():
#     while True:
#         order_id = f"{int(time.time())[-6:]}{random.randint(1000,9999)}"
#         if not Order.objects.filter(order_id=order_id).exists():
#             return order_id

def generate_order_id():
    while True:
        timestamp = str(int(time.time()))[-6:]  # last 6 digits
        random_part = random.randint(1000, 9999)
        order_id = f"{timestamp}{random_part}"

        if not Order.objects.filter(order_id=order_id).exists():
            return order_id

from django.db import transaction

def generate_lsin(store, brand_code):
    with transaction.atomic():
        seq, _ = StoreSequence.objects.select_for_update().get_or_create(
            store=store
        )

        seq.last_lsin_number += 1
        seq.save(update_fields=["last_lsin_number"])

        return f"{brand_code}-{str(seq.last_lsin_number).zfill(6)}"




ALPHANUM = string.ascii_uppercase + string.digits

def generate_alphanumeric_lsin(length=12):
    return "".join(random.choices(ALPHANUM, k=length))
