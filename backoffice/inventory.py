from decimal import Decimal

import pandas as pd
from django.db import transaction
from django.db.models import F
from rest_framework.permissions import IsAuthenticated, AllowAny
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

    def get(self,request):
        store = request.store
        product_id = request.GET.get("product_id")

        queryset = InventoryBatch.objects.select_related("product").filter(store=store).order_by("-created_at")
        # ✅ optional filter
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        offset = (page - 1) * page_size
        total = queryset.count()
        queryset = queryset[offset: offset + page_size]
        data = []

        for batch in queryset:
            data.append({
                "id": batch.id,
                "input_quantity": batch.input_quantity,
                "remaining_quantity": batch.remaining_quantity,
                "cost_per_unit": batch.cost_per_unit,
                "product": {
                    "id": batch.product.id,
                    "name": batch.product.name,
                    "color": batch.product.colour,
                    "size": batch.product.size,
                    "current_stock": batch.product.current_stock
                }
            })

        return CustomResponse.successResponse(
            data=data,
            total=total
        )




class BulkInventory(APIView, CustomResponse):

    permission_classes = [AllowAny]
    def post(self, request):

        if "file" not in request.FILES:
            return self.errorResponse(
                data={},
                description="Excel file required"
            )

        file = request.FILES["file"]

        try:
            df = pd.read_csv(file)
        except Exception as e:
            return self.errorResponse(
                description="Invalid Excel file"
            )

        required_columns = [
            "product_id",
            "name",
            "qty",
            "cost_price",
            "selling_price"
        ]

        for col in required_columns:
            if col not in df.columns:
                return self.errorResponse(
                    description=f"{col} column missing"
                )
        with transaction.atomic():

            for _, row in df.iterrows():

                product_id = row["product_id"]
                qty = row["qty"]
                cost = row["cost_price"]
                price = row["selling_price"]
                try:
                    product = Product.objects.get(id=product_id, store=store)
                except Product.DoesNotExist:
                    return CustomResponse().errorResponse(data={}, description="Invalid product_id")

                quantity = int(qty)
                cost_per_unit = Decimal(cost)
                sell_price = Decimal(price)

                # ---- Create Inventory Batch ----
                batch = InventoryBatch.objects.create(
                    store=product.store,
                    product=product,
                    input_quantity=quantity,
                    remaining_quantity=quantity,
                    cost_per_unit=cost_per_unit,
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
        return self.successResponse(
            description="Inventory updated",
            data={}
        )



