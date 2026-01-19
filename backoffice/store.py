from datetime import timedelta
from unicodedata import category
from django.db.models import Q

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db import IntegrityError
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Sum

from rest_framework.permissions import IsAuthenticated, AllowAny
from urllib3 import request

from config.settings.common import DEBUG
from db.models import Category, Product, ProductVariant, Banner, Inventory, PinCode, Coupon, Store, WebBanner, \
    FlashSaleBanner, Order, User, Cart, OrderProducts, UserOTP, StoreClient, UserSession, ProductMedia, Tag
from enums.store import InventoryType, OrderStatus
from mixins.drf_views import CustomResponse
from rest_framework_simplejwt.tokens import RefreshToken

from utils.user import generate_otp, send_otp_to_mobile


class SendOTP(APIView):

    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data
        store = request.store
        user = User.objects.filter(mobile=data.get("mobile"),user_role__contains=["ADMIN"], store=store).first()
        if user:
            otp = generate_otp()
            if DEBUG:
                otp = 1234
            else:
                send_otp_to_mobile(otp, data.get("mobile"))
            expires_at = timezone.now() + timedelta(minutes=15)

            UserOTP.objects.filter(
                store=request.store,
                mobile=data.get("mobile"),
                is_used=False
            ).update(is_used=True)
            # Save OTP with store
            UserOTP.objects.create(
                store=request.store,
                mobile=data.get("mobile"),
                otp=otp,
                expires_at=expires_at
            )
            return CustomResponse().successResponse(
                description="OTP sent successfully",
                data={
                    "mobile": data.get("mobile"),
                }
            )
        else:
            return CustomResponse().errorResponse(data={}, description="Invalid Mobile Number")

class Login(APIView):

    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data
        store = request.store
        mobile = data.get("mobile")
        otp = data.get("otp")
        user = User.objects.filter(mobile=mobile,
                                   user_role__contains=["ADMIN"],
                                   store=store).first()
        if user:
            otp_obj = UserOTP.objects.filter(
                    store=request.store,
                    mobile=mobile,
                    otp=otp,
                    is_used=False
                ).order_by("-expires_at").first()
            if not otp_obj:
                return CustomResponse().errorResponse(
                    description="Invalid OTP",
                )

            if timezone.now() > otp_obj.expires_at:
                return CustomResponse().errorResponse(
                    description="OTP has expired",
                )
            # Mark OTP as used
            otp_obj.is_used = True
            otp_obj.save(update_fields=["is_used"])
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)
            refresh_token = str(refresh)
            UserSession.objects.create(
                user=user,
                store=request.store,
                session_token=access,
                refresh_token=refresh_token,
                device_id=request.data.get("device_id"),
                device_type=request.client_type,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
                expires_at=timezone.now() + timedelta(hours=24 * 7)
            )
            return CustomResponse().successResponse(
                description="OTP verified successfully",
                data={
                    "access": access,
                    "refresh": refresh_token,
                    "user": {
                        "id": str(user.id),
                        "mobile": user.mobile,
                        "username": user.username,
                        "referral_code": user.referral_code,
                        "device_id": user.device_id,
                        "store_id": user.store.id
                    }
                }
            )
        else:
            return CustomResponse().errorResponse(data={}, description="Invalid Mobile Number")


class ProductAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        data = request.data
        store = request.store

        required_fields = [
            "sku",
            "name",
            "mrp",
            "selling_price",
            "current_stock"
        ]

        for field in required_fields:
            if data.get(field) in [None, ""]:
                return CustomResponse.errorResponse(
                    description=f"{field} is required"
                )

        sku = data["sku"].strip()

        # SKU uniqueness
        if Product.objects.filter(sku=sku).exists():
            return CustomResponse.errorResponse(
                description="SKU already exists"
            )

        # GST calculation (optional)
        gst_percentage = data.get("gst_percentage")
        gst_amount = data.get("gst_amount")
        product=Product.objects.create(
            store=store,
            sku=sku,
            name=data["name"].strip(),
            size=data.get("size"),
            colour=data.get("colour"),
            mrp=data["mrp"],
            selling_price=data["selling_price"],
            gst_percentage=gst_percentage,
            gst_amount=gst_amount,
            current_stock=data["current_stock"],
            is_active=data.get("is_active", True),
            created_by=request.user.mobile
        )
        # 2️⃣ Attach media (optional)
        media_list = data.get("media", [])

        for media in media_list:
            if not media.get("url") or not media.get("media_type"):
                continue  # skip invalid entries

            ProductMedia.objects.create(
                product=product,
                url=media["url"],
                media_type=media["media_type"],
                position=media.get("position", 0),
                created_by=request.user.mobile
            )
        return CustomResponse.successResponse(
            data={},
            description="Product created successfully"
        )


    def get(self, request):
        store = request.store

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        page_size = min(page_size, 100)

        offset = (page - 1) * page_size

        queryset = Product.objects.filter(
            store=store,
            is_active=True
        ).order_by("-created_at")

        total_count = queryset.count()
        products = queryset[offset: offset + page_size]

        data = []
        for p in products:
            data.append({
                "id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "size": p.size,
                "colour": p.colour,
                "mrp": p.mrp,
                "selling_price": p.selling_price,
                "stock": p.current_stock,
                "created_at": p.created_at
            })

        return CustomResponse.successResponse(
            data=data,
            total=total_count,
            description="Products fetched successfully"
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

    @transaction.atomic
    def post(self, request):
        data = request.data
        store = request.store

        if not data.get("default_product_id"):
            return CustomResponse.errorResponse(
                description="default_product_id is required"
            )

        if not data.get("product_name"):
            return CustomResponse.errorResponse(
                description="product_name is required"
            )

        default_product_id = data["default_product_id"]
        product_ids = data.get("product_ids", [])

        # If product_ids not provided or empty → fallback
        if not product_ids:
            product_ids = [default_product_id]

        # If provided, default must be included
        if default_product_id not in product_ids:
            return CustomResponse.errorResponse(
                description="default_product_id must be part of product_ids"
            )

        # Fetch products
        products = Product.objects.filter(
            id__in=product_ids,
            store=store,
            is_active=True
        )

        if products.count() != len(product_ids):
            return CustomResponse.errorResponse(
                description="Invalid product_ids provided"
            )

        default_product = products.get(id=default_product_id)

        # Create ProductVariant
        variant = ProductVariant.objects.create(
            store=store,
            default_product=default_product,
            product_name=data["product_name"].strip(),
            product_tag_line=data.get("product_tag_line"),
            description=data.get("description"),
            highlights=data.get("highlights", []),
            gender=data.get("gender"),
            is_active=True,
            created_by=request.user.mobile
        )

        # Attach products
        variant.products.set(products)
        # 6️⃣ Attach categories (optional)
        category_ids = data.get("category_ids", [])
        if category_ids:
            categories = Category.objects.filter(
                id__in=category_ids,
                store=store,
                is_active=True
            )
            variant.categories.set(categories)

        # 7️⃣ Attach tags (optional)
        tag_ids = data.get("tag_ids", [])
        if tag_ids:
            tags = Tag.objects.filter(
                id__in=tag_ids,
                store=store,
                is_active=True
            )
            variant.tags.set(tags)

        return CustomResponse.successResponse(
            data={"product_variant_id": str(variant.id)},
            description="Product variant created successfully"
        )

    def get(self, request):
        store = request.store
        params = request.query_params

        # 1️⃣ Pagination
        try:
            page = int(params.get("page", 1))
            page_size = int(params.get("page_size", 20))
        except ValueError:
            return CustomResponse.errorResponse(
                description="Invalid pagination parameters"
            )

        if page < 1:
            page = 1
        page_size = min(max(page_size, 1), 100)

        offset = (page - 1) * page_size
        limit = offset + page_size

        # 2️⃣ Base queryset
        queryset = ProductVariant.objects.filter(
            store=store,
            is_active=True
        )

        # 3️⃣ Optional filters
        category_id = params.get("category_id")
        if category_id:
            queryset = queryset.filter(categories__id=category_id)

        tag_id = params.get("tag_id")
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)

        gender = params.get("gender")
        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(product_name__icontains=search) |
                Q(product_tag_line__icontains=search)
            )

        # 4️⃣ Optimize relations
        queryset = queryset.select_related(
            "default_product"
        ).prefetch_related(
            "products",
            "categories",
            "tags"
        ).distinct().order_by("-created_at")

        total_count = queryset.count()
        variants = queryset[offset:limit]

        # 5️⃣ Build response
        results = []
        for v in variants:
            results.append({
                "id": str(v.id),
                "product_name": v.product_name,
                "product_tag_line": v.product_tag_line,
                "gender": v.gender,
                "is_active": v.is_active,

                "default_product": {
                    "id": str(v.default_product.id),
                    "sku": v.default_product.sku,
                    "price": v.default_product.selling_price,
                    "stock": v.default_product.current_stock
                },

                "products_count": v.products.count(),

                "categories": [
                    {
                        "id": str(c.id),
                        "name": c.name
                    } for c in v.categories.all()
                ],

                "tags": [
                    {
                        "id": str(t.id),
                        "name": t.name
                    } for t in v.tags.all()
                ],

                "created_at": v.created_at
            })
        return CustomResponse().successResponse(data=results)



class CategoriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        store = request.store

        # 1. Required fields
        required_fields = ["name", "slug", "icon"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(
                    description=f"{field} is required"
                )

        name = data.get("name").strip()
        icon = data.get("icon")
        slug = data.get("slug").strip().lower()
        parent_id = data.get("parent_id")

        # 2. Unique slug per store
        if Category.objects.filter(store=store, slug=slug).exists():
            return CustomResponse.errorResponse(
                description="Category with this slug already exists"
            )

        # 3. Parent validation (optional)
        parent = None
        if parent_id:
            try:
                parent = Category.objects.get(
                    id=parent_id,
                    store=store,
                    is_active=True
                )
            except ObjectDoesNotExist:
                return CustomResponse.errorResponse(
                    description="Invalid parent category"
                )

        # 4. Create category
        Category.objects.create(
            store=store,
            name=name,
            slug=slug,
            parent=parent,
            icon=icon,
            is_active=data.get("is_active", True),
            created_by=request.user.mobile
        )

        return CustomResponse.successResponse(
            data={},
            description="Category created successfully"
        )

    def get(self, request):
        store = request.store
        # Pagination params
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
        except ValueError:
            return CustomResponse.errorResponse(
                description="Invalid pagination parameters"
            )
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        elif page_size > 100:
            page_size = 100
        offset = (page - 1) * page_size
        limit = offset + page_size
        queryset = Category.objects.filter(
            store=store,
        ).select_related("parent").order_by("name")
        total_count = queryset.count()
        categories = queryset[offset:limit]
        data = []
        for cat in categories:
            data.append({
                "id": str(cat.id),
                "name": cat.name,
                "icon":cat.icon,
                "search_tags": cat.search_tags,
                "is_active": cat.is_active,
                "slug": cat.slug,
                "parent_id": str(cat.parent_id) if cat.parent_id else None,
                "parent_name": cat.parent.name if cat.parent else None,
                "created_at": cat.created_at
            })
        return CustomResponse.successResponse(
            data=data,
            total=total_count,
        )

    def put(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="category id required")

        category = Category.objects.filter(id=id).first()
        if not category:
            return CustomResponse.errorResponse(description="category not found")
        for field in [
            "name","icon","search_tags","is_active", "slug"
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
    permission_classes = [AllowAny]

    # ---------------- CREATE STORE ----------------
    def post(self, request):
        data = request.data
        required_fields = ["name", "mobile", "address", "logo"]
        clients = request.data.get("clients")
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(
                    description=f"{field} is required"
                )
        if Store.objects.filter(mobile=data["mobile"]).exists():
            return CustomResponse.errorResponse(description="Store with this mobile already exists")

        try:
            store = Store.objects.create(
                name=data.get("name"),
                mobile=data.get("mobile"),
                address=data.get("address"),
                logo=data.get("logo"),
                created_by="SUPERADMIN"
            )
            User.objects.create(
                mobile=store.mobile,
                store=store,
                user_role=["ADMIN"],
                username=store.mobile
            )
            for item in clients:
                store_client = StoreClient()
                store_client.store = store
                store_client.identifier = item["identifier"]
                store_client.client_type = item["client_type"]
                store_client.is_active = True
                store_client.save()

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
                "status_counts": status_counts,
                "revenue": {
                    "total_amount": revenue["total_amount"] or 0,
                    "paid_online": revenue["paid_online"] or 0,
                    "cash_on_delivery": revenue["cash_on_delivery"] or 0,
                    "wallet_paid": revenue["wallet_paid"] or 0,
                }
            }

            return CustomResponse().successResponse(
                description="Order statistics fetched successfully",
                data=response_data,
                total=len(response_data)
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                description=str(e)
            )


class AbandonedOrderListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            store = request.store
            from_date = request.query_params.get("from_date")
            to_date = request.query_params.get("to_date")

            # -------- Pagination --------
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))

            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 10

            offset = (page - 1) * page_size

            # -------- Orders (Cancelled + Failed) --------
            queryset = Order.objects.filter(
                store_id=store.id,
                status__in=[OrderStatus.CANCELLED, OrderStatus.FAILED]
            ).order_by("-created_at")

            # -------- Date Filters --------
            if from_date:
                queryset = queryset.filter(created_at__date__gte=from_date)

            if to_date:
                queryset = queryset.filter(created_at__date__lte=to_date)

            orders = list(
                queryset[offset: offset + page_size].values(
                    "order_id",
                    "user_id",
                    "amount",
                    "status",
                    "created_at",
                )
            )

            if not orders:
                return CustomResponse().successResponse(
                    description="Cancelled and failed orders fetched successfully",
                    data=[],
                    total=0
                )

            # -------- Fetch Users --------
            user_ids = {o["user_id"] for o in orders}

            users = User.objects.filter(id__in=user_ids).values(
                "id", "username", "mobile", "email"
            )

            user_map = {
                u["id"]: {
                    "username": u["username"],
                    "mobile": u["mobile"],
                    "email": u["email"],
                }
                for u in users
            }

            # -------- Fetch Order Products --------
            order_ids = [o["order_id"] for o in orders]

            order_products = OrderProducts.objects.filter(
                store_id=store.id,
                order_id__in=order_ids
            ).values(
                "order_id",
                "product_id",
                "sku",
                "qty",
                "mrp",
                "selling_price",
                "Apportioned_discount",
                "Apportioned_wallet",
                "Apportioned_online",
                "Apportioned_gst",
                "rating",
                "review",
            )

            # -------- Fetch Product Names --------
            product_ids = {op["product_id"] for op in order_products}

            products = Product.objects.filter(
                id__in=product_ids
            ).values("id", "name")

            product_map = {
                p["id"]: p["name"]
                for p in products
            }

            # -------- Group Products by Order --------
            products_by_order = {}
            for op in order_products:
                product_amount = op["qty"] * op["selling_price"]

                products_by_order.setdefault(op["order_id"], []).append({
                    "product_id": op["product_id"],
                    "product_name": product_map.get(op["product_id"]),
                    "qty": op["qty"],
                    "mrp": op["mrp"],
                    "selling_price": op["selling_price"],
                    "amount": product_amount,
                    # "apportioned_discount": op["Apportioned_discount"],
                    # "apportioned_wallet": op["Apportioned_wallet"],
                    # "apportioned_online": op["Apportioned_online"],
                    # "apportioned_gst": op["Apportioned_gst"],
                    # "rating": op["rating"],
                    # "review": op["review"],
                })

            # -------- Attach User + Products to Orders --------
            for order in orders:
                user_info = user_map.get(order["user_id"], {})

                order["username"] = user_info.get("username")
                order["mobile"] = user_info.get("mobile")
                order["email"] = user_info.get("email")
                order["products"] = products_by_order.get(order["order_id"], [])

            return CustomResponse().successResponse(
                description="Cancelled and failed orders fetched successfully",
                data=orders,
                total=len(orders)
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

            # -------- Pagination --------
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))

            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 10

            offset = (page - 1) * page_size

            # -------- Base Query --------
            base_qs = Cart.objects.filter(store_id=store.id)

            total_records = base_qs.count()

            carts = list(
                base_qs[offset: offset + page_size].values(
                    "id",
                    "user_id",
                    "product_id",
                    "quantity"
                )
            )

            if not carts:
                return CustomResponse().successResponse(
                    description="Cart records fetched successfully",
                    data=[],
                    total=total_records
                )

            # -------- Fetch Users --------
            user_ids = {cart["user_id"] for cart in carts}

            users = User.objects.filter(id__in=user_ids).values(
                "id", "username", "mobile", "email"
            )

            user_map = {
                user["id"]: {
                    "username": user["username"],
                    "mobile": user["mobile"],
                    "email": user["email"],
                }
                for user in users
            }

            # -------- Fetch Products --------
            product_ids = {cart["product_id"] for cart in carts}

            products = Product.objects.filter(id__in=product_ids).values(
                "id", "name"
            )

            product_map = {
                product["id"]: product["name"]
                for product in products
            }

            # -------- Attach User & Product Info --------
            for cart in carts:
                user_info = user_map.get(cart["user_id"], {})

                cart["username"] = user_info.get("username")
                cart["mobile"] = user_info.get("mobile")
                cart["email"] = user_info.get("email")
                cart["product_name"] = product_map.get(cart["product_id"])

            return CustomResponse().successResponse(
                description="Cart records fetched successfully",
                data=carts,
                total=total_records
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

            # -------- Pagination --------
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))

            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 10

            offset = (page - 1) * page_size

            # -------- Orders --------
            orders = list(
                Order.objects.filter(store_id=store.id)
                .order_by("-created_at")[offset: offset + page_size]
                .values(
                    "order_id",
                    "user_id",
                    "amount",
                    "status",
                    "created_at",
                    "paid_online",
                    "cash_on_delivery",
                    "wallet_paid",
                )
            )

            if not orders:
                return CustomResponse().successResponse(
                    description="Orders fetched successfully",
                    data=[]
                )

            # -------- Users --------
            user_ids = [o["user_id"] for o in orders]

            users = User.objects.filter(id__in=user_ids).values(
                "id", "username"
            )

            user_map = {u["id"]: u["username"] for u in users}

            # -------- Items = number of products --------
            order_ids = [o["order_id"] for o in orders]

            items_count_map = {
                row["order_id"]: row["product_count"]
                for row in OrderProducts.objects.filter(
                    store_id=store.id,
                    order_id__in=order_ids
                )
                .values("order_id")
                .annotate(product_count=Count("product_id", distinct=True))
            }

            # -------- Final Response --------
            result = []
            for order in orders:
                payment_status = (
                    "Paid"
                    if (
                        order["paid_online"] > 0
                        or order["cash_on_delivery"] > 0
                        or order["wallet_paid"] > 0
                    )
                    else "Unpaid"
                )

                result.append({
                    "order_id": order["order_id"],
                    "created_at": order["created_at"],
                    "customer_name": user_map.get(order["user_id"]),
                    "total": order["amount"],
                    "payment_status": payment_status,
                    "status": order["status"],
                    "items": items_count_map.get(order["order_id"], 0),
                })

            return CustomResponse().successResponse(
                description="Orders fetched successfully",
                data=result,
                total=len(result)
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                description=str(e)
            )

