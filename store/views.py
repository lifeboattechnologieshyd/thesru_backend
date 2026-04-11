import uuid
from tokenize import Double
from unicodedata import category
import requests
from django.contrib.admin.templatetags.admin_list import results
from django.db import transaction
from django.db import IntegrityError
from django.db.models import Q, Count, Avg
from decimal import Decimal
from django.core.exceptions import ImproperlyConfigured

from django.utils.timesince import timesince
from django.utils.timezone import now
from rest_framework.templatetags.rest_framework import items
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny
from django.utils import timezone

from django.conf import settings

from config.firebase import send_push_notification
from db import models
from db.models import AddressMaster, PinCode, Product, Order, OrderProducts, Payment, OrderTimeLines, \
    Banner, Category, Cart, CouponUsage, Wishlist, CouponProduct, CouponCategory, CouponTag, WebBanner, FlashSaleBanner, \
    ProductReviews, ContactMessage, Tag, Coupons, ProductReviewMedia, Store, InventoryBatch, \
    InventoryTransaction, ShippingPlan
from db.models.user import WebhookLog
from enums.store import OrderStatus, PaymentStatus, NotificationEvent
from mixins.drf_views import CustomResponse
from utils.notification import trigger_notification
from utils.store import generate_order_number, time_ago, update_stock_after_order
from utils.user import send_order_created_admin_email


class IshuCategories(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        store = request.store
        filters = {
            'parent__isnull': True,
            'is_active': True,
            'store': store
        }
        parents = (
            Category.objects
            .filter(**filters)
            .prefetch_related('children')
            .order_by('priority')
        )
        data = []
        for parent in parents:
            children = parent.children.filter(
                is_active=True
            ).order_by('priority')
            data.append({
                "id": str(parent.id),
                "name": parent.name,
                "priority": parent.priority,
                "category_group": parent.category_group,
                "slug": parent.slug,
                "icon": parent.icon,
                "search_tags": parent.search_tags,
                "is_active": parent.is_active,
                "children": [
                    {
                        "id": str(child.id),
                        "name": child.name,
                        "icon": child.icon,
                        "priority": child.priority
                    }
                    for child in children
                ]
            })
        return CustomResponse().successResponse(
            data=data,
            total=len(data)
        )

class CategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        store = request.store
        queryset = Category.objects.filter(is_active=True,store=store)
        #  LIST ALL CATEGORIES
        data = []
        for category in queryset.order_by("-created_at"):
            data.append({
                "id": str(category.id),
                "name": category.name,
                "priority": category.priority,
                "category_group": category.category_group,
                "slug": category.slug,
                "icon": category.icon,
                "search_tags": category.search_tags,
                "is_active": category.is_active,
            })
        return CustomResponse.successResponse(
            data=data,
            total=len(data)
        )

class TagsListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        store = request.store
        queryset = Tag.objects.filter(is_active=True, store=store)
        #  LIST ALL TAGS
        data = []
        for tag in queryset.order_by("-created_at"):
            data.append({
                "id": str(tag.id),
                "name": tag.name,
                "display_on_home": tag.display_on_home,
                "slug": tag.slug,
                "is_active": tag.is_active,
            })
        return CustomResponse.successResponse(
            data=data,
            total=len(data)
        )

class ProductListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        store = request.store

        # ---------- Query params ----------
        search = request.query_params.get("search")
        category_id = request.query_params.get("categories")
        tags = request.query_params.get("tags")
        product_id = request.query_params.get("product_id", None)
        price = request.query_params.get("price", None)

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 15))

        # ---------- Base queryset ----------
        queryset = Product.objects.filter(
            store=store,
            is_active=True
        ).prefetch_related(
            "categories",
            "tags",
            "media"
        ).order_by("-created_at")

        # ---------- Search ----------
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(search_tags__icontains=search)
            )

        # ---------- Category filter ----------
        if category_id:
            queryset = queryset.filter(
                categories__id=category_id
            )

        if product_id:
            queryset = queryset.filter(id=product_id)
        if price:
            queryset = queryset.filter(selling_price__lte=price)

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

        for p in queryset:
            data.append({
                "id": str(p.id),
                "lsin": p.lsin,
                "group_code": p.group_code,
                "sku": p.sku,

                "name": p.name,
                "colour": p.colour,
                "size": p.size,

                "selling_price": str(p.selling_price),
                "mrp": str(p.mrp),
                "current_stock": p.current_stock,

                "description": p.description,
                "highlights": p.highlights,

                "rating": float(p.rating),
                "total_rating": p.total_rating,
                "number_of_reviews": p.number_of_reviews,

                "categories": [
                    {"id": str(c.id), "name": c.name}
                    for c in p.categories.all()
                ],
                "tags": [
                    {"id": str(t.id), "name": t.name}
                    for t in p.tags.all()
                ],
                "search_tags": p.search_tags,
                "gst_percentage": p.gst_percentage,
                "gst_amount": p.gst_amount,
                "images": [m.url for m in p.media.all()],
                "is_active": p.is_active
            })

        return CustomResponse.successResponse(
            data=data,
            total=total,
            description="Products fetched successfully"
        )

class ProductDetailAPIView(APIView):
    permission_classes = [AllowAny]  # Public API

    def get(self, request, id):
        store = request.store

        try:
            current = Product.objects.prefetch_related(
                "categories",
                "tags",
                "media"
            ).get(
                id=id,
                store=store,
                is_active=True
            )
        except Product.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Product not found"
            )

        related_products = Product.objects.filter(
            store=store,
            group_code=current.group_code,
            is_active=True
        ).exclude(
            id=current.id
        ).prefetch_related("media")

        def serialize_product(p):
            return {
                "id": str(p.id),
                "lsin": p.lsin,
                "group_code": p.group_code,
                "sku": p.sku,

                "name": p.name,
                "colour": p.colour,
                "size": p.size,

                "selling_price": str(p.selling_price),
                "mrp": str(p.mrp),
                "current_stock": p.current_stock,

                "description": p.description,
                "highlights": p.highlights,

                "rating": float(p.rating),
                "total_rating": p.total_rating,
                "number_of_reviews": p.number_of_reviews,

                "categories": [
                    {"id": str(c.id), "name": c.name}
                    for c in p.categories.all()
                ],
                "tags": [
                    {"id": str(t.id), "name": t.name}
                    for t in p.tags.all()
                ],
                "search_tags": p.search_tags,
                "gst_percentage": p.gst_percentage,
                "gst_amount": p.gst_amount,
                "images": [m.url for m in p.media.all()],
                "is_active": p.is_active
            }
        products = [serialize_product(current)]
        products += [serialize_product(p) for p in related_products]
        return CustomResponse.successResponse(
            data=products,
            description="Product details fetched successfully"
        )
class AddToWishlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        store = request.store
        product_id = request.data.get("product_id")

        if not product_id:
            return CustomResponse().errorResponse(
                description="product_id is required"
            )

        try:
            product_variant = Product.objects.get(
                store=store,
                id=product_id,
                is_active=True
            )
        except Product.DoesNotExist:
            return CustomResponse.errorResponse(
                description="product variant not found"
            )

        wishlist, created = Wishlist.objects.get_or_create(
            store=store,
            user=user,
            product=product_variant,
            # defaults={"is_active": True}
        )

        if not created:
            return CustomResponse().successResponse(data={},
                description="Product already in wishlist"
            )

        return CustomResponse().successResponse(data={},
            description="Product added to wishlist"
        )

class RemoveFromWishlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        try:
            product_variant = Product.objects.get(
                store=request.store,
                id=id,
                is_active=True
            )
        except Product.DoesNotExist:
            return CustomResponse.errorResponse(
                description="product variant not found"
            )
        deleted, _ = Wishlist.objects.filter(
            store=request.store,
            user=request.user,
            product=product_variant
        ).delete()

        if not deleted:
            return CustomResponse().errorResponse(
                description="Wishlist item not found",
            )

        return CustomResponse().successResponse(data={},
            description="Item removed from wishlist"
        )

class WishlistListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        store = request.store
        user = request.user

        wishlists = Wishlist.objects.filter(
            store=store,
            user=user,
            is_active=True
        ).select_related(
            "product",
        ).prefetch_related(
            "product__media",
            "product__categories",
            "product__tags"
        ).order_by("-created_at")

        data = []

        for w in wishlists:
            p = w.product

            data.append({
                "id": str(p.id),
                "lsin": p.lsin,
                "group_code": p.group_code,
                "sku": p.sku,

                "name": p.name,
                "colour": p.colour,
                "size": p.size,

                "selling_price": str(p.selling_price),
                "mrp": str(p.mrp),
                "current_stock": p.current_stock,

                "description": p.description,
                "highlights": p.highlights,

                "rating": float(p.rating),
                "total_rating": p.total_rating,
                "number_of_reviews": p.number_of_reviews,

                "categories": [
                    {"id": str(c.id), "name": c.name}
                    for c in p.categories.all()
                ],
                "tags": [
                    {"id": str(t.id), "name": t.name}
                    for t in p.tags.all()
                ],
                "search_tags": p.search_tags,
                "gst_percentage": p.gst_percentage,
                "gst_amount": p.gst_amount,
                "images": [m.url for m in p.media.all()],
                "is_active": p.is_active
            })

        return CustomResponse.successResponse(
            data=data,
            description="Wishlist products fetched successfully"
        )





class AddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data
        store = request.store
        user = request.user


        required_fields = ["mobile","name","address_name","address_type","full_address",
                           "house_number","country","city","state","area","pin_code",
                           "is_default"

                           ]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

        if not user.name:
            user.name = data.get("name")
            user.save(update_fields=["name"])

        if data.get("is_default"):
            AddressMaster.objects.filter(user_id=request.user.id,is_default = True).update(is_default = False)

        AddressMaster.objects.create(
            store_id=store.id,
            user_id = request.user.id,
            mobile = data.get("mobile"),
            name = data.get("name"),
            address_name = data.get("address_name"),
            address_type = data.get("address_type"),
            full_address = data.get("full_address"),
            house_number = data.get("house_number"),
            country = data.get("country"),
            city = data.get("city"),
            state = data.get("state"),
            area = data.get("area"),
            pin_code = data.get("pin_code"),
            landmark = data.get("landmark"),
            is_default = data.get("is_default"),

        )
        return CustomResponse.successResponse(data={},description="address created successfully")
    def get(self,request,id=None):
        store = request.store

        if id:
            address = AddressMaster.objects.filter(id=id,user_id=request.user.id,store_id=store.id).first()
            if not address:
                return CustomResponse.errorResponse(description="address not found")

            return CustomResponse.successResponse(data=[self._address_dict(address)],total=1)
        addresses = AddressMaster.objects.filter(user_id = request.user.id).order_by("-created_at")

        data = []
        for addres in addresses:
            data.append(self._address_dict(addres))
        return CustomResponse.successResponse(data=data,total = len(data))

    def put(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="address id required")

        address = AddressMaster.objects.filter(id=id,user_id=request.user.id).first()

        if not address:
            return CustomResponse.errorResponse(description="address not found")

        if request.data.get("is_default"):
            AddressMaster.objects.filter(user_id = request.user.id,is_default = True).exclude(id=id).update(is_default= False)
            for field in [
                "mobile", "name", "address_name", "address_type",
                "full_address", "house_number", "country", "city",
                "state", "area", "pin_code", "landmark", "is_default"
            ]:
                setattr(address,field,request.data.get(field))

            address.save()

            return CustomResponse.successResponse(data={},description="address updated successfully")
    def delete(self,request,id=None):
        if not id:
            return CustomResponse.errorResponse(description="id is required")

        address = AddressMaster.objects.filter(id=id,user_id = request.user.id).first()
        if not address:
            return CustomResponse.errorResponse(description="address not found")

        address.delete()
        return CustomResponse.successResponse(data={},description="address deleted successfully")

    def _address_dict(self, address):
        return {
            "id": str(address.id),
            "mobile": address.mobile,
            "name": address.name,
            "address_name": address.address_name,
            "address_type": address.address_type,
            "full_address": address.full_address,
            "house_number": address.house_number,
            "country": address.country,
            "city": address.city,
            "state": address.state,
            "area": address.area,
            "pin_code": address.pin_code,
            "landmark": address.landmark,
            "is_default": address.is_default,
        }


class PinListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        pin = request.query_params.get("pincode")

        if not pin:
            return CustomResponse.errorResponse(description="pin required")

        pin = PinCode.objects.filter(pin=pin).first()
        if not pin:
            return CustomResponse.errorResponse(description="pin not found")

        data = {
            "pin":pin.pin,
            "state":pin.state,
            "city":pin.city,
            "district":pin.district,
            "country":pin.country
        }

        return CustomResponse.successResponse(data=data,total=1)

