from datetime import timedelta
from decimal import Decimal
from tokenize import Double
from unicodedata import category
from django.utils.timezone import make_aware
from datetime import datetime

from django.core.files.storage import default_storage
from django.db.models import Q, F

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db import IntegrityError
from django.db.models.aggregates import Avg
from django.utils.timezone import now
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Sum
from django.core.files.storage import default_storage

from rest_framework.permissions import IsAuthenticated, AllowAny
from urllib3 import request

from config import settings
from django.conf import settings

from config.settings.common import DEBUG
from db.models import Category, Product, Banner, Inventory, PinCode, Store, WebBanner, \
    FlashSaleBanner, Order, User, Cart, OrderProducts, UserOTP, StoreClient, UserSession, ProductMedia, Tag, \
    OrderTimeLines, Coupons, CouponProduct, CouponCategory, CouponTag, AddressMaster
from db.models.user import AppVersionConfig
from enums.store import InventoryType, OrderStatus
from mixins.drf_views import CustomResponse
from rest_framework_simplejwt.tokens import RefreshToken

from utils.invoice_generator import generate_shipping_invoice
from utils.store import generate_lsin, generate_order_number, BO_STATUS_FLOW
from utils.user import generate_otp, send_sms_to_mobile, send_otp_email, generate_username, generate_referral_code
from django.db.models import Sum, F, DecimalField, ExpressionWrapper



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
                send_sms_to_mobile(otp, data.get("mobile"), store, store.sms_otp_template_id)
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



class EmailSendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        store = request.store

        if not email:
            return CustomResponse().errorResponse(
                description="Email is required"
            )

        # ADMIN CHECK ONLY
        user = User.objects.filter(
            email=email,
            user_role__contains=["ADMIN"],
            store=store
        ).first()

        if not user:
            return CustomResponse().errorResponse(
                description="Invalid email or access denied"
            )

        # Only ADMIN reaches here
        otp = generate_otp()

        if settings.DEBUG:
            otp = 1234
        else:
            send_otp_email(email, otp)


        expires_at = timezone.now() + timedelta(minutes=15)

        # Invalidate previous OTPs
        UserOTP.objects.filter(
            store=store,
            email=email,
            is_used=False
        ).update(is_used=True)

        # Save new OTP
        UserOTP.objects.create(
            store=store,
            email=email,
            otp=otp,
            expires_at=expires_at
        )

        return CustomResponse().successResponse(
            description="OTP sent successfully",
            data={
                "email": email
            }
        )




class EmailVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        device_id = request.data.get("device_id")
        store = request.store

        if not email or not otp:
            return CustomResponse().errorResponse(
                description="Email and OTP are required"
            )

        otp_obj = (
            UserOTP.objects
            .filter(
                store=store,
                email=email,
                otp=otp,
                is_used=False
            )
            .order_by("-expires_at")
            .first()
        )

        if not otp_obj:
            return CustomResponse().errorResponse(description="Invalid OTP")

        if timezone.now() > otp_obj.expires_at:
            return CustomResponse().errorResponse(description="OTP has expired")

        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

        #  Correct user handling
        user = User.objects.filter(email=email, store=store).first()
        is_new_user = False




        # Ensure required fields
        if not user.username:
            user.username = generate_username(user)

        if not user.referral_code:
            user.referral_code = generate_referral_code()

        if device_id and user.device_id != device_id:
            user.device_id = device_id

        user.last_login = timezone.now()
        user.save()

        # Tokens
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)

        UserSession.objects.create(
            user=user,
            store=store,
            session_token=access,
            refresh_token=refresh_token,
            device_id=device_id,
            device_type=request.client_type,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT"),
            expires_at=timezone.now() + timedelta(days=7)
        )

        return CustomResponse().successResponse(
            description="OTP verified successfully",
            data={
                "access": access,
                "refresh": refresh_token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "referral_code": user.referral_code,
                    "device_id": user.device_id,
                    "store_id": str(store.id)
                }
            }
        )

class UsersAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        store = request.store
        users_qs = User.objects.filter(
                store=store
            ).values()[:20]
        return CustomResponse().successResponse(data=users_qs)


