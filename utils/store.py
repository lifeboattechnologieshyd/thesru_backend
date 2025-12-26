import string
import time
import random

from db.models import Order



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