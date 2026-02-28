import string
import time
import random
import requests
from db.models import Order, StoreSequence, OrderSequence, Product

# def generate_order_id():
#     while True:
#         order_id = f"{int(time.time())[-6:]}{random.randint(1000,9999)}"
#         if not Order.objects.filter(order_id=order_id).exists():
#             return order_id

from django.utils import timezone

from enums.store import OrderStatus


def time_ago(dt):
    if not dt:
        return None

    now = timezone.now()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds // 604800)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds // 2592000)
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = int(seconds // 31536000)
        return f"{years} year{'s' if years > 1 else ''} ago"


from django.db import transaction

def generate_lsin(store, brand_code):
    with transaction.atomic():
        seq, _ = StoreSequence.objects.select_for_update().get_or_create(
            store=store
        )
        seq.last_lsin_number += 1
        seq.save(update_fields=["last_lsin_number"])

        return f"{brand_code}-{str(seq.last_lsin_number).zfill(6)}"

def generate_order_number(store, prefix):
    with transaction.atomic():
        seq, _ = OrderSequence.objects.select_for_update().get_or_create(
            store=store
        )
        seq.order_number += 1
        seq.save(update_fields=["order_number"])

        return f"{prefix}-{store.id.hex[:4].upper()}-{seq.order_number:08d}"


BO_STATUS_FLOW = {
    OrderStatus.CREATED: [OrderStatus.PACKED],
    OrderStatus.PACKED: [OrderStatus.SHIPPED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
}

from django.db import transaction
from django.db.models import F

def update_stock_after_order(order):
    """
    Reduce stock for each product in the order
    """

    for item in order.items.select_related("product"):
        product = item.product
        qty = item.qty

        # Safety check
        if product.current_stock < qty:
            raise Exception(
                f"Insufficient stock for {product.name}"
            )

        # Atomic update (prevents race conditions)
        Product.objects.filter(
            id=product.id
        ).update(
            current_stock=F("current_stock") - qty
        )


import requests

def cashfree_create_subscription(store, payload):
    """
    Creates subscription in Cashfree using STORE-based credentials
    """

    url = "https://sandbox.cashfree.com/pg/subscriptions"

    headers = {
        "x-client-id": store.client_id,
        "x-client-secret": store.client_secret,
        "Content-Type": "application/json"
    }

    print("CASHFREE REQUEST PAYLOAD:", payload)

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    return response.json()