class CreateAppVersionConfigAPI(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        os = request.data.get("os")
        min_version = request.data.get("min_supported_version")
        latest_version = request.data.get("latest_version")

        if not all([os, min_version, latest_version]):
            return CustomResponse().successResponse(
                data={}, description="Missing required fields"
            )
        # Check if active record already exists
        if AppVersionConfig.objects.filter(os=os, is_active=True).exists():
            return CustomResponse().successResponse(
                data={}, description=f"Active config already exists for {os}"
            )

        config = AppVersionConfig.objects.create(
            os=os,
            min_supported_version=min_version,
            latest_version=latest_version,
            force_update=request.data.get("force_update", False),
            update_title=request.data.get("update_title"),
            update_message=request.data.get("update_message"),
            is_active=True
        )
        return CustomResponse().successResponse(data={}, description="App version config created")

    def put(self, request, config_id):
        try:
            config = AppVersionConfig.objects.get(id=config_id, is_active=True)
        except AppVersionConfig.DoesNotExist:
            return CustomResponse().successResponse(
                data={}, description="Active config not found"
            )

        # Update allowed fields
        for field in [
            "min_supported_version",
            "latest_version",
            "force_update",
            "update_title",
            "update_message",
        ]:
            if field in request.data:
                setattr(config, field, request.data[field])

        config.save()
        return CustomResponse().successResponse(data={}, description="App version config updated")


class UserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        mobile = request.query_params.get("mobile")
        store = request.store
        if not mobile or len(mobile) < 3:
            return CustomResponse().errorResponse(data={}, description="Enter at least 3 digits of mobile number")
        users_qs = User.objects.filter(
                store=store,
                mobile__startswith=mobile
            ).first()
        address = AddressMaster.objects.filter(store_id=store.id,
                                               mobile=users_qs.mobile,
                                               is_default=True).values().first()




        return CustomResponse().successResponse(data={
            "username": users_qs.username,
            "name": users_qs.name,
            "mobile": users_qs.mobile,
            "email": users_qs.email,
            "address": address,
        })


class UserAddress(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        mobile = request.query_params.get("mobile")
        store = request.store
        address = AddressMaster.objects.filter(store_id=store.id, mobile=mobile, is_default=True).values()
        if address:
            return CustomResponse().successResponse(data=address.first())
        else:
            return CustomResponse().errorResponse(data={}, description="No Address found for this user")





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
            "group_code",
            "description",
            "selling_price",
            "current_stock"
        ]

        for field in required_fields:
            if data.get(field) in [None, ""]:
                return CustomResponse.errorResponse(
                    description=f"{field} is required"
                )
        if Decimal(data["selling_price"]) > Decimal(data["mrp"]):
            return CustomResponse.errorResponse(
                "Selling price cannot be greater than MRP"
            )

        sku = data["sku"].strip()
        if Product.objects.filter(store=store, sku=sku).exists():
            return CustomResponse.errorResponse(
                description="SKU already exists"
            )
        selling_price = Decimal(data["selling_price"])
        gst_percentage = Decimal(data.get("gst_percentage", 0))
        if gst_percentage > 0:
            product_cost = (selling_price * 100) / (100 + gst_percentage)
            gst_amount = selling_price - product_cost
        else:
            gst_amount = Decimal("0.00")
        product=Product.objects.create(
            store=store,
            sku=sku,
            lsin=generate_lsin(store, "SRU"),
            name=data["name"].strip(),
            size=data.get("size"),
            colour=data.get("colour"),
            mrp=data["mrp"],
            group_code=data["group_code"],
            selling_price=data["selling_price"],
            description=data["description"],
            gst_percentage=gst_percentage,
            gst_amount=gst_amount,
            current_stock=data["current_stock"],
            is_active=data.get("is_active", True),
            created_by=request.user.mobile
        )
        # ---------- Categories ----------
        category_ids = data.get("categories", [])
        if category_ids:
            categories = Category.objects.filter(
                id__in=category_ids,
                store=store,
                is_active=True
            )
            product.categories.set(categories)

        # ---------- Tags ----------
        tag_ids = data.get("tags", [])
        if tag_ids:
            tags = Tag.objects.filter(
                id__in=tag_ids,
                store=store,
                is_active=True
            )
            product.tags.set(tags)

        media_list = data.get("media", [])

        for media in media_list:
            if not media.get("url") or not media.get("media_type"):
                continue

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

        # ---------- Query params ----------
        search = request.query_params.get("search")
        category_id = request.query_params.get("category")
        tags = request.query_params.get("tags")  # comma-separated
        lsin = request.query_params.get("lsin")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        # ---------- Base queryset ----------
        queryset = Product.objects.filter(
            store=store
        ).prefetch_related(
            "categories",
            "tags",
            "media"
        ).order_by("-created_at")

        # ---------- LSIN filter ----------
        if lsin:
            queryset = queryset.filter(lsin__iexact=lsin)

        # ---------- Search ----------
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(lsin__icontains=search) |
                Q(search_tags__icontains=search)
            )

        # ---------- Category filter ----------
        if category_id:
            queryset = queryset.filter(
                categories__id=category_id
            )

        # ---------- Tags filter ----------
        if tags:
            tag_ids = [t.strip() for t in tags.split(",") if t.strip()]
            queryset = queryset.filter(
                tags__id__in=tag_ids
            )

        queryset = queryset.distinct()

        # ---------- Pagination ----------
        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]

        # ---------- Response ----------
        data = []

        for product in queryset:
            data.append({
                "id": str(product.id),
                "lsin": product.lsin,
                "group_code": product.group_code,
                "sku": product.sku,

                "name": product.name,
                "colour": product.colour,
                "size": product.size,
                "gst_amount": product.gst_amount,
                "gst_percentage": product.gst_percentage,
                "description": product.description,

                "mrp": str(product.mrp),
                "selling_price": str(product.selling_price),
                "current_stock": product.current_stock,

                "categories": [
                    {"id": str(c.id), "name": c.name}
                    for c in product.categories.all()
                ],

                "tags": [
                    {"id": str(t.id), "name": t.name}
                    for t in product.tags.all()
                ],
                "media": [
                    {
                        "id": str(m.id),
                        "url": m.url,
                        "type": m.media_type,
                        "position": m.position
                    } for m in product.media.all()
                ],
                "search_tags": product.search_tags,
                "is_active": product.is_active,
                "created_at": product.created_at
            })

        return CustomResponse.successResponse(
            data=data,
            total=total,
            description="Products fetched successfully"
        )


    @transaction.atomic
    def put(self, request, id=None):
        store = request.store
        data = request.data

        if not id:
            return CustomResponse.errorResponse(
                description="Product id is required"
            )

        try:
            product = Product.objects.get(
                id=id,
                store=store,
                is_active=True
            )
        except Product.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Product not found"
            )

        # ------------------ Update product fields ------------------
        updatable_fields = [
            "name", "size", "colour", "mrp",
            "selling_price", "gst_percentage", "description",
            "gst_amount", "current_stock", "is_active"
        ]

        for field in updatable_fields:
            if field in data:
                setattr(product, field, data.get(field))

        product.updated_by = request.user.mobile
        product.save()

        # ================== UPDATE CATEGORIES ==================
        if "categories" in data:
            category_ids = data.get("categories", [])

            categories = Category.objects.filter(
                id__in=category_ids,
                store=store,
                is_active=True
            )

            product.categories.set(categories)

        # ================== UPDATE TAGS ==================
        if "tags" in data:
            tag_ids = data.get("tags", [])

            tags = Tag.objects.filter(
                id__in=tag_ids,
                store=store,
                is_active=True
            )

            product.tags.set(tags)

        # ================== DELETE MEDIA (DB + S3) ==================
        media_to_delete = data.get("media_to_delete", [])

        if media_to_delete:
            media_qs = ProductMedia.objects.filter(
                url__in=media_to_delete,
                product=product
            )

            for media in media_qs:
                #  delete from S3 using stored path
                if media.url and default_storage.exists(media.url):
                    default_storage.delete(media.url)

                media.delete()

        # ================== ADD NEW MEDIA ==================
        media_to_add = data.get("media_to_add", [])

        for media in media_to_add:
            if not all(k in media for k in ("url", "position", "media_type")):
                continue

            ProductMedia.objects.create(
                product=product,
                url=media["url"],                 #  from request
                media_type=media["media_type"],
                position=media.get("position", 0),
                created_by=request.user.mobile
            )

        return CustomResponse.successResponse(
            data={},
            description="Product updated successfully"
        )




    @transaction.atomic
    def delete(self, request, id=None):
        store = request.store

        if not id:
            return CustomResponse.errorResponse(
                description="Product id is required"
            )

        try:
            product = Product.objects.get(
                id=id,
                store=store,
                is_active=True
            )
        except Product.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Product not found"
            )

        # Soft delete
        product.is_active = False
        product.updated_by = request.user.mobile
        product.save(update_fields=["is_active", "updated_by"])

        return CustomResponse.successResponse(
            data={},
            description="Product deleted successfully"
        )





