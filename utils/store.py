import string
import time
import random

from db.models import Order



def generate_order_id():
    while True:
        order_id = f"{int(time.time())[-6:]}{random.randint(1000,9999)}"
        if not Order.objects.filter(order_id=order_id).exists():
            return order_id

