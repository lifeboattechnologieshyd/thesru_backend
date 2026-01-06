from unicodedata import category
from django.db import transaction
from django.db import IntegrityError
from rest_framework.views import APIView
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated

from db.models import  Category, Product, DisplayProduct, Banner, Inventory, PinCode, Coupon, Store
from enums.store import InventoryType
from mixins.drf_views import CustomResponse


class ProductAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data

        required_fields = ["name", "mrp", "selling_price","thumbnail_image"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse().errorResponse(
                    description=f"{field} is required"
                )
        try:
            Product.objects.create(
                name=data.get("name"),
                size=data.get("size"),
                colour=data.get("colour"),
                mrp=data.get("mrp"),
                selling_price=data.get("selling_price"),
                mrp_others=data.get("mrp_others"),
                selling_price_others=data.get("selling_price_others"),
                inr=data.get("inr"),
                sku=data.get("sku"),
                gst_percentage=data.get("gst_percentage"),
                gst_amount=data.get("gst_amount"),
                current_stock=data.get("current_stock"),
                images=data.get("images"),
                videos=data.get("videos"),
                thumbnail_image=data.get("thumbnail_image")
            )

            return CustomResponse.successResponse(
                data={},
                description="Product created successfully"
            )

        except IntegrityError as e:
            # Handle duplicate SKU error
            if "product_sku_key" in str(e):
                return CustomResponse.errorResponse(
                    description="Product with this SKU already exists"
                )
            return CustomResponse.errorResponse(
                description="Database integrity error"
            )
    def get(self, request, id=None):
        # ---------- SINGLE CATEGORY ----------
        if id:
            product = Product.objects.filter(id=id).values().first()
            if not product:
                return CustomResponse.errorResponse(
                    description="product  not found"
                )

            return CustomResponse.successResponse(
                data=[product],
                total=1
            )

        # ---------- PAGINATION ----------
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse.errorResponse(
                description="page and page_size must be positive integers"
            )

        queryset = Product.objects.all().order_by("-created_at")

        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]

        data = list(queryset.values())

        return CustomResponse.successResponse(
            data=data,
            total=total
        )

    def put(self, request, id=None):
        if not id:
            return CustomResponse().errorResponse(description="Product id is required")

        product = Product.objects.filter(id=id).first()
        if not product:
            return CustomResponse().errorResponse(description="Product not found")

        for field in [
            "name", "size", "colour", "mrp", "selling_price","selling_price_others","mrp_others","inr"
            "gst_percentage", "gst_amount", "current_stock",
            "images", "videos", "thumbnail_image"
        ]:
            if field in request.data:
                setattr(product, field, request.data.get(field))

        product.save()

        return CustomResponse().successResponse(
            data={}, description="Product updated successfully"
        )

    def delete(self, request, id=None):
        if not id:
            return CustomResponse().errorResponse(description="Product id is required")

        product = Product.objects.filter(id=id).first()
        if not product:
            return CustomResponse().errorResponse(description="Product not found")

        product.delete()

        return CustomResponse().successResponse(
            data={}, description="Product deleted successfully"
        )




class DisplayProductAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data

        required_fields = ["default_product_id", "variant_product_id", "category","product_name"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse().errorResponse(
                    description=f"{field} is required"
                )
        DisplayProduct.objects.create(
            default_product_id = data.get("default_product_id"),
            variant_product_id = data.get("variant_product_id"),
            is_active = data.get("is_active"),
            category = data.get("category"),
            gender = data.get("gender"),
            tags = data.get("tags"),
            search_tags = data.get("search_tags"),
            product_name = data.get("product_name"),
            product_tagline = data.get("product_tagline"),
            age = data.get("age"),
            description = data.get("description"),
            highlights = data.get("highlights"),
            rating = data.get("rating"),
            number_of_reviews = data.get("number_of_reviews")



        )
        return CustomResponse.successResponse(data={},description="display product created successfully")






    def get(self, request, id=None):
        queryset = DisplayProduct.objects.filter(is_active=True)

        # ---------- SINGLE DISPLAY PRODUCT ----------
        if id:
            product = queryset.filter(id=id).first()
            if not product:
                return CustomResponse().errorResponse(
                    description="display product not found"
                )

            return CustomResponse().successResponse(
                data={
                    "id": str(product.id),
                    "default_product_id": str(product.default_product_id),
                    "variant_product_id": product.variant_product_id or [],
                    "category": product.category,
                    "gender": product.gender,
                    "tags": product.tags,
                    "search_tags": product.search_tags,
                    "product_name": product.product_name,
                    "product_tagline": product.product_tagline,
                    "age": product.age,
                    "description": product.description,
                    "highlights": product.highlights,
                    "rating": product.rating,
                    "number_of_reviews": product.number_of_reviews,
                    "is_active": product.is_active,
                    "created_at": product.created_at,
                },
                total=1
            )

        # ---------- PAGINATION ----------
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse().errorResponse(
                description="page and page_size must be positive integers"
            )

        queryset = queryset.order_by("-created_at")

        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]

        # ---------- LIST DISPLAY PRODUCTS ----------
        data = []
        for product in queryset:
            data.append({
                "id": str(product.id),
                "default_product_id": str(product.default_product_id),
                "variant_product_id": product.variant_product_id or [],
                "product_name": product.product_name,
                "product_tagline": product.product_tagline,
                "category": product.category,
                "gender": product.gender,
                "rating": product.rating,
                "number_of_reviews": product.number_of_reviews,
                "created_at": product.created_at,
            })

        return CustomResponse().successResponse(
            data=data,
            total=total
        )




    def put(self, request, id=None):
        if not id:
            return CustomResponse().errorResponse(description="display product id is required")

        product = DisplayProduct.objects.filter(id=id).first()
        if not product:
            return CustomResponse().errorResponse(description="display product not found")

        for field in [
            "default_product_id", "variant_product_id", "is_active", "category", "gender","tags","search_tags","product_name"
            "product_tagline", "age", "description",
            "highlights", "rating", "number_of_reviews"
        ]:
            if field in request.data:
                setattr(product, field, request.data.get(field))

        product.save()

        return CustomResponse().successResponse(
            data={}, description="display product updated successfully"
        )



    def delete(self, request, id=None):
        if not id:
            return CustomResponse().errorResponse(description="display product id is required")

        product = DisplayProduct.objects.filter(id=id).first()
        if not product:
            return CustomResponse().errorResponse(description="display product not found")

        product.delete()

        return CustomResponse().successResponse(
            data={}, description="display product deleted successfully"
        )



class CategoriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data

        required_fields = ["name","icon","search_tags","is_active"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

        Category.objects.create(
            name = data.get("name"),
            icon = data.get("icon"),
            search_tags = data.get("search_tags"),
            is_active = data.get("is_active")


        )
        return CustomResponse.successResponse(data={},description="category created successfully")

    def get(self, request, id=None):
        if id:
            category = Category.objects.filter(id=id).values().first()
            if not category:
                return CustomResponse.errorResponse(
                    description="category not found"
                )

            return CustomResponse.successResponse(
                data=[category],
                total=1
            )

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse.errorResponse(
                description="page and page_size must be positive integers"
            )

        queryset = Category.objects.all().order_by("-created_at")

        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]

        data = list(queryset.values())

        return CustomResponse.successResponse(
            data=data,
            total=total,

        )

    def put(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="category id required")

        category = Category.objects.filter(id=id).first()
        if not category:
            return CustomResponse.errorResponse(description="category not found")
        for field in [
            "name","icon","search_tags","is_active"
        ]:
            if field in request.data:
                setattr(category,field,request.data.get(field))

        category.save()

        return CustomResponse.successResponse(data={},description="category updated successfully")

    def delete(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="category id required")

        category = Category.objects.filter(id=id).first()
        if not category:
            return CustomResponse.errorResponse(description="category not found")
        category.delete()
        return CustomResponse.successResponse(data={},description="category deleted successfully")


class BannerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data
        required_fields = ["screen","image","is_active","priority","action","destination"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

        Banner.objects.create(
            screen = data.get("screen"),
            image = data.get("image"),
            is_active = data.get("is_active"),
            priority = data.get("priority"),
            action = data.get("action"),
            destination = data.get("destination"),




        )
        return CustomResponse.successResponse(data={},description="banner created successfully")

    def get(self, request, id=None):
        # ---------- SINGLE BANNER ----------
        if id:
            banner = Banner.objects.filter(id=id).values().first()
            if not banner:
                return CustomResponse.errorResponse(
                    description="banner id required"
                )

            return CustomResponse.successResponse(
                data=[banner],
                total=1
            )

        # ---------- PAGINATION ----------
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse.errorResponse(
                description="page and page_size must be positive integers"
            )

        queryset = Banner.objects.all().order_by("-created_at")

        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]

        data = list(queryset.values())

        return CustomResponse.successResponse(
            data=data,
            total=total
        )


    def put(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="banner id required")

        banner = Banner.objects.filter(id=id).first()

        if not banner:
            return CustomResponse.errorResponse(description="banner not found")


        for field in [
            "screen","image","priority","is_active","action","destination"
        ]:
            if field in request.data:
                setattr(banner,field,request.data.get(field))

        banner.save()
        return CustomResponse.successResponse(data={},description="banner updated successfully")

    def delete(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="banner id required")

        banner = Banner.objects.filter(id=id).filter()
        if not banner:
            return CustomResponse.errorResponse(description="banner not found")

        banner.delete()
        return CustomResponse.successResponse(data={},description="banner deleted successfully")




class InventoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        required_fields = [
            "product_id", "sku", "type", "quantity"
        ]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse().errorResponse(
                    description=f"{field} is required"
                )

        product_id = data.get("product_id")
        sku = data.get("sku")
        inv_type = data.get("type")
        quantity = int(data.get("quantity"))

        if quantity <= 0:
            return CustomResponse().errorResponse(
                description="Quantity must be greater than zero"
            )

        # Get last stock
        last_inventory = (
            Inventory.objects
            .filter(product_id=product_id)
            .order_by("-created_at")
            .first()
        )

        quantity_before = last_inventory.quantity_after if last_inventory else 0

        # Decide stock movement
        if inv_type in [
            InventoryType.PURCHASE,
            InventoryType.SaleReturn,
        ]:
            quantity_after = quantity_before + quantity

        elif inv_type in [
            InventoryType.SELL,
            InventoryType.PurchaseReturn,
        ]:
            if quantity > quantity_before:
                return CustomResponse().errorResponse(
                    description="Insufficient stock"
                )
            quantity_after = quantity_before - quantity
        else:
            return CustomResponse().errorResponse(
                description="Invalid inventory type"
            )


        #  Price calculations
        purchase_price = data.get("purchase_price")
        sale_price = data.get("sale_price")

        purchase_rate = 0
        sale_rate = 0

        # PURCHASE & PURCHASE_RETURN
        if inv_type in [InventoryType.PURCHASE, InventoryType.PurchaseReturn]:
            if not purchase_price:
                return CustomResponse().errorResponse(
                    description="purchase_price is required for purchase"
                )

            purchase_price = float(purchase_price)
            purchase_rate = round(purchase_price / quantity, 2)

        # SELL & SALE_RETURN
        elif inv_type in [InventoryType.SELL, InventoryType.SaleReturn]:
            if not sale_price:
                return CustomResponse().errorResponse(
                    description="sale_price is required for sale"
                )

            sale_price = float(sale_price)
            sale_rate = round(sale_price / quantity, 2)

        #   set defaults
        purchase_price = purchase_price or 0
        sale_price = sale_price or 0
        purchase_rate = purchase_rate or 0
        sale_rate = sale_rate or 0




        # 4️⃣ Save inventory atomically
        with transaction.atomic():
            inventory = Inventory.objects.create(
                product_id=product_id,
                sku=sku,
                type=inv_type,
                date=data.get("date") or timezone.now(),
                user=request.user.id,
                quantity=quantity,
                quantity_before=quantity_before,
                quantity_after=quantity_after,

                purchase_rate_per_item=purchase_rate,
                purchase_price=purchase_price,

                sale_rate_per_item=sale_rate,
                sale_price=sale_price,

                gst_input=data.get("gst_input", 0),
                gst_output=data.get("gst_output", 0),
                remarks=data.get("remarks"),
            )


        return CustomResponse().successResponse(
            description="Inventory updated successfully",
            data={
                "inventory_id": str(inventory.id),
                "quantity_before": quantity_before,
                "quantity_after": quantity_after,
                "type": inv_type,
                "purchase_rate_per_item":purchase_rate,
                "purchase_price":purchase_price,
            }
        )
    def get(self, request, id=None):
        queryset = Inventory.objects.all()

        # ---------- SINGLE INVENTORY ----------
        if id:
            inv = queryset.filter(id=id).first()
            if not inv:
                return CustomResponse().errorResponse(
                    description="Inventory not found"
                )

            return CustomResponse().successResponse(
                data={
                    "id": str(inv.id),
                    "product_id": str(inv.product_id),
                    "sku": inv.sku,
                    "type": inv.type,
                    "quantity": inv.quantity,
                    "quantity_before": inv.quantity_before,
                    "quantity_after": inv.quantity_after,
                    "purchase_price": inv.purchase_price,
                    "sale_price": inv.sale_price,
                    "created_at": inv.created_at,
                },
                total=1
            )

        # ---------- PAGINATION ----------
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse().errorResponse(
                description="page and page_size must be positive integers"
            )

        queryset = queryset.order_by("-created_at")

        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]

        # ---------- LIST INVENTORY ----------
        data = []
        for inv in queryset:
            data.append({
                "id": str(inv.id),
                "product_id": str(inv.product_id),
                "type": inv.type,
                "quantity": inv.quantity,
                "quantity_after": inv.quantity_after,
                "created_at": inv.created_at,
            })

        return CustomResponse().successResponse(
            data=data,
            total=total
        )



    def put(self, request,id=None):
        if not id:
            return CustomResponse().errorResponse(
                description="Inventory id is required"
            )

        inventory = Inventory.objects.filter(id=id).first()
        if not inventory:
            return CustomResponse().errorResponse(
                description="Inventory not found"
            )

        editable_fields = ["remarks"]

        for field in editable_fields:
            if field in request.data:
                setattr(inventory, field, request.data.get(field))

        inventory.save()

        return CustomResponse().successResponse(
            data={},description="Inventory updated successfully"
        )

    def delete(self, request,id=None):
        if not id:
            return CustomResponse().errorResponse(
                description="Inventory id is required"
            )

        inventory = Inventory.objects.filter(id=id).first()
        if not inventory:
            return CustomResponse().errorResponse(
                description="Inventory not found"
            )

        inventory.delete()

        return CustomResponse().successResponse(data={},
            description="Inventory deleted successfully"
        )

class PinCodeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data

        required_fields = ["pin","state","area","city","country"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")


        try:
            PinCode.objects.create(
            pin = data.get("pin"),
            state = data.get("state"),
            area = data.get("area"),
            city = data.get("city"),
            country = data.get("country")
            )
            return CustomResponse.successResponse(data={},description="pincode created successfully")

        except IntegrityError as e:
            if "pin" in str(e).lower():
                return CustomResponse.errorResponse(
                    description="This pincode already exists"
                )
            return CustomResponse.errorResponse(
                description="Database integrity error"
            )






    def get(self, request, id=None):
        # ---------- SINGLE PINCODE ----------
        if id:
            pin = PinCode.objects.filter(id=id).values().first()
            if not pin:
                return CustomResponse.errorResponse(
                    description="pincode id required"
                )

            return CustomResponse.successResponse(
                data=[pin],
                total=1
            )

        # ---------- PAGINATION ----------
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse.errorResponse(
                description="page and page_size must be positive integers"
            )

        queryset = PinCode.objects.all().order_by("-created_at")

        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]

        data = list(queryset.values())

        return CustomResponse.successResponse(
            data=data,
            total=total
        )


    def put(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="pincode id required")

        pin = PinCode.objects.filter(id=id).first()

        if not pin:
            return CustomResponse.errorResponse(description="pincode not found")


        for field in [
            "pin","state","area","city","country",
        ]:
            if field in request.data:
                setattr(pin,field,request.data.get(field))

        pin.save()
        return CustomResponse.successResponse(data={},description="pincode updated successfully")

    def delete(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="pincode id required")

        pin = PinCode.objects.filter(id=id).filter()
        if not pin:
            return CustomResponse.errorResponse(description="pincode not found")

        pin.delete()
        return CustomResponse.successResponse(data={},description="pincode deleted successfully")



class CouponAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data

        required_fields = ["bonus_code","start_date","expiry_date","minimum_cart_value","bonus_percentage",
                           "maximum_bonus",]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

        Coupon.objects.create(
            bonus_code = data.get("bonus_code"),
            start_date = data.get("start_date"),
            expiry_date = data.get("expiry_date"),
            minimum_cart_value = data.get("minimum_cart_value"),
            bonus_percentage = data.get("bonus_percentage"),
            maximum_bonus = data.get("maximum_bonus"),
            terms = data.get("terms"),
            validity_count = data.get("validity_count"),
            short_title = data.get("short_title"),
            long_title = data.get("long_title"),


        )
        return CustomResponse.successResponse(data={},description="coupon created successfully")


    def get(self,request,id = None):
        if id:
            coupon = Coupon.objects.filter(id=id).values().first()
            if not coupon:
                return CustomResponse.errorResponse(
                    description="coupon id required"
                )

            return CustomResponse.successResponse(
                data=[coupon],
                total=1
            )
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse.errorResponse(
                description="page and page_size must be positive integers"
            )

        queryset = Coupon.objects.all().order_by("-created_at")

        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]

        data = list(queryset.values())

        return CustomResponse.successResponse(
            data=data,
            total=total
        )
    def put(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="coupon id required")

        coupon = Coupon.objects.filter(id=id).first()

        if not coupon:
            return CustomResponse.errorResponse(description="coupon not found")


        for field in [
            "start_date","state","area","city","country",
        ]:
            if field in request.data:
                setattr(coupon,field,request.data.get(field))

        coupon.save()
        return CustomResponse.successResponse(data={},description="coupon updated successfully")

    def delete(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="coupon id required")

        coupon = Coupon.objects.filter(id=id).filter()
        if not coupon:
            return CustomResponse.errorResponse(description="coupon not found")

        coupon.delete()
        return CustomResponse.successResponse(data={},description="coupon deleted successfully")





class StoreAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # ---------------- CREATE STORE ----------------
    def post(self, request):
        data = request.data

        required_fields = ["name", "mobile", "address", "logo", "gst_number"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(
                    description=f"{field} is required"
                )

        try:
            Store.objects.create(
                name=data.get("name"),
                mobile=data.get("mobile"),
                address=data.get("address"),
                logo=data.get("logo"),
                gst_number=data.get("gst_number"),
            )

            return CustomResponse.successResponse(
                data={},
                description="store created successfully"
            )

        except IntegrityError:
            return CustomResponse.errorResponse(
                description="Database integrity error"
            )

    # ---------------- GET STORE / LIST ----------------
    def get(self, request, id=None):
        # ---------- SINGLE STORE ----------
        if id:
            store = Store.objects.filter(id=id).values().first()
            if not store:
                return CustomResponse.errorResponse(
                    description="store not found"
                )

            return CustomResponse.successResponse(
                data=[store],
                total=1
            )

        # ---------- PAGINATION ----------
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse.errorResponse(
                description="page and page_size must be positive integers"
            )

        queryset = Store.objects.all().order_by("-created_at")

        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]

        data = list(queryset.values())

        return CustomResponse.successResponse(
            data=data,
            total=total
        )

    # ---------------- UPDATE STORE ----------------
    def put(self, request, id=None):
        if not id:
            return CustomResponse.errorResponse(
                description="store id required"
            )

        store = Store.objects.filter(id=id).first()
        if not store:
            return CustomResponse.errorResponse(
                description="store not found"
            )

        for field in [
            "name",
            "mobile",
            "address",
            "logo",
            "gst_number",
        ]:
            if field in request.data:
                setattr(store, field, request.data.get(field))

        store.save()

        return CustomResponse.successResponse(
            data={},
            description="store updated successfully"
        )

    # ---------------- DELETE STORE ----------------
    def delete(self, request, id=None):
        if not id:
            return CustomResponse.errorResponse(
                description="store id required"
            )

        store = Store.objects.filter(id=id)
        if not store.exists():
            return CustomResponse.errorResponse(
                description="store not found"
            )

        store.delete()

        return CustomResponse.successResponse(
            data={},
            description="store deleted successfully"
        )