# class DisplayProductAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     @transaction.atomic
#     def post(self, request):
#         data = request.data
#         store = request.store
#
#         if not data.get("default_product_id"):
#             return CustomResponse.errorResponse(
#                 description="default_product_id is required"
#             )
#
#         if not data.get("display_name"):
#             return CustomResponse.errorResponse(
#                 description="display_name is required"
#             )
#
#         default_product_id = data["default_product_id"]
#         product_ids = data.get("product_ids", [])
#         products = Product.objects.filter(
#             id__in=product_ids,
#             store=store,
#             is_active=True
#         )
#
#         if products.count() != len(product_ids):
#             return CustomResponse.errorResponse(
#                 description="Invalid product_ids provided"
#             )
#
#         default_product = Product.objects.filter(
#             id=default_product_id,
#             store=store,
#             is_active=True
#         ).first()
#         if not default_product:
#             return CustomResponse.errorResponse(
#                 description="Invalid product_id provided"
#             )
#         lsin = generate_lsin(store, "SRU")
#
#         # Create ProductVariant
#         variant = ProductVariant.objects.create(
#             store=store,
#             default_product=default_product,
#             display_name=data["display_name"].strip(),
#             description=data.get("description"),
#             highlights=data.get("highlights", ""),
#             gender=data.get("gender"),
#             is_active=True,
#             lsin=lsin,
#             search_tags=data.get("search_tags", []),
#             created_by=request.user.mobile
#         )
#
#         # Attach products
#         variant.products.set(products)
#         # 6️⃣ Attach categories (optional)
#         category_ids = data.get("category_ids", [])
#         if category_ids:
#             categories = Category.objects.filter(
#                 id__in=category_ids,
#                 store=store,
#                 is_active=True
#             )
#             variant.categories.set(categories)
#
#         # 7️⃣ Attach tags (optional)
#         tag_ids = data.get("tag_ids", [])
#         if tag_ids:
#             tags = Tag.objects.filter(
#                 id__in=tag_ids,
#                 store=store,
#                 is_active=True
#             )
#             variant.tags.set(tags)
#
#         return CustomResponse.successResponse(
#             data={"product_variant_id": str(variant.id)},
#             description="Product variant created successfully"
#         )
#
#     def get(self, request):
#         store = request.store
#         params = request.query_params
#
#         # 1️⃣ Pagination
#         try:
#             page = int(params.get("page", 1))
#             page_size = int(params.get("page_size", 20))
#         except ValueError:
#             return CustomResponse.errorResponse(
#                 description="Invalid pagination parameters"
#             )
#
#         if page < 1:
#             page = 1
#         page_size = min(max(page_size, 1), 100)
#
#         offset = (page - 1) * page_size
#         limit = offset + page_size
#
#         # 2️⃣ Base queryset
#         queryset = ProductVariant.objects.filter(
#             store=store,
#             is_active=True
#         ).select_related(
#             "default_product"
#         ).prefetch_related(
#             "products__media",  # 👈 REQUIRED
#             "categories",
#             "tags"
#         ).distinct().order_by("-created_at")
#
#         # 3️⃣ Optional filters
#         category_id = params.get("category_id")
#         if category_id:
#             queryset = queryset.filter(categories__id=category_id)
#
#         tag_id = params.get("tag_id")
#         if tag_id:
#             queryset = queryset.filter(tags__id=tag_id)
#
#         gender = params.get("gender")
#         if gender:
#             queryset = queryset.filter(gender__iexact=gender)
#
#         search = params.get("search")
#         if search:
#             queryset = queryset.filter(
#                 Q(product_name__icontains=search) |
#                 Q(product_tag_line__icontains=search)
#             )
#
#
#
#         total_count = queryset.count()
#         variants = queryset[offset:limit]
#
#         # 5️⃣ Build response
#         results = []
#
#         for v in variants:
#
#             # 🔹 Build default product block
#             dp = v.default_product
#             default_product_data = {
#                 "id": str(dp.id),
#                 "sku": dp.sku,
#                 "name": dp.name,
#                 "is_active": dp.is_active,
#                 "size": dp.size,
#                 "colour": dp.colour,
#                 "mrp": dp.mrp,
#                 "selling_price": dp.selling_price,
#                 "gst_percentage": dp.gst_percentage,
#                 "gst_amount": dp.gst_amount,
#                 "stock": dp.current_stock,
#                 "media": [m.url for m in dp.media.all()]
#             }
#
#             # 🔹 Build products list
#             products_data = []
#             for p in v.products.all():
#                 products_data.append({
#                 "id": str(p.id),
#                 "sku": p.sku,
#                 "name": p.name,
#                 "is_active": p.is_active,
#                 "size": p.size,
#                 "colour": p.colour,
#                 "mrp": p.mrp,
#                 "selling_price": p.selling_price,
#                 "gst_percentage": p.gst_percentage,
#                 "gst_amount": p.gst_amount,
#                 "stock": p.current_stock,
#                 "media": [m.url for m in p.media.all()]
#                 })
#
#             results.append({
#                 "id": str(v.id),
#                 "display_name": v.display_name,
#                 "description": v.description,
#                 "gender": v.gender,
#                 "is_active": v.is_active,
#                 "default_product": default_product_data,
#                 "products": products_data,
#                 "highlights": v.highlights,
#                 "search_tags": v.search_tags,
#                 "categories": [
#                     {
#                         "id": str(c.id),
#                         "name": c.name
#                     }
#                     for c in v.categories.all()
#                 ],
#                 "tags": [
#                     {
#                         "id": str(t.id),
#                         "name": t.name
#                     }
#                     for t in v.tags.all()
#                 ]
#             })
#
#         return CustomResponse().successResponse(data=results, total=total_count)
#     @transaction.atomic
#     def put(self, request, id=None):
#         store = request.store
#         data = request.data
#
#         if not id:
#             return CustomResponse.errorResponse(
#                 description="display product id is required"
#             )
#
#         # 1️⃣ Fetch variant (store-safe)
#         try:
#             variant = ProductVariant.objects.get(
#                 id=id,
#                 store=store,
#                 is_active=True
#             )
#         except ProductVariant.DoesNotExist:
#             return CustomResponse.errorResponse(
#                 description="Display product not found"
#             )
#
#         #  Update basic fields
#         for field in [
#             "display_name",
#             "description",
#             "highlights",
#             "gender",
#             "search_tags",
#             "is_active"
#         ]:
#             if field in data:
#                 setattr(variant, field, data.get(field))
#
#         #  Update default product
#         if "default_product_id" in data:
#             default_product_id = data.get("default_product_id")
#             if not default_product_id:
#                 return CustomResponse.errorResponse(
#                     description="default_product_id cannot be empty"
#                 )
#
#             default_product = Product.objects.filter(
#                 id=default_product_id,
#                 store=store,
#                 is_active=True
#             ).first()
#
#             if not default_product:
#                 return CustomResponse.errorResponse(
#                     description="Invalid default_product_id"
#                 )
#
#             variant.default_product = default_product
#
#         # 4️⃣ Update products (replace list)
#         if "product_ids" in data:
#             product_ids = data.get("product_ids", [])
#             products = Product.objects.filter(
#                 id__in=product_ids,
#                 store=store,
#                 is_active=True
#             )
#
#             if products.count() != len(product_ids):
#                 return CustomResponse.errorResponse(
#                     description="Invalid product_ids provided"
#                 )
#
#             variant.products.set(products)
#
#         # 5️⃣ Update categories
#         if "category_ids" in data:
#             category_ids = data.get("category_ids", [])
#             categories = Category.objects.filter(
#                 id__in=category_ids,
#                 store=store,
#                 is_active=True
#             )
#             variant.categories.set(categories)
#
#         # 6️⃣ Update tags
#         if "tag_ids" in data:
#             tag_ids = data.get("tag_ids", [])
#             tags = Tag.objects.filter(
#                 id__in=tag_ids,
#                 store=store,
#                 is_active=True
#             )
#             variant.tags.set(tags)
#
#         # 7️⃣ Audit
#         variant.updated_by = request.user.mobile
#         variant.save()
#
#         return CustomResponse.successResponse(
#             data={},
#             description="Display product updated successfully"
#         )
#     @transaction.atomic
#     def delete(self, request, id=None):
#         store = request.store
#
#         if not id:
#             return CustomResponse.errorResponse(
#                 description="display product id is required"
#             )
#
#         try:
#             variant = ProductVariant.objects.get(
#                 id=id,
#                 store=store,
#                 is_active=True
#             )
#         except ProductVariant.DoesNotExist:
#             return CustomResponse.errorResponse(
#                 description="Display product not found"
#             )
#
#         variant.is_active = False
#         variant.updated_by = request.user.mobile
#         variant.save(update_fields=["is_active", "updated_by"])
#
#         return CustomResponse.successResponse(
#             data={},
#             description="Display product deleted successfully"
#         )





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
    def put(self, request, id=None):
        store = request.store
        data = request.data

        if not id:
            return CustomResponse.errorResponse(
                description="Category id is required"
            )

        try:
            category = Category.objects.get(id=id, store=store)
        except Category.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Category not found"
            )

        if "name" in data:
            name = data.get("name")
            if not name:
                return CustomResponse.errorResponse(
                    description="name cannot be empty"
                )
            category.name = name.strip()

        if "slug" in data:
            slug = data.get("slug")
            if not slug:
                return CustomResponse.errorResponse(
                    description="slug cannot be empty"
                )

            slug = slug.strip().lower()

            if Category.objects.filter(
                    store=store,
                    slug=slug
            ).exclude(id=category.id).exists():
                return CustomResponse.errorResponse(
                    description="Category with this slug already exists"
                )

            category.slug = slug

        if "icon" in data:
            category.icon = data.get("icon")

        if "is_active" in data:
            category.is_active = bool(data.get("is_active"))

        if "parent_id" in data:
            parent_id = data.get("parent_id")

            if parent_id:
                try:
                    parent = Category.objects.get(
                        id=parent_id,
                        store=store,
                        is_active=True
                    )
                except Category.DoesNotExist:
                    return CustomResponse.errorResponse(
                        description="Invalid parent category"
                    )

                if parent.id == category.id:
                    return CustomResponse.errorResponse(
                        description="Category cannot be its own parent"
                    )

                category.parent = parent
            else:
                category.parent = None

        category.updated_by = request.user.mobile
        category.save()

        return CustomResponse.successResponse(
            data={},
            description="Category updated successfully"
        )
    def delete(self, request, id=None):
        store = request.store

        if not id:
            return CustomResponse.errorResponse(
                description="Category id is required"
            )

        try:
            category = Category.objects.get(
                id=id,
                store=store,
                is_active=True
            )
        except Category.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Category not found"
            )

        # Optional: prevent delete if category has children
        if Category.objects.filter(parent=category, is_active=True).exists():
            return CustomResponse.errorResponse(
                description="Cannot delete category with active subcategories"
            )

        category.is_active = False
        category.updated_by = request.user.mobile
        category.save()
        # category.delete()

        return CustomResponse.successResponse(
            data={},
            description="Category deleted successfully"
        )






class TagsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        store = request.store

        if not data.get("name"):
            return CustomResponse.errorResponse(
                description="name is required"
            )

        slug = data.get("slug") or data["name"].strip().lower().replace(" ", "-")

        if Tag.objects.filter(store=store, slug=slug).exists():
            return CustomResponse.errorResponse(
                description="Tag with this slug already exists"
            )

        if Tag.objects.filter(store=store, name=data["name"]).exists():
            return CustomResponse.errorResponse(
                description="Tag with this name already exists"
            )

        Tag.objects.create(
            store=store,
            name=data["name"].strip(),
            slug=slug,
            is_active=data.get("is_active", True),
            created_by=request.user.mobile
        )

        return CustomResponse.successResponse(
            data={},
            description="Tag created successfully"
        )

    def get(self, request):
        store = request.store
        params = request.query_params

        page = int(params.get("page", 1))
        page_size = min(int(params.get("page_size", 20)), 100)

        offset = (page - 1) * page_size

        queryset = Tag.objects.filter(
            store=store,
            is_active=True
        )

        total_count = queryset.count()
        tags = queryset.order_by("name")[offset:offset + page_size]

        data = [{
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "created_at": t.created_at
        } for t in tags]

        return CustomResponse.successResponse(
            data=data,
            total=total_count,
            description="Tags fetched successfully"
        )
    def put(self, request, id=None):
        store = request.store
        data = request.data

        if not id:
            return CustomResponse.errorResponse(
                description="Tag id is required"
            )

        # 1. Fetch tag (store-safe)
        try:
            tag = Tag.objects.get(id=id, store=store)
        except Tag.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Tag not found"
            )

        # 2. Name update
        if "name" in data:
            name = data.get("name")
            if not name:
                return CustomResponse.errorResponse(
                    description="name cannot be empty"
                )

            name = name.strip()

            # Unique name per store (exclude self)
            if Tag.objects.filter(
                    store=store,
                    name=name
            ).exclude(id=tag.id).exists():
                return CustomResponse.errorResponse(
                    description="Tag with this name already exists"
                )

            tag.name = name

            # Auto-update slug if slug not explicitly provided
            if "slug" not in data:
                slug = name.lower().replace(" ", "-")
                if Tag.objects.filter(
                        store=store,
                        slug=slug
                ).exclude(id=tag.id).exists():
                    return CustomResponse.errorResponse(
                        description="Tag slug conflict after name change"
                    )
                tag.slug = slug

        # 3. Slug update
        if "slug" in data:
            slug = data.get("slug")
            if not slug:
                return CustomResponse.errorResponse(
                    description="slug cannot be empty"
                )

            slug = slug.strip().lower()

            if Tag.objects.filter(
                    store=store,
                    slug=slug
            ).exclude(id=tag.id).exists():
                return CustomResponse.errorResponse(
                    description="Tag with this slug already exists"
                )

            tag.slug = slug

        # 4. is_active update
        if "is_active" in data:
            tag.is_active = bool(data.get("is_active"))

        # 5. Audit
        tag.updated_by = request.user.mobile
        tag.save()

        return CustomResponse.successResponse(
            data={},
            description="Tag updated successfully"
        )
    def delete(self, request, id=None):
        store = request.store

        if not id:
            return CustomResponse.errorResponse(
                description="Tag id is required"
            )

        try:
            tag = Tag.objects.get(
                id=id,
                store=store,
                is_active=True
            )
        except Tag.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Tag not found"
            )

        # Soft delete
        tag.is_active = False
        tag.updated_by = request.user.mobile
        tag.save(update_fields=["is_active", "updated_by"])

        return CustomResponse.successResponse(
            data={},
            description="Tag deleted successfully"
        )



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
                district = data.get("district"),
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