class CheckoutPreview(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        store = request.store
        user = request.user
        data = request.data

        items = data.get("products", data.get("items", []))
        coupon_code = data.get("coupon_code")
        address = data.get("address")

        if not items:
            return CustomResponse.errorResponse("Products are required")

        products_data = []
        cart_items = []

        mrp_total = Decimal("0.00")
        subtotal = Decimal("0.00")

        # ---------- Validate & prepare products ----------
        for item in items:
            product_id = item.get("product_id")
            qty = int(item.get("qty", 0))

            if not product_id or qty <= 0:
                return CustomResponse.errorResponse("Invalid product or qty")

            product = Product.objects.filter(
                id=product_id,
                store=store,
                is_active=True
            ).first()
            if not product:
                return CustomResponse.errorResponse(
                    "Product not found or inactive"
                )
            if product.current_stock < qty:
                return CustomResponse.errorResponse(
                    f"{product.name} is out of stock"
                )

            line_mrp = product.mrp * qty
            line_subtotal = product.selling_price * qty

            mrp_total += line_mrp
            subtotal += line_subtotal

            products_data.append({
                "product": product,
                "qty": qty,
                "line_mrp": line_mrp,
                "line_subtotal": line_subtotal
            })
            cart_items.append(product)


        price_drop_discount = mrp_total - subtotal
        # ---------- Coupon ----------
        coupon_discount = Decimal("0.00")
        apportioned_map = {}
        coupon = None

        if coupon_code:
            try:
                coupon_discount, apportioned_map, coupon = calculate_coupon_discount(
                    store=store,
                    user=user,
                    products=[
                        {
                            "product": p["product"],
                            "qty": p["qty"],
                            "line_total": p["line_subtotal"]
                        }
                        for p in products_data
                    ],
                    subtotal=subtotal,
                    coupon_code=coupon_code
                )
            except Exception as e:
                return CustomResponse.errorResponse(str(e))

        # ---------- Charges (future ready) ----------
        shipping_charge = calculate_shipping(store, subtotal, address.get("pincode", address.get("pin_code")), cart_items)
        platform_fee = Decimal("0.00")  # later config-based

        final_payable = (
                subtotal
                - coupon_discount
                + shipping_charge
                + platform_fee
        )

        # ---------- Product response ----------
        product_response = []
        for item in products_data:
            product = item["product"]
            discount = apportioned_map.get(product.id, Decimal("0.00"))

            product_response.append({
                "product_id": str(product.id),
                "name": product.name,
                "sku": product.sku,
                "qty": item["qty"],

                "mrp": str(product.mrp),
                "selling_price": str(product.selling_price),

                "line_mrp": str(item["line_mrp"]),
                "line_subtotal": str(item["line_subtotal"]),

                "coupon_discount": str(discount),
                "payable": str(item["line_subtotal"] - discount),

                "media": [
                    {"url": m.url, "type": m.media_type}
                    for m in product.media.all()
                ]
            })
        coupon_details = None
        if coupon:
            coupon_details = {
                "code": coupon.code if coupon else None,
                "discount": str(coupon_discount)
            }

        return CustomResponse.successResponse(
            data={
                "products": product_response,
                "billing": {
                    "mrp_total": str(mrp_total),
                    "price_drop_discount": str(price_drop_discount),
                    "subtotal": str(subtotal),
                    "coupon_discount": str(coupon_discount),
                    "shipping_charge": str(shipping_charge),
                    "platform_fee": str(platform_fee),
                    "final_payable": str(final_payable)
                },
                "coupon": coupon_details
            },
            description="Checkout preview calculated"
        )
def calculate_shipping(store, cart_total, pincode=None, cart_items=None):
    plan = store.shipping_plans.filter(is_active=True).first()
    if not plan or not plan.is_active:
        return 0
    cart_items = cart_items or []

    paid_items = [
        item for item in cart_items
        if not item.is_free_shipping
    ]

    if not paid_items:
        return 0


    # 1️⃣ Free above rule (highest priority)
    if plan.free_above_amount and cart_total >= plan.free_above_amount:
        return 0

    # 2️⃣ Check PINCODE rules first
    if pincode:
        rule = plan.rules.filter(
            pincode=pincode
        ).first()
        if rule:
            return rule.rate
    # 4️⃣ Default flat rate
    return plan.flat_rate or 0


def calculate_coupon_discount(
    store,
    user,
    products,
    subtotal,
    coupon_code=None
):
    """
    products  = [
        {
            "product": Product instance,
            "qty": int,
            "line_total": Decimal  # selling_price * qty
        }
    ]
    and
    Returns:
    - total_coupon_discount (Decimal)
    - apportioned_discount_map {product_id: Decimal}
    - coupon object or None
    """

    # ---------- No coupon ----------
    if not coupon_code:
        return Decimal("0.00"), {}, None

    # ---------- Fetch coupon ----------
    try:
        coupon = Coupons.objects.get(
            store=store,
            code__iexact=coupon_code,
            is_active=True,
            start_date__lte=now(),
            end_date__gte=now()
        )
    except Coupons.DoesNotExist:
        raise Exception("Invalid or expired coupon code")

    # ---------- First order check ----------
    if coupon.first_order_only:
        if Order.objects.filter(
            store=store,
            user=user,
            status=OrderStatus.DELIVERED
        ).exists():
            raise Exception("Coupon valid only for first order")

    # ---------- Min order value ----------
    if subtotal < coupon.min_order_amount:
        raise Exception("Order amount not eligible for this coupon")

    # ---------- Identify eligible products ----------
    eligible_items = []

    for item in products:
        product = item["product"]

        if coupon.target_type == "ORDER":
            eligible_items.append(item)

        elif coupon.target_type == "PRODUCT":
            if CouponProduct.objects.filter(
                coupon=coupon,
                product=product
            ).exists():
                eligible_items.append(item)

        elif coupon.target_type == "CATEGORY":
            if CouponCategory.objects.filter(
                coupon=coupon,
                category__in=product.categories.all()
            ).exists():
                eligible_items.append(item)

        elif coupon.target_type == "TAG":
            if CouponTag.objects.filter(
                coupon=coupon,
                tag__in=product.tags.all()
            ).exists():
                eligible_items.append(item)

        elif coupon.target_type == "SHIPPING":
            # Handled outside (shipping engine)
            eligible_items.append(item)

    if not eligible_items:
        raise Exception("Coupon not applicable to selected products")

    # ---------- Eligible amount ----------
    eligible_amount = sum(
        item["line_total"] for item in eligible_items
    )

    if eligible_amount <= 0:
        return Decimal("0.00"), {}, coupon

    # ---------- Calculate discount ----------
    if coupon.discount_type == "FLAT":
        discount = coupon.discount_value
    else:
        discount = (eligible_amount * coupon.discount_value) / Decimal("100")

    # ---------- Cap discount ----------
    if coupon.max_discount_amount:
        discount = min(discount, coupon.max_discount_amount)

    discount = min(discount, eligible_amount)

    # ---------- Apportion discount product-wise ----------
    apportioned_map = {}

    for item in eligible_items:
        product = item["product"]
        ratio = item["line_total"] / eligible_amount
        apportioned_map[product.id] = (
            discount * ratio
        ).quantize(Decimal("0.01"))

    return discount.quantize(Decimal("0.01")), apportioned_map, coupon



class InitiateOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        store = request.store
        user = request.user
        data = request.data

        items = data.get("products", [])
        address = data.get("address")
        coupon_code = data.get("coupon_code", None)

        if not items:
            return CustomResponse.errorResponse("products are required")

        if not address:
            return CustomResponse.errorResponse("address is required")
        products_data = []
        cart_items = []

        subtotal = Decimal("0.00")
        mrp_total = Decimal("0.00")
        product_map = {} # not used yet
        try:
            with transaction.atomic():
                # ---------- Validate products & lock stock ----------
                for item in items:
                    product_id = item.get("product_id")
                    qty = int(item.get("qty", 0))

                    if not product_id or qty <= 0:
                        return CustomResponse.errorResponse(
                            "Invalid product or quantity"
                        )

                    product = Product.objects.select_for_update().get(
                        id=product_id,
                        store=store,
                        is_active=True
                    )

                    if product.current_stock < qty:
                        return CustomResponse.errorResponse(
                            f"{product.name} is out of stock"
                        )
                    line_mrp = product.mrp * qty
                    line_subtotal = product.selling_price * qty

                    mrp_total += line_mrp
                    subtotal += line_subtotal
                    products_data.append({
                        "product": product,
                        "qty": qty,
                        "line_total": line_subtotal,
                        "line_mrp": line_mrp
                    })
                    cart_items.append(product)
                price_drop_discount = mrp_total - subtotal
                # ---------- Coupon ----------
                coupon_discount = Decimal("0.00")
                apportioned_map = {}
                coupon = None
                if coupon_code:
                    coupon_discount, apportioned_map, coupon = calculate_coupon_discount(
                        store=store,
                        user=user,
                        products=[
                            {
                                "product": p["product"],
                                "qty": p["qty"],
                                "line_total": p["line_total"]
                            }
                            for p in products_data
                        ],
                        subtotal=subtotal,
                        coupon_code=coupon_code
                    )
            # ---------- Charges (future ready) ----------
            shipping_charge = calculate_shipping(store, subtotal, address.get("pincode"), cart_items)
            platform_fee = Decimal("0.00")

            final_amount = subtotal - coupon_discount + shipping_charge + platform_fee
            order_number = generate_order_number(store, store.product_code)
            order = Order.objects.create(
                store=store,
                user=user,
                order_number=order_number,
                address=data.get("address"),
                mrp=mrp_total,
                selling_price=subtotal,
                coupon_discount=coupon_discount,
                coupon_code=coupon_code,
                coupon=coupon,
                amount=final_amount,
                paid_online=final_amount,
                wallet_paid=Decimal("0.00"),
                shipping_charges=shipping_charge,
                status=OrderStatus.INITIATED,
                created_by=user.mobile
            )


            # ---------- Create Order Products ----------
            print(f"products data before === {products_data}")
            for item in products_data:

                product = item["product"]
                qty = item["qty"]

                discount = apportioned_map.get(
                    product.id, Decimal("0.00")
                )

                OrderProducts.objects.create(
                    order=order,
                    product=product,
                    sku=product.sku,
                    qty=qty,

                    mrp=product.mrp,
                    selling_price=product.selling_price,

                    apportioned_discount=discount,
                    apportioned_online=(
                            product.selling_price * qty - discount
                    ),
                    apportioned_wallet=Decimal("0.00"),
                    apportioned_gst=product.gst_amount
                )
            # ---------- Order Timeline ----------
            OrderTimeLines.objects.create(
                order=order,
                status=OrderStatus.INITIATED,
                remarks="Order initiated"
            )

            # ---------- Create Payment ----------
            payment = Payment.objects.create(
                store=store,
                user=user,
                order=order,
                gateway="CASHFREE",
                amount=final_amount,
                status=PaymentStatus.INITIATED,
                remarks="Payment Initiated"
            )
            payment_resp = initiateOrder(
                user=user,
                amount=final_amount,
                order=order,
                store=store
            )
            if payment_resp["success"]:
                payment.session_id = payment_resp["payment_session_id"]
                payment.cf_order_id = payment_resp["cf_order_id"]
                payment.save(
                    update_fields=["session_id", "cf_order_id"]
                )
                return CustomResponse.successResponse(
                    data={
                        "order_number": order.order_number,
                        "payment_session_id": payment.session_id,
                        "cf_order_id": payment.cf_order_id,
                        "amount": str(final_amount)
                    },
                    description="Order initiated successfully"
                )
            else:
                payment.status = PaymentStatus.FAILED
                payment.remarks = str(payment.remarks) + "==" + "PaymentStatus.FAILED" + ": " + payment_resp[
                    "description"]
                payment.save(
                    update_fields=["status", "remarks"]
                )
                order.status = OrderStatus.FAILED
                order.save()
                return CustomResponse.errorResponse(
                    data={},
                    description=payment_resp["description"]
                )
        except Exception as e:
            return CustomResponse().errorResponse(
                description=str(e) or "Failed to initiate order"
            )

def initiateOrder(user, amount, order, store):
    """
    Initiate payment using school-specific CashFree credentials from the database.
    """
    print("DEBUG CASHFREE CLIENT ID:", store.client_id)
    print("DEBUG CASHFREE CLIENT SECRET:", store.client_secret)
    print("DEBUG CASHFREE URL:", settings.CASHFREE_URL)
    print("DEBUG CASHFREE WEBHOOK:", settings.CASHFREE_WEBHOOK)

    # --- Prepare payload ---
    payload = {
        "order_currency": "INR",
        "order_amount": float(amount),
        "order_id": str(order.order_number),
        "customer_details": {
            "customer_id": str(user.id),
            "customer_phone": str(user.mobile),
            "customer_name": str(user.username),
        },
        "order_meta": {
            "notify_url": settings.CASHFREE_WEBHOOK,
        },
    }

    # --- Prepare headers ---
    headers = {
        "x-api-version": settings.CASHFREE_API_VERSION,
        "x-client-id": store.client_id,
        "x-client-secret": store.client_secret,
        "Content-Type": "application/json",
    }
    print("headers",headers)
    print("payload",payload)


    try:
        # --- Send request to CashFree ---
        response = requests.post(settings.CASHFREE_URL, json=payload, headers=headers, timeout=15)


        # --- Validate response ---
        if response.status_code == 200:
            resp_json = response.json()
            order_id = resp_json.get("cf_order_id")
            session_id = resp_json.get("payment_session_id")

            if order_id and session_id:
                return {
                    "success": True,
                    "cf_order_id": order_id,
                    "payment_session_id": session_id,
                    "order_number":order.order_number
                }
            else:
                return {
                    "success": False,
                    "description": "Could not found cf_order_id and payment_session_id"
                }
        else:
            return {
                "success": False,
                "description": f"Cashfree response code {response.status_code}: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "description": "Exception occurred"
        }


SYSTEM_UPDATED_BY = "CASHFREE_WEBHOOK"

def deduct_stock_fifo(product, quantity):

    batches = InventoryBatch.objects.select_for_update().filter(
        product=product,
        remaining_quantity__gt=0
    ).order_by("created_at")

    qty_to_deduct = quantity
    total_profit = 0
    deduction_details = []

    for batch in batches:
        if qty_to_deduct <= 0:
            break

        deduct_qty = min(batch.remaining_quantity, qty_to_deduct)

        profit_per_unit = batch.sell_price - batch.cost_per_unit
        total_profit += profit_per_unit * deduct_qty

        # Reduce stock
        batch.remaining_quantity -= deduct_qty
        batch.save()

        # Ledger entry
        InventoryTransaction.objects.create(
            store=product.store,
            product=product,
            batch=batch,
            transaction_type='OUT',
            quantity=deduct_qty,
            cost_price=batch.cost_per_unit,
            selling_price=batch.sell_price
        )

        deduction_details.append({
            "batch_id": batch.id,
            "deducted": deduct_qty,
            "cost_price": batch.cost_per_unit,
            "sell_price": batch.sell_price
        })

        qty_to_deduct -= deduct_qty

    if qty_to_deduct > 0:
        raise Exception("Insufficient stock")

    return total_profit, deduction_details


def remove_cart_items(user, store):
    Cart.objects.filter(user=user, store=store).delete()

class Webhook(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            event_type = data.get("type")
            order_id = data.get("data", {}).get("order", {}).get("order_id")
            order_amount = data.get("data", {}).get("order", {}).get("order_amount")
            print("Webhook received:", data)
            # logs of webhook just for records...
            log = WebhookLog()
            log.event_type = "ORDER_PAYMENT_WEBHOOK"
            log.payload = data
            log.save()
            # Cashfree test webhook may not have real order_id
            if not order_id:
                print("Webhook test / invalid payload")
                return CustomResponse().successResponse(data={},
                    description="Webhook received"
                )
            with transaction.atomic():

                order = Order.objects.select_for_update().filter(order_number=order_id).first()
                if not order:
                    print("No Order Found with Order Number")
                    return CustomResponse().successResponse(data={},
                                                        description="No Order Found with Order Number"
                                                        )

                payment = Payment.objects.filter(order=order).first()
                # If no DB records → still return 200
                if not payment:
                    print("Order/Payment not found for order_id:", order_id)
                    return CustomResponse().successResponse(data={},
                        description="Webhook received"
                    )
                if payment.status != PaymentStatus.INITIATED:
                    print("Payment status verified with Cashfree and updated Already")

                    return CustomResponse().successResponse(
                        data={
                            "order_number": order.order_number,
                            "final_payment_status": order.status,
                        },
                        description="Payment status verified with Cashfree and updated"
                    )

                if event_type == "PAYMENT_SUCCESS_WEBHOOK":
                    update_stock_after_order(order)
                    payment.status = PaymentStatus.COMPLETED
                    payment.updated_by = event_type
                    payment.save(update_fields=["status", "updated_by"])
                    order.status = OrderStatus.CREATED
                    order.paid_online = order_amount
                    order.updated_by = event_type
                    order.save(update_fields=["status", "paid_online", "updated_by"])
                    OrderTimeLines.objects.create(
                        order=order,
                        status=OrderStatus.CREATED,
                        remarks="Order Placed"
                    )
                    try:
                        send_order_created_admin_email(order)
                        print("send_order_created_admin_email")
                    except ImproperlyConfigured as e:
                        pass
                    if order.coupon is not None:
                        CouponUsage.objects.create(
                            coupon=order.coupon,
                            user=order.user,
                            order=order
                        )
                    context = {
                        "var": f"{order.user.name}|{order.order_number[-5:]}|"
                    }
                    trigger_notification(order.store,NotificationEvent.ORDER_PLACED, context, order.user.mobile, order.user.email)
                    trigger_notification(order.store,NotificationEvent.ADMIN_ORDER_RECEIVED, context, order.store.mobile, order.store.email)
                    remove_cart_items(order.user, order.store)
                elif event_type == "PAYMENT_FAILED_WEBHOOK":
                    payment.status = PaymentStatus.FAILED
                    payment.updated_by = event_type
                    payment.save(update_fields=["status", "updated_by"])

                    order.status = OrderStatus.FAILED
                    order.updated_by = event_type
                    order.save(update_fields=["status", "updated_by"])

                    OrderTimeLines.objects.create(
                        order=order,
                        status=OrderStatus.FAILED,
                        remarks="Order Failed"
                    )
                elif event_type == "PAYMENT_USER_DROPPED_WEBHOOK":
                    payment.status = PaymentStatus.CANCELLED
                    payment.updated_by = event_type
                    payment.save(update_fields=["status", "updated_by"])

                    order.status = OrderStatus.CANCELLED
                    order.updated_by = event_type
                    order.save(update_fields=["status", "updated_by"])
                    OrderTimeLines.objects.create(
                        order=order,
                        status=OrderStatus.CANCELLED,
                        remarks="Order Cancelled"
                    )
                else:
                    print("Unhandled webhook type:", event_type)

            print("Webhook Processed")
            return CustomResponse().successResponse(data={},
                description="Webhook processed"
            )
        except Exception as e:
            print("Webhook exception:", str(e))
            return CustomResponse().successResponse(data={},
                description="Webhook received"
            )
#
class PaymentStatusAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        print("Payment Status api payload received:", data)
        order_number = data.get("order_number")
        cf_order_id = data.get("cf_order_id")

        if not order_number:
            return CustomResponse().errorResponse(
                description="order number  required"
            )

        order = Order.objects.filter(order_number=order_number).first()
        if not order:
            return CustomResponse().errorResponse(
                description="Order Details Mismatched"
            )
        payment = Payment.objects.filter(cf_order_id=cf_order_id).first()
        if not payment:
            return CustomResponse().errorResponse(
                description="Payment not found"
            )
        if payment.status == PaymentStatus.COMPLETED:
            return CustomResponse().successResponse(
                data={
                    "order_number": order_number,
                    "final_payment_status": order.status,
                },
                description="Payment status verified with Cashfree and updated"
            )


        # 🔥 FETCH CASHFREE STATUS
        cf_response = fetch_cashfree_payment_status(order_number, request.store)

        cf_order_status = cf_response.get("order_status")  # PAID / ACTIVE / FAILED
        verified_status = map_cashfree_status(cf_order_status)

        with transaction.atomic():

            payment.status = verified_status
            payment.save(update_fields=["status"])

            if verified_status == PaymentStatus.COMPLETED:
                update_stock_after_order(order)

                order.status = OrderStatus.CREATED
                order.paid_online = payment.amount
                order.updated_by = "PAYMENT STATUS BY FE"
                order.save(update_fields=["status", "paid_online"])
                OrderTimeLines.objects.create(
                    order=order,
                    status=OrderStatus.CREATED,
                    remarks="Order Placed"
                )
                if order.coupon is not None:
                    CouponUsage.objects.create(
                        coupon=order.coupon,
                        user=order.user,
                        order=order
                    )
                context = {
                    "var" : f"{order.order_number}|"
                }

                trigger_notification(order.store,
                                     NotificationEvent.ORDER_PLACED,
                                     context,
                                     order.user.mobile, order.user.email)
                # send_push_notification(
                #     store=order.store,
                #     token=order.user.fcm_token,
                #     title="Order Placed",
                #     body="Your order has been placed successfully",
                #     data={"order_id": order.order_number}
                # )
                # todo: send an email to admin also.
                # todo: send a sms n whatsapp to admin also.
                remove_cart_items(order.user, order.store)
            elif verified_status == PaymentStatus.FAILED:
                order.status = OrderStatus.FAILED
                order.updated_by = "PAYMENT STATUS BY FE"
                order.save(update_fields=["status", "updated_by"])
                OrderTimeLines.objects.create(
                    order=order,
                    status=OrderStatus.FAILED,
                    remarks="Order failed"
                )

            elif verified_status == PaymentStatus.CANCELLED:
                order.status = OrderStatus.CANCELLED
                order.updated_by = "PAYMENT STATUS BY FE"
                order.save(update_fields=["status", "updated_by"])
                OrderTimeLines.objects.create(
                    order=order,
                    status=OrderStatus.CANCELLED,
                    remarks="Order Cancelled"
                )
        print("Payment Status api response")
        return CustomResponse().successResponse(
            data={
                "order_number": order_number,
                "final_payment_status": order.status,
            },
            description="Payment status verified with Cashfree and updated"
        )

def map_cashfree_status(cf_status):
    mapping = {
        "PAID": PaymentStatus.COMPLETED,
        "ACTIVE": PaymentStatus.PENDING,
        "FAILED": PaymentStatus.FAILED,
        "CANCELLED": PaymentStatus.CANCELLED,
    }
    return mapping.get(cf_status, PaymentStatus.PENDING)

def fetch_cashfree_payment_status(order_number, cashfree):
    url = f"{settings.CASHFREE_URL}/{order_number}"

    headers = {
        "x-api-version": settings.CASHFREE_API_VERSION,
        "x-client-id": cashfree.client_id,
        "x-client-secret": cashfree.client_secret,
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
        raise Exception("Failed to fetch order status from Cashfree")

    return response.json()

class OrderedProducts(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        order_id = request.GET.get("order_id")
        products = OrderProducts.objects.filter(order_id=order_id).values()
        return CustomResponse().successResponse(
            data=list(products),
            total=products.count()
        )


class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    TIMELINE_STATUS_MAP = {
        "PAYMENT": [
            OrderStatus.INITIATED,
            OrderStatus.CREATED,
            OrderStatus.FAILED,
            OrderStatus.CANCELLED,
        ],
        "PACKED": [
            OrderStatus.PACKED,
        ],
        "SHIPPED": [
            OrderStatus.SHIPPED,
            OrderStatus.OUT_FOR_DELIVERY,
        ],
        "DELIVERED": [
            OrderStatus.DELIVERED,
        ],
    }

    STATUS_FILTER_MAP = {
        "ONGOING": [
            OrderStatus.INITIATED,
            OrderStatus.CREATED,
            OrderStatus.PACKED,
            OrderStatus.SHIPPED,
            OrderStatus.OUT_FOR_DELIVERY,
        ],
        "DELIVERED": [
            OrderStatus.DELIVERED,
        ],
        "CANCELLED": [
            OrderStatus.CANCELLED,
            OrderStatus.FAILED,
            OrderStatus.UNFULFILLED,
        ],
    }

    def build_fe_timelines(self, order):
        timeline_map = {
            "PAYMENT": None,
            "PACKED": None,
            "SHIPPED": None,
            "DELIVERED": None,
        }

        for t in order.timelines.all():
            for fe_status, mapped_statuses in self.TIMELINE_STATUS_MAP.items():
                if t.status in mapped_statuses:
                    # pick the FIRST occurrence only
                    if timeline_map[fe_status] is None:
                        timeline_map[fe_status] = t

        # ---------- Final FE timeline ----------
        timelines = []

        for fe_status in ["PAYMENT", "PACKED", "SHIPPED", "DELIVERED"]:
            t = timeline_map[fe_status]

            timelines.append({
                "status": fe_status,
                "completed": t is not None,
                "date": t.created_at.strftime("%d %b %Y") if t else None,
                "time_ago": f"{timesince(t.created_at)} ago" if t else None
            })

        return timelines

    def get(self, request):
        store = request.store
        user = request.user
        status_filter = request.query_params.get("status", "ONGOING")
        orders_qs = Order.objects.filter(
            store=store,
            user=user
        ).order_by("-created_at")
        status_filter = status_filter.upper()
        if status_filter not in self.STATUS_FILTER_MAP:
            return CustomResponse.errorResponse(
                description="Invalid status filter"
            )

        orders_qs = orders_qs.filter(
            status__in=self.STATUS_FILTER_MAP[status_filter]
        )
        # ---------- Prefetch order items ----------
        orders_qs = orders_qs.prefetch_related(
            "items__product__media",
            "timelines"
        )


        data = []

        for order in orders_qs:
            items = []

            for item in order.items.all():
                product = item.product
                image_url = None
                for m in product.media.all():
                    if m.media_type.lower() == "image":
                        image_url = m.url
                        break

                items.append({
                    "order_product_id": str(item.id),
                    "product_id": str(product.id),
                    "sku": item.sku,
                    "image": image_url,

                    "name": product.name,
                    "colour": product.colour,
                    "size": product.size,

                    "qty": item.qty,
                    "selling_price": str(item.selling_price),
                    "mrp": str(item.mrp),
                    "total_price": str(item.selling_price * item.qty),

                    "rating": float(item.rating),
                    "reviewed": item.review
                })
            timelines = self.build_fe_timelines(order)



            data.append({
                "order": {
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "status": order.status,
                    "shipping_charges": order.shipping_charges,

                    "coupon_discount": str(order.coupon_discount),
                    "amount": str(order.amount),

                    "wallet_paid": str(order.wallet_paid),
                    "paid_online": str(order.paid_online),
                    "cash_on_delivery": str(order.cash_on_delivery),

                    "created_at": order.created_at,
                    "address": order.address,

                    "display_date": order.created_at.strftime("%d %b %Y"),

                },
                "timelines": timelines,   # 👈 ADDED
                "items": items
            })

        return CustomResponse.successResponse(
            data=data,
            description="Orders fetched successfully"
        )






class BannerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id=None):
        store = request.store


        action = request.query_params.get("action")

        queryset = Banner.objects.filter(is_active=True,store_id=store.id
)

        #  ACTION FILTER
        if action is not None:
            if action.lower() == "true":
                queryset = queryset.filter(action=True)
            elif action.lower() == "false":
                queryset = queryset.filter(action=False)

        #  SINGLE BANNER
        if id:
            banner = queryset.filter(id=id).first()
            if not banner:
                return CustomResponse.errorResponse(
                    description="Active banner not found"
                )

            return CustomResponse.successResponse(
                data=[{
                    "id": str(banner.id),
                    "screen": banner.screen,
                    "image": banner.image,
                    "is_active": banner.is_active,
                    "priority": banner.priority,
                    "action": banner.action,
                    "destination": banner.destination,

                }],
                total=1
            )

        #  LIST BANNERS
        data = []
        for banner in queryset.order_by("-created_at"):
            data.append({
                "id": str(banner.id),
                "screen": banner.screen,
                "image": banner.image,
                "is_active": banner.is_active,
                "priority": banner.priority,
                "action": banner.action,
                "destination": banner.destination,

            })

        return CustomResponse.successResponse(
            data=data,
            total=len(data)
        )

class WebBannerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id=None):
        store = request.store
        action = request.query_params.get("action")

        queryset = WebBanner.objects.filter(
            store_id=store.id,
            is_active=True
        )
        # ---------- Priority-based ordering ----------
        queryset = queryset.order_by(
            "priority",
            "-created_at"
        )

        data = [
            {
                "id": str(banner.id),
                "screen": banner.screen,
                "title": banner.title,
                "description": banner.description,
                "image": banner.image,
                "priority": banner.priority,
                "action": banner.action,
                "destination": banner.destination,
                "is_active": banner.is_active,
                "created_at": banner.created_at,
                "updated_at": banner.updated_at,
            }
            for banner in queryset
        ]

        return CustomResponse.successResponse(
            data=data,
            total=len(data)
        )


class FlashSaleBannerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        store = request.store
        queryset = FlashSaleBanner.objects.filter(
            store_id=store.id,
            is_active=True
        ).order_by(
            "priority",
            "-created_at"
        )
        data = [
            {
                "id": str(banner.id),
                "screen": banner.screen,
                "name": banner.name,
                "title": banner.title,
                "description": banner.description,
                "image": banner.image,
                "priority": banner.priority,
                "action": banner.action,
                "destination": banner.destination,
                "is_active": banner.is_active,
                "start_date": banner.start_date,
                "end_date": banner.end_date,
                "discount": banner.discount,
                "product_ids": banner.product_id,
                "created_at": banner.created_at,
                "updated_at": banner.updated_at,
            }
            for banner in queryset
        ]

        return CustomResponse.successResponse(
            data=data,
            total=len(data)
        )





class AddToCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        store = request.store
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))
        if not product_id:
            return CustomResponse().errorResponse(
                description="product_id is required"
            )

        product = Product.objects.filter(id=product_id).first()
        if not product:
            return CustomResponse().errorResponse(
                description="Product not found",
            )

        cart_item, created = Cart.objects.get_or_create(
            store=store,
            user=user,
            product=product,
            defaults={"quantity": quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save(update_fields=["quantity"])
        else:
            cart_item.is_active = True
            cart_item.save(update_fields=["is_active"])

        return CustomResponse.successResponse(
            data={},
            description="Product added to cart"
        )

class CartListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        store = request.store
        user = request.user

        cart_items = Cart.objects.filter(
            store=store,
            user=user,
            is_active=True
        ).select_related(
            "product",
        ).prefetch_related(
            "product__media",
            "product__categories",
            "product__tags"
        ).order_by("-created_at")

        data = []

        for w in cart_items:
            p = w.product
            data.append({
                "id": str(p.id),
                "lsin": p.lsin,
                "group_code": p.group_code,
                "sku": p.sku,

                "name": p.name,
                "colour": p.colour,
                "size": p.size,

                "selling_price": str(p.selling_price),
                "mrp": str(p.mrp),
                "current_stock": p.current_stock,

                "description": p.description,
                "highlights": p.highlights,

                "rating": float(p.rating),
                "total_rating": p.total_rating,
                "number_of_reviews": p.number_of_reviews,

                "categories": [
                    {"id": str(c.id), "name": c.name}
                    for c in p.categories.all()
                ],
                "tags": [
                    {"id": str(t.id), "name": t.name}
                    for t in p.tags.all()
                ],
                "search_tags": p.search_tags,
                "gst_percentage": p.gst_percentage,
                "gst_amount": p.gst_amount,
                "images": [m.url for m in p.media.all()],
                "is_active": p.is_active,
                "quantity": w.quantity
            })
        return CustomResponse.successResponse(
            data=data,
            description="Cart items fetched successfully"
        )








class UpdateCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        quantity = request.data.get("quantity")

        if not quantity or int(quantity) <= 0:
            return CustomResponse().errorResponse(
                description="Valid quantity is required"
            )

        product = Product.objects.filter(id=id).first()
        if not product:
            return CustomResponse().errorResponse(
                description="Product not found"
            )

        try:
            cart_item = Cart.objects.get(
                product=product,
                user=request.user
            )
        except Cart.DoesNotExist:
            return CustomResponse().errorResponse(
                description="Cart item not found"
            )

        cart_item.quantity = int(quantity)
        cart_item.save()

        return CustomResponse().successResponse(
            data={},
            description="cart updated successfully"
        )

class RemoveFromCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):

        product = Product.objects.filter(id=id).first()
        if not product:
            return CustomResponse().errorResponse(
                description="Product not found"
            )
        deleted, _ = Cart.objects.filter(
            product=product,
            user=request.user
        ).delete()

        if not deleted:
            return CustomResponse().errorResponse(
                description="Cart item not found",
            )

        return CustomResponse().successResponse(data={},
            description="Item removed from cart"
        )











class CartTotalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        store = request.store

        cart_items = Cart.objects.filter(user=user,store=store).count()
        wishlist_items = Wishlist.objects.filter(user=user,store=store).count()

        return CustomResponse().successResponse(
            data={
                "wishlist_items": wishlist_items,
                "cart_items": cart_items
            },

        )


class Reviews(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def post(self, request):
        payload = request.data
        user = request.user
        store = request.store

        product_id = payload.get("product_id")
        rating = int(payload.get("rating", 0))
        review_text = payload.get("review", "")
        media_list = payload.get("media", [])

        if not product_id:
            return CustomResponse().errorResponse(
                description="product_id is required"
            )
        if rating < 1 or rating > 5:
            return CustomResponse.errorResponse("rating must be between 1 and 5")

        product = Product.objects.filter(id=product_id).first()
        if not product:
            return CustomResponse().errorResponse(
                description="We couldn’t find any product with the provided ID."
            )

        has_purchased = OrderProducts.objects.filter(
            product=product,
            order__user=user,
            order__status=OrderStatus.DELIVERED
        ).exists()

        if not has_purchased:
            return CustomResponse().errorResponse(
                description="You can review this product only after purchasing it."
            )

        if ProductReviews.objects.filter(user=user, product=product).exists():
            return CustomResponse().errorResponse(data={}, description="You have already submitted a review for this product.")
        try:
            with transaction.atomic():
                review = ProductReviews.objects.create(
                    store=store,
                    product=product,
                    user=user,
                    rating=rating,
                    review=review_text,
                    created_by=user.id
                )
                # ---- Save media ----
                for media in media_list:
                    ProductReviewMedia.objects.create(
                        review=review,
                        url=media.get("url"),
                        media_type=media.get("media_type")
                    )
                # ---- Update product rating ----
                agg = ProductReviews.objects.filter(
                    product=product
                ).aggregate(
                    avg=Avg("rating"),
                    count=Count("id")
                )
                product.rating = round(agg["avg"] or 0, 2)
                product.number_of_reviews = agg["count"]
                product.save(update_fields=["rating", "number_of_reviews"])
            return CustomResponse.successResponse(
                description="Review added successfully",data={}
            )
        except Exception as e:
            return CustomResponse.errorResponse(
                description=str(e)
            )


    def get(self, request):
        store = request.store
        product_id = request.query_params.get("product_id")

        if not product_id:
            return CustomResponse.errorResponse("product_id is required")

        reviews = ProductReviews.objects.filter(
            store=store,
            product_id=product_id
        ).select_related("user").prefetch_related("media")

        if not reviews.exists():
            return CustomResponse.successResponse(
                data={
                    "reviews": [],
                    "rating_summary": {
                        "average_rating": 0,
                        "total_ratings": 0,
                        "rating_breakup": {
                            "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
                        }
                    }
                }
            )

        # ---------------- Rating Aggregates ----------------
        rating_counts = (
            reviews
            .values("rating")
            .annotate(count=Count("rating"))
        )

        rating_breakup = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        total_ratings = 0

        for r in rating_counts:
            rating_breakup[str(r["rating"])] = r["count"]
            total_ratings += r["count"]

        avg_rating = reviews.aggregate(
            avg=Avg("rating")
        )["avg"] or 0

        # ---------------- Review List ----------------
        review_list = []
        for review in reviews.order_by("-created_at"):
            review_list.append({
                "review_id": review.id,
                "user": {
                    "id": review.user.id,
                    "name": review.user.username,
                    "profile_image": review.user.profile_image
                },
                "rating": review.rating,
                "review": review.review,
                "media": [
                    {
                        "type": media.media_type,
                        "url": media.url
                    }
                    for media in review.media.all()
                ],
                "created_at": review.created_at,
                "time_ago": time_ago(review.created_at)
            })

        return CustomResponse.successResponse(
            data={
                "rating_summary": {
                    "average_rating": round(avg_rating, 1),
                    "total_ratings": total_ratings,
                    "rating_breakup": rating_breakup
                },
                "reviews": review_list
            }
        )


class ContactMessageAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            name = request.data.get("name")
            email = request.data.get("email")
            subject = request.data.get("subject")
            message = request.data.get("message")

            # -------- Validation --------
            if not all([name, email, subject, message]):
                return CustomResponse().errorResponse(
                    description="All fields (name, email, subject, message) are required"
                )

            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )

            return CustomResponse().successResponse(
                description="Message submitted successfully",
                data={}
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                description=str(e)
            )


# class ApplyCoupon(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         user = request.user
#         store = user.store
#         data = request.data
#         coupon_code = data.get("coupon_code")
#         items = data.get("items", [])
#         # ---------- Fetch coupon ----------
#         try:
#             coupon = Coupons.objects.get(
#                 store=store,
#                 code=coupon_code,
#                 is_active=True,
#                 start_date__lte=now(),
#                 end_date__gte=now()
#             )
#         except Coupons.DoesNotExist:
#             return CustomResponse.errorResponse("Invalid or expired coupon")
#
#         product_ids = [i.get("product_id") for i in items if i.get("product_id")]
#         products = Product.objects.filter(
#             id__in=product_ids,
#             store=store,
#             is_active=True
#         )
#         if not products.exists():
#             return CustomResponse.errorResponse("Invalid products")
#         return calculate_coupon_discount(store=store,coupon=coupon, user=user, products=products, items=items)


# from decimal import Decimal

# def calculate_coupon_discount(*, store, user,coupon, products, items):
#     order_amount = Decimal("0.00")
#     product_ids = [i.get("product_id") for i in items if i.get("product_id")]
#     qty_map = {i["product_id"]: int(i.get("qty", 0)) for i in items}
#
#     product_price_map = {}
#     for p in products:
#         qty = qty_map.get(str(p.id), 0)
#         line_total = p.selling_price * qty
#         order_amount += line_total
#         product_price_map[str(p.id)] = {
#             "price": p.selling_price,
#             "qty": qty,
#             "line_total": line_total
#         }
#     # ---------- First order check ----------
#     if coupon.first_order_only:
#         has_order = Order.objects.filter(
#             store=store,
#             user=user,
#             status__in=[
#                 OrderStatus.CONFIRMED,
#                 OrderStatus.DELIVERED
#             ]
#         ).exists()
#
#         if has_order:
#             return CustomResponse.errorResponse(
#                 "Coupon valid only for first order"
#             )
#     # ---------- Usage limits ----------
#     if coupon.usage_limit is not None:
#         if CouponUsage.objects.filter(coupon=coupon).count() >= coupon.usage_limit:
#             return CustomResponse.errorResponse("Coupon usage limit exceeded")
#     if coupon.per_user_limit is not None:
#         if CouponUsage.objects.filter(
#                 coupon=coupon,
#                 user=user
#         ).count() >= coupon.per_user_limit:
#             return CustomResponse.errorResponse(
#                 "You have already used this coupon"
#             )
#     # ---------- Minimum order ----------
#     if order_amount < coupon.min_order_amount:
#         return CustomResponse.errorResponse(
#             f"Minimum order value ₹{coupon.min_order_amount} required"
#         )
#     eligible_amount = order_amount
#     # ---------- Target based eligibility ----------
#     if coupon.target_type == "PRODUCT":
#         eligible_products = CouponProduct.objects.filter(
#             coupon=coupon,
#             product_id__in=product_ids
#         ).values_list("product_id", flat=True)
#
#         eligible_amount = sum(
#             product_price_map[str(pid)]["line_total"]
#             for pid in eligible_products
#             if str(pid) in product_price_map
#         )
#
#         if eligible_amount == 0:
#             return CustomResponse.errorResponse(
#                 "Coupon not applicable to selected products"
#             )
#     elif coupon.target_type == "CATEGORY":
#         eligible_products = Product.objects.filter(
#             id__in=product_ids,
#             categories__in=CouponCategory.objects.filter(
#                 coupon=coupon
#             ).values_list("category_id", flat=True)
#         ).distinct()
#
#         eligible_amount = sum(
#             product_price_map[str(p.id)]["line_total"]
#             for p in eligible_products
#         )
#
#         if eligible_amount == 0:
#             return CustomResponse.errorResponse(
#                 "Coupon not applicable to product categories"
#             )
#
#     elif coupon.target_type == "TAG":
#         eligible_products = Product.objects.filter(
#             id__in=product_ids,
#             tags__in=CouponTag.objects.filter(
#                 coupon=coupon
#             ).values_list("tag_id", flat=True)
#         ).distinct()
#
#         eligible_amount = sum(
#             product_price_map[str(p.id)]["line_total"]
#             for p in eligible_products
#         )
#
#         if eligible_amount == 0:
#             return CustomResponse.errorResponse(
#                 "Coupon not applicable to product tags"
#             )
#     # ---------- Calculate discount ----------
#     if coupon.discount_type == "FLAT":
#         discount = coupon.discount_value
#     else:
#         discount = eligible_amount * coupon.discount_value / Decimal("100")
#     if coupon.max_discount_amount:
#         discount = min(discount, coupon.max_discount_amount)
#     discount = min(discount, order_amount)
#     payable_amount = order_amount - discount
#     return CustomResponse.successResponse(
#         data={
#             "coupon_code": coupon.code,
#             "order_amount": str(order_amount),
#             "discount_amount": str(discount.quantize(Decimal("0.01"))),
#             "payable_amount": str(payable_amount.quantize(Decimal("0.01"))),
#             "eligible_amount": str(eligible_amount),
#             "message": "Coupon applied successfully"
#         }
#     )




class UserCouponListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        store = request.store

        # ---------- Pagination ----------
        current_time = now()
        queryset = Coupons.objects.filter(
            store=store,
            is_active=True,
            start_date__lte=current_time,
            end_date__gte=current_time
        ).order_by("-created_at")
        # ---------- First order check ----------
        has_completed_order = Order.objects.filter(
            store=store,
            user=request.user,
            status__in=[
                # OrderStatus.CONFIRMED,
                OrderStatus.DELIVERED
            ]
        ).exists()

        eligible_coupons = []


        # ---------- Response ----------
        data = []

        for c in queryset:
            # 1️⃣ First order validation
            if c.first_order_only and has_completed_order:
                continue
            # 2️⃣ Global usage limit
            if c.usage_limit is not None:
                total_used = CouponUsage.objects.filter(
                    coupon=c
                ).count()
                if total_used >= c.usage_limit:
                    continue
            # 3️⃣ Per-user usage limit
            if c.per_user_limit is not None:
                user_used = CouponUsage.objects.filter(
                        coupon=c,
                        user=request.user
                    ).count()
                if user_used >= c.per_user_limit:
                    continue

            data.append({
                "id": str(c.id),
                "code": c.code,
                "description": c.description,
                "target_type": c.target_type,
                "discount_type": c.discount_type,
                "discount_value": str(c.discount_value),
                "max_discount_amount": (
                    str(c.max_discount_amount)
                    if c.max_discount_amount else None
                ),
                "min_order_amount": str(c.min_order_amount),
                "first_order_only": c.first_order_only,
                "start_date": c.start_date,
                "end_date": c.end_date
            })

        return CustomResponse.successResponse(
            data=data,
            description="Active coupons fetched successfully"
        )





from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

class TestTriggerNotificationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        store_id = data.get("store_id")
        event = data.get("event")
        mobile = data.get("mobile")
        email = data.get("email")
        context = data.get("context", {})

        if not store_id or not event:
            return CustomResponse().errorResponse(
                description="store_id and event are required"
            )

        if not context:
            return CustomResponse().errorResponse(
                description="context is required"
            )



        store = get_object_or_404(Store, id=store_id)

        # 🔔 Trigger notification
        trigger_notification(
            store=store,
            event=event,
            context=context,
            recipient=mobile,
            email=email
        )

        return CustomResponse().successResponse(
            data={
                "store": store.name,
                "event": event,
                "mobile": mobile,
                "email": email,
                "context": context
            },
            description="Notification trigger executed successfully"
        )






class FirebaseTestPushAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        store = request.store
        user = request.user



        # Validate FCM token
        fcm_token = request.data.get("fcm_token")
        if not fcm_token:
            return CustomResponse().errorResponse(
                description="fcm_token is required"
            )

        try:
            response = send_push_notification(
                store=store,
                token=fcm_token,
                title="Firebase Test Notification",
                body=" Firebase is working successfully!",
                data={
                    "type": "TEST",
                    "time": str(timezone.now())
                }
            )

            return CustomResponse().successResponse(
                data={
                    "firebase_response": response
                },
                description="Firebase push notification sent successfully"
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                description="Firebase push failed",
                data={
                    "error": str(e)
                }
            )

class ShippingDetails(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        store = request.store
        shipping_details = ShippingPlan.objects.filter(store=store).values()
        return CustomResponse().successResponse(
            data=shipping_details.first(),
        )
