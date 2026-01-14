from unicodedata import category
from django.db import transaction
from django.db import IntegrityError
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Sum

from rest_framework.permissions import IsAuthenticated

from db.models import  Category, Product, DisplayProduct, Banner, Inventory, PinCode, Coupon, Store, WebBanner, \
    FlashSaleBanner, Order, User, Cart
from enums.store import InventoryType, OrderStatus
from mixins.drf_views import CustomResponse


class ProductAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data
        store = request.store


        required_fields = ["name", "mrp", "selling_price","thumbnail_image"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse().errorResponse(
                    description=f"{field} is required"
                )
        try:
            Product.objects.create(
                store_id=store.id,
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
        store = request.store


        required_fields = ["default_product_id", "category","product_name"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse().errorResponse(
                    description=f"{field} is required"
                )
        DisplayProduct.objects.create(
            store_id=store.id,
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
        store = request.store


        required_fields = ["name","icon","search_tags","is_active"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

        Category.objects.create(
            store_id=store.id,
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
        store = request.store

        required_fields = ["screen","image","is_active","priority","action","destination"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

        Banner.objects.create(
            store_id=store.id,
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
        store = request.store


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
                store_id=store.id,
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


class WebBannerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data
        store = request.store

        required_fields = ["screen","image","is_active","priority","action","destination"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

        WebBanner.objects.create(
            store_id=store.id,
            screen = data.get("screen"),
            image = data.get("image"),
            is_active = data.get("is_active"),
            priority = data.get("priority"),
            action = data.get("action"),
            destination = data.get("destination"),

        )
        return CustomResponse.successResponse(data={},description="web banner created successfully")

    def get(self, request, id=None):
        # ---------- SINGLE BANNER ----------
        if id:
            banner = WebBanner.objects.filter(id=id).values().first()
            if not banner:
                return CustomResponse.errorResponse(
                    description="web banner id required"
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

        queryset = WebBanner.objects.all().order_by("-created_at")

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
            return CustomResponse.errorResponse(description="web banner id required")

        banner = WebBanner.objects.filter(id=id).first()

        if not banner:
            return CustomResponse.errorResponse(description="web banner not found")


        for field in [
            "screen","image","priority","is_active","action","destination"
        ]:
            if field in request.data:
                setattr(banner,field,request.data.get(field))

        banner.save()
        return CustomResponse.successResponse(data={},description="web banner updated successfully")

    def delete(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="web banner id required")

        banner = WebBanner.objects.filter(id=id).filter()
        if not banner:
            return CustomResponse.errorResponse(description="web banner not found")

        banner.delete()
        return CustomResponse.successResponse(data={},description="web banner deleted successfully")


class FlashSaleBannerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data
        store = request.store

        required_fields = ["screen","image","is_active","priority","action","destination","start_date","end_date","product_id","discount"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

        FlashSaleBanner.objects.create(
            store_id=store.id,
            screen = data.get("screen"),
            image = data.get("image"),
            is_active = data.get("is_active"),
            priority = data.get("priority"),
            action = data.get("action"),
            destination = data.get("destination"),
            start_date = data.get("start_date"),
            end_date = data.get("end_date"),
            product_id = data.get("product_id"),
            discount = data.get("discount"),
            name = data.get("name"),
            title = data.get("title"),
            description = data.get("description"),

        )
        return CustomResponse.successResponse(data={},description="flash sale banner created successfully")

    def get(self, request, id=None):
        # ---------- SINGLE BANNER ----------
        if id:
            banner = FlashSaleBanner.objects.filter(id=id).values().first()
            if not banner:
                return CustomResponse.errorResponse(
                    description="flash sale banner id required"
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

        queryset = FlashSaleBanner.objects.all().order_by("-created_at")

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
            return CustomResponse.errorResponse(description="flash sale banner id required")

        banner = FlashSaleBanner.objects.filter(id=id).first()

        if not banner:
            return CustomResponse.errorResponse(description="flash sale banner not found")


        for field in [
            "screen","image","priority","is_active","action","destination","description","title","name"
        ]:
            if field in request.data:
                setattr(banner,field,request.data.get(field))

        banner.save()
        return CustomResponse.successResponse(data={},description="flash sale banner updated successfully")

    def delete(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="flash sale banner id required")

        banner = FlashSaleBanner.objects.filter(id=id).filter()
        if not banner:
            return CustomResponse.errorResponse(description="flash sale banner not found")

        banner.delete()
        return CustomResponse.successResponse(data={},description="flash sale banner deleted successfully")



class OrderStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            store = request.store
            from_date = request.query_params.get("from_date")
            to_date = request.query_params.get("to_date")

            queryset = Order.objects.filter(store_id=store.id)

            # -------- Date Filters --------
            if from_date:
                queryset = queryset.filter(created_at__date__gte=from_date)

            if to_date:
                queryset = queryset.filter(created_at__date__lte=to_date)

            # -------- Total Orders --------
            total_orders = queryset.count()

            # -------- Status-wise Count --------
            status_data = (
                queryset.values("status")
                .annotate(count=Count("id"))
            )

            status_counts = {
                item["status"]: item["count"]
                for item in status_data
            }

            # -------- amount Stats --------
            revenue = queryset.aggregate(
                total_amount=Sum("amount"),
                paid_online=Sum("paid_online"),
                cash_on_delivery=Sum("cash_on_delivery"),
                wallet_paid=Sum("wallet_paid"),
            )

            response_data = {
                "total_orders": total_orders,
                "status_counts": status_counts,
                "revenue": {
                    "total_amount": revenue["total_amount"] or 0,
                    "paid_online": revenue["paid_online"] or 0,
                    "cash_on_delivery": revenue["cash_on_delivery"] or 0,
                    "wallet_paid": revenue["wallet_paid"] or 0,
                }
            }

            return CustomResponse().successResponse(
                message="Order statistics fetched successfully",
                data=response_data
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                description=str(e)
            )


class AbandonedOrderStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            store = request.store
            from_date = request.query_params.get("from_date")
            to_date = request.query_params.get("to_date")

            queryset = Order.objects.filter(
                store_id=store.id,
                status__in=[
                    OrderStatus.CANCELLED,
                    OrderStatus.FAILED
                ]
            )

            # -------- Date Filters --------
            if from_date:
                queryset = queryset.filter(created_at__date__gte=from_date)

            if to_date:
                queryset = queryset.filter(created_at__date__lte=to_date)

            # -------- Counts --------
            cancelled_count = queryset.filter(
                status=OrderStatus.CANCELLED
            ).count()

            failed_count = queryset.filter(
                status=OrderStatus.FAILED
            ).count()

            # -------- Amount Stats --------
            cancelled_amount = queryset.filter(
                status=OrderStatus.CANCELLED
            ).aggregate(total=Sum("amount"))["total"] or 0

            failed_amount = queryset.filter(
                status=OrderStatus.FAILED
            ).aggregate(total=Sum("amount"))["total"] or 0

            response_data = {
                "cancelled": {
                    "count": cancelled_count,
                    "amount": cancelled_amount
                },
                "failed": {
                    "count": failed_count,
                    "amount": failed_amount
                }
            }

            return CustomResponse().successResponse(
                message="Cancelled and failed order statistics fetched successfully",
                data=response_data
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                description=str(e)
            )

class CartListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            store = request.store

            carts = list(
                Cart.objects.filter(store_id=store.id).values(
                    "id",
                    "user_id",
                    "product_id",
                    "quantity"
                )
            )

            # -------- Fetch Usernames --------
            user_ids = {cart["user_id"] for cart in carts}

            users = User.objects.filter(id__in=user_ids).values(
                "id", "username"
            )

            user_map = {
                user["id"]: user["username"]
                for user in users
            }

            # -------- Attach Username --------
            for cart in carts:
                cart["username"] = user_map.get(cart["user_id"])

            return CustomResponse().successResponse(
                message="Cart records fetched successfully",
                data=carts
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                description=str(e)
            )


class OrderListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            store = request.store

            orders = list(
                Order.objects.filter(store_id=store.id)
                .order_by("-created_at")
                .values(
                    "id",
                    "order_id",
                    "user_id",
                    "amount",
                    "wallet_paid",
                    "paid_online",
                    "cash_on_delivery",
                    "status",
                    "created_at",
                )
            )

            # -------- Fetch Usernames --------
            user_ids = {order["user_id"] for order in orders}

            users = User.objects.filter(id__in=user_ids).values(
                "id", "username"
            )

            user_map = {
                user["id"]: user["username"]
                for user in users
            }

            # -------- Final Response Shape --------
            for order in orders:
                order["user_name"] = user_map.get(order["user_id"])

                order["payment_status"] = (
                    "Paid"
                    if (
                            order["paid_online"] > 0
                            or order["cash_on_delivery"] > 0
                            or order["wallet_paid"] > 0
                    )
                    else "Unpaid"
                )

                # cleanup
                order.pop("user_id", None)
                order.pop("paid_online", None)
                order.pop("cash_on_delivery", None)
                order.pop("wallet_paid", None)

            return CustomResponse().successResponse(
                message="Orders fetched successfully",
                data=orders
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                description=str(e)
            )