class StoreAPIView(APIView):
    permission_classes = [AllowAny]

    # ---------------- CREATE STORE ----------------
    def post(self, request):
        data = request.data
        required_fields = ["name", "mobile", "address", "logo","product_code"]
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
                created_by="SUPERADMIN",
                product_code = data.get("product_code")
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

        except IntegrityError as error:
            return CustomResponse.errorResponse(
                description=f"Database integrity error {error}"
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

    @transaction.atomic
    def post(self, request):
        data = request.data
        store = request.store

        required_fields = [
            "screen",
            "title",
            "description",
            "image",
            "priority",
            "action",
            "destination"
        ]

        for field in required_fields:
            if field not in data or data[field] in [None, ""]:
                return CustomResponse.errorResponse(
                    description=f"{field} is required"
                )

        try:
            priority = int(data["priority"])
        except ValueError:
            return CustomResponse.errorResponse(
                description="priority must be an integer"
            )

        screen = data["screen"]
        # ---------- Handle priority conflicts ----------
        WebBanner.objects.filter(
            store_id=store.id,
            screen=screen,
            priority__gte=priority
        ).update(
            priority=F("priority") + 1
        )

        # ---------- Create banner ----------
        banner = WebBanner.objects.create(
            store_id=store.id,
            screen=screen,
            title=data["title"],
            description=data["description"],
            image=data["image"],
            is_active=data.get("is_active", True),
            priority=priority,
            action=data["action"],
            destination=data["destination"],
            created_by=request.user.mobile
        )

        return CustomResponse.successResponse(
            data={"banner_id": str(banner.id)},
            description="Web banner created successfully"
        )
    def get(self, request):
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

    @transaction.atomic
    def put(self, request, id=None):
        if not id:
            return CustomResponse.errorResponse(
                description="web banner id required"
            )

        store = request.store
        data = request.data

        banner = WebBanner.objects.filter(
            id=id,
            store_id=store.id
        ).first()

        if not banner:
            return CustomResponse.errorResponse(
                description="web banner not found"
            )

        old_priority = banner.priority
        old_screen = banner.screen

        new_screen = data.get("screen", old_screen)
        new_priority = data.get("priority", old_priority)

        # ---------- Validate priority ----------
        try:
            new_priority = int(new_priority)
        except (TypeError, ValueError):
            return CustomResponse.errorResponse(
                description="priority must be an integer"
            )

        # ---------- Handle priority shift ----------
        if new_priority != old_priority or new_screen != old_screen:
            WebBanner.objects.filter(
                store_id=store.id,
                screen=new_screen,
                priority__gte=new_priority
            ).exclude(
                id=banner.id
            ).update(
                priority=F("priority") + 1
            )

            banner.priority = new_priority
            banner.screen = new_screen

        # ---------- Update other fields safely ----------
        updatable_fields = [
            "image",
            "is_active",
            "action",
            "destination",
            "title",
            "description",
        ]

        for field in updatable_fields:
            if field in data:
                setattr(banner, field, data[field])

        banner.save()

        return CustomResponse.successResponse(
            data={"banner_id": str(banner.id)},
            description="web banner updated successfully"
        )

    @transaction.atomic
    def delete(self, request, id=None):
        if not id:
            return CustomResponse.errorResponse(
                description="web banner id required"
            )

        store = request.store

        banner = WebBanner.objects.filter(
            id=id,
            store_id=store.id
        ).first()

        if not banner:
            return CustomResponse.errorResponse(
                description="web banner not found"
            )
        screen = banner.screen
        deleted_priority = banner.priority
        # ---------- Delete banner ----------
        banner.delete()
        # ---------- Rebalance priorities ----------
        WebBanner.objects.filter(
            store_id=store.id,
            screen=screen,
            priority__gt=deleted_priority
        ).update(
            priority=F("priority") - 1
        )
        return CustomResponse.successResponse(
            description="web banner deleted successfully",
            data={}
        )


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

            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            from_date = request.query_params.get("from_date")
            to_date = request.query_params.get("to_date")

            orders_qs = Order.objects.filter(
                store=store,
                status__in=[
                    OrderStatus.CANCELLED,
                    OrderStatus.FAILED
                ]
            ).select_related(
                "user"
            ).prefetch_related(
                "items__product__media"
            ).order_by("-created_at")

            # ---------- Date filters ----------
            if from_date:
                orders_qs = orders_qs.filter(created_at__date__gte=from_date)

            if to_date:
                orders_qs = orders_qs.filter(created_at__date__lte=to_date)

            total = orders_qs.count()
            offset = (page - 1) * page_size
            orders_qs = orders_qs[offset: offset + page_size]

            data = []

            for order in orders_qs:
                items = []

                for item in order.items.all():
                    product = item.product

                    # ---- primary image ----
                    image_url = None
                    for m in product.media.all():
                        if m.media_type == "image":
                            image_url = m.url
                            break

                    items.append({
                        "product_id": str(product.id),
                        "sku": item.sku,
                        "name": product.name,
                        "qty": item.qty,
                        "image": image_url,
                        "price": str(item.selling_price)
                    })

                data.append({
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "status": order.status,
                    "amount": str(order.amount),
                    "created_at": order.created_at,
                    "user": {
                        "id": str(order.user.id),
                        "name": order.user.name,
                        "mobile": order.user.mobile,
                        "email": order.user.email
                    },
                    "items": items
                })

            return CustomResponse.successResponse(
                data=data,
                total=total,
                description="Abandoned orders fetched successfully"
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

    STATUS_FILTER_MAP = {
        "ONGOING": [
            OrderStatus.INITIATED,
            OrderStatus.CREATED,
            OrderStatus.PACKED,
            OrderStatus.SHIPPED,
        ],
        "DELIVERED": [OrderStatus.DELIVERED],
        "CANCELLED": [
            OrderStatus.CANCELLED,
            OrderStatus.FAILED,
            OrderStatus.UNFULFILLED,
        ],
    }

    def get(self, request):
        store = request.store

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")

        queryset = Order.objects.filter(
            store=store
        ).select_related("user").order_by("-created_at")

        # ---- status filter ----
        if status_filter:
            status_filter = status_filter.upper()
            if status_filter not in self.STATUS_FILTER_MAP:
                return CustomResponse.errorResponse("Invalid status filter")

            queryset = queryset.filter(
                status__in=self.STATUS_FILTER_MAP[status_filter]
            )

        # ---- search by order number ----
        if search:
            queryset = queryset.filter(
                order_number__icontains=search
            )

        total = queryset.count()
        offset = (page - 1) * page_size
        orders = queryset[offset: offset + page_size]

        data = []
        for order in orders:
            data.append({
                "order_id": str(order.id),
                "order_number": order.order_number,
                "user_id": str(order.user.id),
                "user_name": order.user.name,
                "status": order.status,
                "amount": str(order.amount),
                "created_at": order.created_at,
                "item_count": order.items.count()
            })

        return CustomResponse.successResponse(
            data=data,
            total=total,
            description="Orders fetched successfully"
        )

    def post(self, request):
        store = request.store
        admin = request.user
        data = request.data

        user_id = data.get("user_id")
        products = data.get("products", [])
        address = data.get("address")

        if not user_id:
            return CustomResponse.errorResponse("user_id is required")

        if not products:
            return CustomResponse.errorResponse("products are required")

        if not address:
            return CustomResponse.errorResponse("address is required")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return CustomResponse.errorResponse("Invalid user_id")

        subtotal = Decimal("0.00")
        order_items = []

        with transaction.atomic():

            # ---------- Validate products ----------
            for item in products:
                product_id = item.get("product_id")
                qty = int(item.get("qty", 0))

                if qty <= 0:
                    return CustomResponse.errorResponse("Invalid quantity")

                try:
                    product = Product.objects.select_for_update().get(
                        id=product_id,
                        store=store,
                        is_active=True
                    )
                except Product.DoesNotExist:
                    return CustomResponse.errorResponse(
                        f"Invalid product {product_id}"
                    )

                if product.current_stock < qty:
                    return CustomResponse.errorResponse(
                        f"{product.name} out of stock"
                    )

                line_total = product.selling_price * qty
                subtotal += line_total

                order_items.append((product, qty))

            # ---------- Create Order ----------
            order_number = generate_order_number(store, "SRU")  # sequence-based

            order = Order.objects.create(
                store=store,
                user=user,
                order_number=order_number,
                address=address,
                coupon_discount=Decimal("0.00"),
                amount=subtotal,
                wallet_paid=Decimal("0.00"),
                paid_online=subtotal,
                status=OrderStatus.CREATED,
                created_by=admin.id
            )

            # ---------- Create OrderProducts ----------
            for product, qty in order_items:
                OrderProducts.objects.create(
                    order=order,
                    product=product,
                    sku=product.sku,
                    qty=qty,
                    mrp=product.mrp,
                    selling_price=product.selling_price,
                    apportioned_discount=Decimal("0.00"),
                    apportioned_wallet=Decimal("0.00"),
                    apportioned_online=Decimal("0.00"),
                    apportioned_gst=Decimal("0.00")
                )

                # Reduce stock immediately (admin confirmed)
                product.current_stock -= qty
                product.save(update_fields=["current_stock"])
            OrderTimeLines.objects.create(
                order=order,
                status=OrderStatus.INITIATED,
                remarks=data.get("remarks", "Order initiated")
            )

        return CustomResponse.successResponse(
            data={
                "order_id": str(order.id),
                "order_number": order.order_number,
                "amount": str(order.amount),
                "status": order.status
            },
            description="Order created successfully"
        )
    def put(self, request, id):
        order = Order.objects.filter(id=id).first()

        if not order:
            return CustomResponse().errorResponse(
                description="No order found with provided Id"
            )

        new_status = request.data.get("status")
        remarks = request.data.get("remarks")

        if not new_status:
            return CustomResponse().errorResponse(
                description="status is required"
            )

        current_status = order.status
        allowed_next = BO_STATUS_FLOW.get(current_status, [])

        if new_status not in allowed_next:
            return CustomResponse().errorResponse(
                data={
                    "message": "Invalid status transition",
                    "current_status": current_status,
                    "allowed_next": allowed_next
                },
                description="Invalid status transition",
            )

        # Detect first time becoming PACKED
        is_becoming_packed = (
                current_status != OrderStatus.PACKED
                and new_status == OrderStatus.PACKED
        )

        #  Require dimensions only when first time PACKED
        if is_becoming_packed:

            weight = request.data.get("weight")
            length = request.data.get("length")
            breadth = request.data.get("breadth")
            height = request.data.get("height")

            if not all([weight, length, breadth, height]):
                return CustomResponse().errorResponse(
                    description="Weight, length, breadth and height are required"
                )

            # Convert safely to Decimal
            order.weight = Decimal(weight)
            order.length = Decimal(length)
            order.breadth = Decimal(breadth)
            order.height = Decimal(height)

        #  Update status
        order.status = new_status
        order.save()

        #  Generate shipping slip only first time PACKED
        if is_becoming_packed and not order.shipping_slip:
            shipping_slip_path = generate_shipping_invoice(order)
            order.shipping_slip = shipping_slip_path
            order.save(update_fields=["shipping_slip"])

        # Timeline
        OrderTimeLines.objects.create(
            order=order,
            status=new_status,
            remarks=remarks
        )

        return CustomResponse.successResponse(
            data={},
            description="Order Updated successfully"
        )


    # def put(self, request, id):
    #     order = Order.objects.filter(
    #         id=id
    #     ).first()
    #     if not order:
    #         return CustomResponse().errorResponse(data={}, description="No order found with provided Id")
    #     new_status = request.data.get("status")
    #     remarks = request.data.get("remarks")
    #
    #     if not new_status:
    #         return CustomResponse().errorResponse(data={}, description="status is required")
    #
    #     current_status = order.status
    #     allowed_next = BO_STATUS_FLOW.get(current_status, [])
    #     if new_status not in allowed_next:
    #         return CustomResponse().errorResponse( data=
    #             {
    #                 "message": "Invalid status transition",
    #                 "current_status": current_status,
    #                 "allowed_next": allowed_next
    #             },
    #             description="Invalid status transition",
    #         )
    #     order.status = new_status
    #     order.save()
    #     if order.status == OrderStatus.PACKED:
    #         shipping_slip_path = generate_shipping_invoice(order)
    #         order.shipping_slip = shipping_slip_path
    #         order.save(update_fields=["shipping_slip"])
    #
    #
    #
    #         #todo: generate shipping slip
    #         # pass
    #     OrderTimeLines.objects.create(
    #         order=order,
    #         status=new_status,
    #         remarks=remarks
    #     )
    #     return CustomResponse.successResponse(
    #         data={},
    #         description="Order Updated successfully"
    #     )
    #


class AdminOrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        order_id = request.GET.get("id", "")
        store = request.store
        try:
            order = Order.objects.select_related(
                "user"
            ).prefetch_related(
                "items__product__media",
                "payments",
                "timelines"
            ).get(
                id=order_id,
                store=store
            )
        except Order.DoesNotExist:
            return CustomResponse.errorResponse("Order not found")

        # ---- order products ----
        items = []
        for item in order.items.all():
            product = item.product
            image = None
            product_images = product.media.filter(media_type=ProductMedia.IMAGE)

            if product_images.exists():
                image = product_images.first().url

            items.append({
                "order_product_id": str(item.id),
                "product_id": str(product.id),
                "sku": item.sku,
                "name": product.name,
                "colour": product.colour,
                "size": product.size,
                "qty": item.qty,
                "selling_price": str(item.selling_price),
                "mrp": str(item.mrp),
                "total_price": str(item.selling_price * item.qty),
                "rating": float(item.rating),
                "reviewed": item.review,
                "image": image
            })

        # ---- payments ----
        payments = []
        for p in order.payments.all():
            payments.append({
                "payment_id": str(p.id),
                "gateway": p.gateway,
                "amount": str(p.amount),
                "status": p.status,
                "cf_order_id": p.cf_order_id,
                "created_at": p.created_at
            })
        # ---------- Timelines ----------
        timelines = []
        coupon_details = {}
        for t in order.timelines.all():
            timelines.append({
                "status": t.status,
                "remarks": t.remarks,
                "timestamp": t.created_at
            })
        if order.coupon:
            coupon_details = {
                        "code": order.coupon.code,
                        "target_type": order.coupon.target_type,
                        "discount_type": order.coupon.discount_type,
                        "discount_value": order.coupon.discount_value,
                    }
        return CustomResponse.successResponse(
            data={
                "order": {
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "status": order.status,
                    "subtotal": str(order.amount),
                    "coupon_discount": str(order.coupon_discount),
                    "amount": str(order.amount),
                    "wallet_paid": str(order.wallet_paid),
                    "paid_online": str(order.paid_online),
                    "cash_on_delivery": str(order.cash_on_delivery),
                    "created_at": order.created_at,
                    "address": order.address,
                    "coupon": coupon_details,
                    "user": {
                        "id": str(order.user.id),
                        "name": order.user.name,
                        "mobile": order.user.mobile,
                        "email": order.user.email
                    }
                },
                "items": items,
                "payments": payments,
                "timelines": timelines
            },
            description="Order details fetched successfully"
        )


class AdminCreateCouponAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        store = request.store
        admin = request.user
        data = request.data

        code = data.get("code")
        target_type = data.get("target_type")
        discount_type = data.get("discount_type")
        discount_value = data.get("discount_value")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # ---------- Basic validation ----------
        if not code:
            return CustomResponse.errorResponse("Coupon code is required")

        if target_type not in ["ORDER", "SHIPPING", "PRODUCT", "CATEGORY", "TAG"]:
            return CustomResponse.errorResponse("Invalid target_type")

        if discount_type not in ["FLAT", "PERCENTAGE"]:
            return CustomResponse.errorResponse("Invalid discount_type")

        if discount_value is None or float(discount_value) <= 0:
            return CustomResponse.errorResponse("Invalid discount_value")

        if discount_type == "PERCENTAGE" and float(discount_value) > 100:
            return CustomResponse.errorResponse(
                "Percentage discount cannot exceed 100"
            )

        if not start_date or not end_date:
            return CustomResponse.errorResponse(
                "start_date and end_date are required"
            )

        # ---------- Uniqueness ----------
        if Coupons.objects.filter(
            store=store,
            code__iexact=code
        ).exists():
            return CustomResponse.errorResponse(
                "Coupon code already exists"
            )

        try:
            with transaction.atomic():

                coupon = Coupons.objects.create(
                    store=store,
                    code=code.upper(),
                    description=data.get("description"),

                    target_type=target_type,
                    discount_type=discount_type,
                    discount_value=discount_value,
                    max_discount_amount=data.get("max_discount_amount"),

                    min_order_amount=data.get("min_order_amount", 0),
                    min_product_amount=data.get("min_product_amount"),
                    first_order_only=data.get("first_order_only", False),

                    start_date=start_date,
                    end_date=end_date,

                    usage_limit=data.get("usage_limit"),
                    per_user_limit=data.get("per_user_limit"),

                    is_active=True,
                    created_by=admin.id
                )

                # ---------- Target mapping ----------
                if target_type == "PRODUCT":
                    product_ids = data.get("product_ids", [])
                    if not product_ids:
                        return CustomResponse.errorResponse(
                            "product_ids are required for PRODUCT coupon"
                        )
                    for pid in product_ids:
                        CouponProduct.objects.create(
                            coupon=coupon,
                            product_id=pid
                        )

                elif target_type == "CATEGORY":
                    category_ids = data.get("category_ids", [])
                    if not category_ids:
                        return CustomResponse.errorResponse(
                            "category_ids are required for CATEGORY coupon"
                        )
                    for cid in category_ids:
                        CouponCategory.objects.create(
                            coupon=coupon,
                            category_id=cid
                        )

                elif target_type == "TAG":
                    tag_ids = data.get("tag_ids", [])
                    if not tag_ids:
                        return CustomResponse.errorResponse(
                            "tag_ids are required for TAG coupon"
                        )
                    for tid in tag_ids:
                        CouponTag.objects.create(
                            coupon=coupon,
                            tag_id=tid
                        )

        except Exception as e:
            return CustomResponse.errorResponse(
                description=str(e) or "Failed to create coupon"
            )

        return CustomResponse.successResponse(
            data={
                "coupon_id": str(coupon.id),
                "code": coupon.code,
                "target_type": coupon.target_type
            },
            description="Coupon created successfully"
        )

    def get(self, request):
        store = request.store

        # ---------- Query params ----------
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        is_active = request.query_params.get("is_active")
        target_type = request.query_params.get("target_type")
        search = request.query_params.get("search")

        # ---------- Base queryset ----------
        queryset = Coupons.objects.filter(store=store)
        # ---------- Filters ----------
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        if target_type:
            queryset = queryset.filter(target_type__iexact=target_type)

        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )

        queryset = queryset.order_by("-created_at")

        # ---------- Pagination ----------
        total = queryset.count()
        offset = (page - 1) * page_size
        coupons = queryset[offset: offset + page_size]

        # ---------- Response ----------
        data = []
        current_time = now()

        for c in coupons:
            data.append({
                "id": str(c.id),
                "code": c.code,
                "description": c.description,

                "target_type": c.target_type,
                "discount_type": c.discount_type,
                "discount_value": str(c.discount_value),
                "max_discount_amount": str(c.max_discount_amount) if c.max_discount_amount else None,

                "min_order_amount": str(c.min_order_amount),
                "min_product_amount": str(c.min_product_amount) if c.min_product_amount else None,

                "first_order_only": c.first_order_only,

                "start_date": c.start_date,
                "end_date": c.end_date,

                "usage_limit": c.usage_limit,
                "per_user_limit": c.per_user_limit,

                "is_active": c.is_active,
                "is_expired": c.end_date < current_time,

                "created_at": c.created_at
            })

        return CustomResponse.successResponse(
            data=data,
            total=total,
            description="Coupons fetched successfully"
        )


class OrderShippingSlipAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        store = request.store

        if not store:
            return CustomResponse().errorResponse(
                description="Store context not found"
            )

        order = Order.objects.filter(
            id=id,
            store=store
        ).first()

        if not order:
            return CustomResponse().errorResponse(
                description="Order not found"
            )

        #  Status validation
        if order.status not in [
            OrderStatus.PACKED,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]:
            return CustomResponse().errorResponse(
                description="Shipping slip not available for this status"
            )

        if not order.shipping_slip:
            return CustomResponse().errorResponse(
                description="Shipping slip not generated yet"
            )

        return CustomResponse().successResponse(
            data={
                "order_id": str(order.id),
                "order_number": order.order_number,
                "shipping_slip": order.shipping_slip,
                "status": order.status
            },
            description="Shipping slip fetched successfully"
        )

class StoreAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        store = request.store

        if not store:
            return CustomResponse().errorResponse(
                description="Store context not found"
            )

        # -------------------------
        # Date Filters (ONLY for Orders & Sales)
        # -------------------------
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        order_date_filters = {}

        if from_date:
            order_date_filters["created_at__gte"] = make_aware(
                datetime.strptime(from_date, "%Y-%m-%d")
            )

        if to_date:
            order_date_filters["created_at__lte"] = make_aware(
                datetime.strptime(to_date, "%Y-%m-%d")
            )

        # -------------------------
        # Completed Orders (Date-filtered)
        # -------------------------
        completed_orders = Order.objects.filter(
            store=store,
            status__in=[
                OrderStatus.CREATED,
                OrderStatus.PACKED,
                OrderStatus.SHIPPED,
                OrderStatus.DELIVERED,
            ],
            **order_date_filters
        )
        # -------------------------
        # Order count by status (Date-filtered)
        # -------------------------
        status_counts_qs = (
            completed_orders
            .values("status")
            .annotate(count=Count("id"))
        )

        order_status_counts = {
            status["status"]: status["count"]
            for status in status_counts_qs
        }

        # Ensure all statuses are present (even if count = 0)
        for status in [
            OrderStatus.CREATED,
            OrderStatus.PACKED,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]:
            order_status_counts.setdefault(status, 0)

        # -------------------------
        # 1️⃣ Total Sales (Date-filtered)
        # -------------------------
        total_sales = completed_orders.aggregate(
            total=Sum("amount")
        )["total"] or 0

        # -------------------------
        # 2️⃣ Total Orders (Date-filtered)
        # -------------------------
        total_orders = completed_orders.count()

        # -------------------------
        # 3️⃣ Total Customers (NO date filter)
        # -------------------------
        total_customers = User.objects.filter(
            store=store
        ).count()

        # -------------------------
        # 4️⃣ Total Products (NO date filter)
        # -------------------------
        total_products = Product.objects.filter(
            store=store
        ).count()

        # -------------------------
        # 5️⃣ Recent 5 Orders (Date-filtered)
        # -------------------------
        recent_orders_qs = completed_orders.select_related("user") \
            .order_by("-created_at")[:5]

        recent_orders = []
        for order in recent_orders_qs:
            recent_orders.append({
                "order_id": str(order.id),
                "order_number": order.order_number,
                "customer_name": order.user.name,
                "amount": float(order.amount),
                "status": order.status,
                "created_at": order.created_at,
            })

        # -------------------------
        # 6️⃣ Top 5 Selling Products (Date-filtered)
        # -------------------------
        top_products_qs = (
            OrderProducts.objects
            .filter(
                order__store=store,
                order__status__in=[
                    OrderStatus.CREATED,
                    OrderStatus.PACKED,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED,
                ],
                **{f"order__{k}": v for k, v in order_date_filters.items()},
                product__isnull=False
            )
            .values("product_id", "product__name")
            .annotate(
                number_of_sales=Sum("qty"),
                amount=Sum(
                    ExpressionWrapper(
                        F("selling_price") * F("qty"),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                )
            )
            .order_by("-number_of_sales")[:5]
        )

        top_products = []
        for product in top_products_qs:
            top_products.append({
                "product_id": str(product["product_id"]),
                "name": product["product__name"],
                "number_of_sales": product["number_of_sales"],
                "amount": float(product["amount"] or 0),
            })

        # -------------------------
        # 7️⃣ Category-wise Sales Count (Date-filtered)
        # -------------------------
        category_qs = (
            OrderProducts.objects
            .filter(
                order__store=store,
                order__status__in=[
                    OrderStatus.CREATED,
                    OrderStatus.PACKED,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED,
                ],
                **{f"order__{k}": v for k, v in order_date_filters.items()},
                product__isnull=False
            )
            .values(
                "product__categories__id",
                "product__categories__name"
            )
            .annotate(
                total_qty=Sum("qty"),
                total_amount=Sum(
                    ExpressionWrapper(
                        F("selling_price") * F("qty"),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                )
            )
            .order_by("-total_qty")
        )

        categories = []
        for cat in category_qs:
            if cat["product__categories__id"]:
                categories.append({
                    "category_id": str(cat["product__categories__id"]),
                    "category_name": cat["product__categories__name"],
                    "total_quantity": cat["total_qty"],
                    "total_amount": float(cat["total_amount"] or 0),
                })





        # -------------------------
        # Final Response
        # -------------------------
        data = {
            "total_sales": float(total_sales),
            "total_orders": total_orders,
            "total_customers": total_customers,
            "total_products": total_products,

            "order_status_counts": order_status_counts,

            "recent_orders": recent_orders,
            "top_selling_products": top_products,

            "category_numbers": categories,
        }


        return CustomResponse().successResponse(
            data=data,
            description="Store analytics fetched successfully"
        )

#
# class StoreAnalyticsAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         store = request.store
#
#         if not store:
#             return CustomResponse().errorResponse(
#                 description="Store context not found"
#             )
#
#         # -------------------------
#         # Use ALL these statuses
#         # -------------------------
#         completed_orders = Order.objects.filter(
#             store=store,
#             status__in=[
#                 OrderStatus.CREATED,
#                 OrderStatus.PACKED,
#                 OrderStatus.SHIPPED,
#                 OrderStatus.DELIVERED,
#             ]
#         )
#
#         # -------------------------
#         # 1️⃣ Total Sales
#         # -------------------------
#         total_sales = completed_orders.aggregate(
#             total=Sum("amount")
#         )["total"] or 0
#
#         # -------------------------
#         # 2️⃣ Total Orders
#         # -------------------------
#         total_orders = completed_orders.count()
#
#         # -------------------------
#         # 3️⃣ Total Customers (All store users)
#         # -------------------------
#         total_customers = User.objects.filter(
#             store=store
#         ).count()
#
#         # -------------------------
#         # 4️⃣ Total Products
#         # -------------------------
#         total_products = Product.objects.filter(
#             store=store
#         ).count()
#
#         # -------------------------
#         # 5️⃣ Recent 5 Orders
#         # -------------------------
#         recent_orders_qs = completed_orders.select_related("user") \
#             .order_by("-created_at")[:5]
#
#         recent_orders = []
#         for order in recent_orders_qs:
#             recent_orders.append({
#                 "order_id": str(order.id),
#                 "order_number": order.order_number,
#                 "customer_name": order.user.name,
#                 "amount": float(order.amount),
#                 "status": order.status,
#                 "created_at": order.created_at,
#             })
#
#         # -------------------------
#         # 6️⃣ Top 5 Selling Products
#         # -------------------------
#         top_products_qs = (
#             OrderProducts.objects
#             .filter(
#                 order__store=store,
#                 order__status__in=[
#                     OrderStatus.CREATED,
#                     OrderStatus.PACKED,
#                     OrderStatus.SHIPPED,
#                     OrderStatus.DELIVERED,
#                 ],
#                 product__isnull=False
#             )
#             .values("product_id", "product__name")
#             .annotate(
#                 number_of_sales=Sum("qty"),
#                 amount=Sum(
#                     ExpressionWrapper(
#                         F("selling_price") * F("qty"),
#                         output_field=DecimalField(max_digits=12, decimal_places=2)
#                     )
#                 )
#             )
#             .order_by("-number_of_sales")[:5]
#         )
#
#         top_products = []
#         for product in top_products_qs:
#             top_products.append({
#                 "product_id": str(product["product_id"]),
#                 "name": product["product__name"],
#                 "number_of_sales": product["number_of_sales"],
#                 "amount": float(product["amount"] or 0),
#             })
#
#         # -------------------------
#         # Final Response
#         # -------------------------
#         data = {
#             "total_sales": float(total_sales),
#             "total_orders": total_orders,
#             "total_customers": total_customers,
#             "total_products": total_products,
#             "recent_orders": recent_orders,
#             "top_selling_products": top_products,
#         }
#
#         return CustomResponse().successResponse(
#             data=data,
#             description="Store analytics fetched successfully"
#         )

class ClientInfo(APIView):

    permission_classes = [AllowAny]

    def get(self, request):
        store = request.store
        res = {
            "logo": store.logo,
            "name": store.name,
            "mobile": store.mobile,
            "address": store.address,
            "secondary_color": store.secondary_color,
            "primary_color": store.primary_color,
            "is_email_login": store.email_login,
            "is_mobile_login": store.mobile_login,
        }
        return CustomResponse().successResponse(
            data=res,
            description="Client info fetched successfully"
        )


