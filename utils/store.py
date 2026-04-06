import string
import time
import random

import base64
import hashlib
import json
import requests
from django.conf import settings

from db.models import Order, StoreSequence, OrderSequence, Product, InventoryBatch, InventoryTransaction

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
        order_number = f"{prefix}-{store.id.hex[:4].upper()}-{seq.order_number:08d}"
        if Order.objects.filter(order_number=order_number).first():
            generate_order_number(store, prefix)
        return order_number


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

        updated = Product.objects.filter(
            id=product.id,
            current_stock__gte=qty
        ).update(
            current_stock=F("current_stock") - qty
        )

        if updated == 0:
            raise Exception(f"Insufficient stock for {product.name}")

        # stockout from inventory also.
        batches = InventoryBatch.objects.select_for_update().filter(
            product=product,
            remaining_quantity__gt=0
        ).order_by("created_at")
        qty_to_deduct = qty
        total_cost = 0
        for batch in batches:
            if qty_to_deduct <= 0:
                break
            deduct_qty = min(batch.remaining_quantity, qty_to_deduct)
            total_cost += batch.cost_per_unit * deduct_qty
            batch.remaining_quantity -= deduct_qty
            batch.save(update_fields=["remaining_quantity"])

            InventoryTransaction.objects.create(
                store=product.store,
                product=product,
                batch=batch,
                transaction_type="OUT",
                quantity=deduct_qty,
                cost_price=batch.cost_per_unit,
                selling_price=item.selling_price
            )
            qty_to_deduct -= deduct_qty
        if qty_to_deduct > 0:
            raise Exception(f"Insufficient stock for {product.name}")
        cost_price_at_sale = total_cost / qty
        gross_profit = (item.selling_price * qty) - total_cost
        item.cost_price = cost_price_at_sale
        item.gross_profit = gross_profit
        item.save(update_fields=["cost_price", "gross_profit"])




def generate_phonepe_payment(obj):

    payload = {
        "merchantId": settings.PHONEPE_MERCHANT_ID,
        "merchantTransactionId": str(obj.id),
        "merchantUserId": str(obj.id),
        "amount": 100 * 100,  # ₹100 → paise
        "redirectUrl": f"https://yourdomain.com/payment-success/{obj.id}",
        "redirectMode": "POST",
        "callbackUrl": "https://yourdomain.com/api/phonepe/webhook/",
        "mobileNumber": obj.mobile_number,
        "paymentInstrument": {
            "type": "PAY_PAGE"
        }
    }

    #  Step 1: Convert to JSON string
    payload_json = json.dumps(payload)

    #  Step 2: Base64 encode
    payload_base64 = base64.b64encode(payload_json.encode()).decode()

    #  Step 3: Create checksum
    string_to_hash = payload_base64 + "/pg/v1/pay" + settings.PHONEPE_SALT_KEY
    sha256 = hashlib.sha256(string_to_hash.encode()).hexdigest()
    checksum = sha256 + "###" + settings.PHONEPE_SALT_INDEX

    #  Step 4: Headers
    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": checksum
    }

    #  Step 5: API Call
    response = requests.post(
        settings.PHONEPE_BASE_URL,
        json={"request": payload_base64},
        headers=headers
    )

    return response.json()
