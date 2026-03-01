from decimal import Decimal

from django.db import transaction
from django.db.models import F
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Product, InventoryBatch, InventoryTransaction
from mixins.drf_views import CustomResponse


class StockInAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        store = request.store
        user = request.user
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity")
        cost_per_unit = request.data.get("cost_per_unit")
        sell_price = request.data.get("sell_price")
        # ---- Basic Validations ----
        if not product_id:
            return CustomResponse().errorResponse(data={}, description="product_id is required")
        if not quantity or int(quantity) <= 0:
            return CustomResponse().errorResponse(data={}, description="quantity must be greater than 0")
        if not cost_per_unit:
            return CustomResponse().errorResponse(data={}, description="cost_per_unit is required")
        if not sell_price:
            return CustomResponse().errorResponse(data={}, description="sell_price is required")
        try:
            product = Product.objects.get(id=product_id, store=store)
        except Product.DoesNotExist:
            return CustomResponse().errorResponse(data={}, description="Invalid product_id")

        quantity = int(quantity)
        cost_per_unit = Decimal(cost_per_unit)
        sell_price = Decimal(sell_price)

        # ---- Create Inventory Batch ----
        batch = InventoryBatch.objects.create(
            store=product.store,
            product=product,
            input_quantity=quantity,
            remaining_quantity=quantity,
            cost_per_unit=cost_per_unit,
            sell_price=sell_price
        )

        # ---- Create Ledger Entry ----
        InventoryTransaction.objects.create(
            store=product.store,
            product=product,
            batch=batch,
            transaction_type='IN',
            quantity=quantity,
            cost_price=cost_per_unit,
            selling_price=sell_price
        )
        Product.objects.filter(id=product.id).update(
            current_stock=F("current_stock") + quantity
        )
        return CustomResponse().successResponse(data={}, description="Stock added successfully")





