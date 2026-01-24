import uuid
from tokenize import Double
from unicodedata import category
import requests
from django.contrib.admin.templatetags.admin_list import results
from django.db import transaction
from django.db import IntegrityError
from django.db.models import Q
from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny

from django.conf import settings
from db.models import AddressMaster, PinCode, Product, Order, OrderProducts, Payment, OrderTimeLines, \
    Banner, Category, Cart, Wishlist, WebBanner, FlashSaleBanner, ProductReviews, ContactMessage, Tag
from enums.store import OrderStatus, PaymentStatus
from mixins.drf_views import CustomResponse
from utils.store import generate_order_number


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
        category_id = request.query_params.get("category")
        tags = request.query_params.get("tags")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 12))

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
            lsin=current.lsin,
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

        required_fields = ["mobile","name","address_name","address_type","full_address",
                           "house_number","country","city","state","area","pin_code",
                           "is_default"

                           ]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

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
            "area":pin.area,
            "country":pin.country
        }

        return CustomResponse.successResponse(data=data,total=1)




class InitiateOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        store = request.store
        user = request.user
        data = request.data

        cart_items = Cart.objects.select_related("product").filter(
            store=store,
            user=user
        )
        if not cart_items.exists():
            return CustomResponse.errorResponse("Cart is empty")

        subtotal = Decimal("0.00")
        for item in cart_items:
            if item.product.current_stock < item.quantity:
                return CustomResponse.errorResponse(
                    f"{item.product.name} is out of stock"
                )
            subtotal += item.product.selling_price * item.quantity
        coupon_discount = Decimal("0.00")
        # todo : validatae coupon if applied
        total_amount = subtotal - coupon_discount


        order_number = generate_order_number(store, "ORD")

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    store=store,
                    user=user,
                    order_number=order_number,
                    address=data.get("address"),
                    coupon_discount=coupon_discount,
                    amount=total_amount,
                    wallet_paid=Decimal("0.00"),
                    status=OrderStatus.INITIATED,
                    created_by=user.id
                )

                for item in cart_items:
                    OrderProducts.objects.create(
                        order=order,
                        product=item.product,
                        sku=item.product.sku,
                        qty=item.quantity,
                        mrp=item.product.mrp,
                        selling_price=item.product.selling_price,
                        apportioned_discount=Decimal("0.00"), # coupon discount if any
                        apportioned_online=item.product.selling_price * item.quantity,
                        apportioned_wallet=Decimal("0.00"), # wallet paid if any
                        apportioned_gst=item.product.gst_amount
                    )

                #  Create Order Timeline
                OrderTimeLines.objects.create(
                    order=order,
                    status=OrderStatus.INITIATED,
                    remarks=data.get("remarks", "Order initiated")
                ) # after 72hrs INITIATED orders remarks should be changed to auto cancelled.

                #  Create Payment
                payment = Payment.objects.create(
                    store=store,
                    order=order,
                    gateway='CASHFREE',
                    amount=total_amount,
                    user=user,
                )
                payment_resp = initiateOrder(user, total_amount, order, request.store)
                print("DEBUG cf_order_id:", payment_resp["cf_order_id"], len(payment_resp["cf_order_id"]))
                print("DEBUG payment_session_id:", payment_resp["payment_session_id"], len(payment_resp["payment_session_id"]))


                payment.session_id = payment_resp["payment_session_id"]
                payment.cf_order_id = payment_resp["cf_order_id"]
                payment.save(update_fields=["session_id", "order_id"])

            return CustomResponse().successResponse(
                data=payment_resp,
                description="Order initiated. Please continue payment"
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
    print("DEBUG CASHFREE URL:", store.url)
    print("DEBUG CASHFREE WEBHOOK:", store.webhook)

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
            "notify_url": store.webhook,
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
        response = requests.post(store.url, json=payload, headers=headers, timeout=15)


        # --- Validate response ---
        if response.status_code == 200:
            resp_json = response.json()
            order_id = resp_json.get("cf_order_id")
            session_id = resp_json.get("payment_session_id")

            if order_id and session_id:
                return {
                    "cf_order_id": order_id,
                    "payment_session_id": session_id,
                    "order_number":order.order_number
                }
            else:
                raise Exception("Could not found cf_order_id and payment_session_id")
        else:
            raise Exception(
                f"Cashfree response code {response.status_code}: {response.text}"
            )
    except Exception as e:
        raise Exception(e)


SYSTEM_UPDATED_BY = "CASHFREE_WEBHOOK"

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

            # Cashfree test webhook may not have real order_id
            if not order_id:
                print("Webhook test / invalid payload")
                return CustomResponse().successResponse(data={},
                    description="Webhook received"
                )
            order = Order.objects.filter(order_number=order_id).first()
            if not order:
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

            with transaction.atomic():

                if event_type == "PAYMENT_SUCCESS_WEBHOOK":
                    payment.status = PaymentStatus.COMPLETED
                    payment.updated_by = SYSTEM_UPDATED_BY
                    payment.save(update_fields=["status", "updated_by"])

                    order.status = OrderStatus.PLACED
                    order.paid_online = order_amount
                    order.updated_by = SYSTEM_UPDATED_BY
                    order.save(update_fields=["status", "paid_online", "updated_by"])

                    remove_cart_items(order.user, order.store)
                elif event_type == "PAYMENT_FAILED_WEBHOOK":
                    payment.status = PaymentStatus.FAILED
                    order.updated_by = SYSTEM_UPDATED_BY
                    order.save(update_fields=["status", "paid_online", "updated_by"])

                    order.status = OrderStatus.FAILED
                    order.updated_by = SYSTEM_UPDATED_BY
                    order.save(update_fields=["status", "updated_by"])

                elif event_type == "PAYMENT_USER_DROPPED_WEBHOOK":
                    payment.status = PaymentStatus.CANCELLED
                    payment.updated_by = SYSTEM_UPDATED_BY
                    payment.save(update_fields=["status", "updated_by"])

                    order.status = OrderStatus.CANCELLED
                    order.updated_by = SYSTEM_UPDATED_BY
                    order.save(update_fields=["status", "updated_by"])
                else:
                    print("Unhandled webhook type:", event_type)

            return CustomResponse().successResponse(data={},
                description="Webhook processed"
            )

        except Exception as e:
            # IMPORTANT: Always return 200
            print("Webhook exception:", str(e))
            return CustomResponse().successResponse(data={},
                description="Webhook received"
            )


#
class PaymentStatusAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data

        order_number = data.get("order_number")
        cf_order_id = data.get("cf_order_id")

        if not order_number:
            return CustomResponse().errorResponse(
                description="order_number and status are required"
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
            return CustomResponse().successResponse(data={},
                description="Payment already completed (webhook confirmed)"
            )

        # 🔥 FETCH CASHFREE STATUS
        cf_response = fetch_cashfree_payment_status(order_number, request.store)

        cf_order_status = cf_response.get("order_status")  # PAID / ACTIVE / FAILED
        verified_status = map_cashfree_status(cf_order_status)

        with transaction.atomic():

            payment.status = verified_status
            payment.save(update_fields=["status"])

            if verified_status == PaymentStatus.COMPLETED:
                order.status = OrderStatus.PLACED
                order.paid_online = payment.amount
                order.save(update_fields=["status", "paid_online"])

                remove_cart_items(order.user, order.store)


            elif verified_status == PaymentStatus.FAILED:
                order.status = OrderStatus.FAILED
                order.save(update_fields=["status", "paid_online"])


            elif verified_status == PaymentStatus.CANCELLED:
                order.status = OrderStatus.CANCELLED
                order.save(update_fields=["status", "paid_online"])

        return CustomResponse().successResponse(
            data={
                "order_number": order_number,
                "cashfree_status": cf_order_status,
                "final_payment_status": payment.status,
                "order_status": order.status,
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
    url = f"{cashfree.url}/{order_number}"

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

    STATUS_FILTER_MAP = {
        "ONGOING": [
            OrderStatus.INITIATED,
            OrderStatus.PLACED,
            OrderStatus.CONFIRMED,
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


    def get(self, request):
        store = request.store
        user = request.user
        status_filter = request.query_params.get("status")
        orders_qs = Order.objects.filter(
            store=store,
            user=user
        ).order_by("-created_at")
        # ---------- Status filter ----------
        if status_filter:
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
                "items__product"
            )

            data = []

            for order in orders_qs:
                items = []

                for item in order.items.all():
                    product = item.product

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
                        "reviewed": item.review
                    })

                data.append({
                    "order": {
                        "order_id": str(order.id),
                        "order_number": order.order_number,
                        "status": order.status,

                        "coupon_discount": str(order.coupon_discount),
                        "amount": str(order.amount),

                        "wallet_paid": str(order.wallet_paid),
                        "paid_online": str(order.paid_online),
                        "cash_on_delivery": str(order.cash_on_delivery),

                        "created_at": order.created_at,
                        "address": order.address
                    },
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
        queryset = WebBanner.objects.filter(is_active=True,store_id=store.id)

        #  ACTION FILTER
        if action is not None:
            if action.lower() == "true":
                queryset = queryset.filter(action=True)
            elif action.lower() == "false":
                queryset = queryset.filter(action=False)

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

class FlashSaleBannerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        store = request.store
        action = request.query_params.get("action")

        queryset = FlashSaleBanner.objects.filter(
            is_active=True,
            store_id=store.id
        )

        # ACTION FILTER
        if action is not None:
            queryset = queryset.filter(action=action.lower() == "true")

        # ---------- LIST BANNERS ----------
        banners = list(queryset.order_by("-created_at"))

        # Collect ALL product IDs from all banners
        all_product_ids = set()
        for banner in banners:
            if banner.product_id:
                all_product_ids.update(banner.product_id)

        # Fetch products in ONE query
        products = Product.objects.filter(id__in=all_product_ids)
        product_map = {str(p.id): p.name for p in products}

        data = []
        for banner in banners:
            product_names = []
            if banner.product_id:
                product_names = [
                    product_map.get(str(pid))
                    for pid in banner.product_id
                    if str(pid) in product_map
                ]

            data.append({
                "id": str(banner.id),
                "screen": banner.screen,
                "name":banner.name,
                "title":banner.title,
                "description":banner.description,
                "image": banner.image,
                "is_active": banner.is_active,
                "priority": banner.priority,
                "action": banner.action,
                "destination": banner.destination,
                "start_date": banner.start_date,
                "end_date": banner.end_date,
                "product_id": banner.product_id,
                "product_names": product_names,
                "discount": banner.discount
            })

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
        if not product_id:
            return CustomResponse().errorResponse(
                description="product_id is required"
            )

        product = Product.objects.filter(id=product_id).first()
        if not product:
            return CustomResponse().errorResponse(
                description="We couldn’t find any product with the provided ID."
            )

        has_purchased = OrderProducts.objects.filter(
            product_id=product.id,
            # store=store,
            order__in=Order.objects.filter(user=user, status='CREATED')
        ).exists()

        if not has_purchased:
            return CustomResponse().errorResponse(
                description="You can review this product only after purchasing it."
            )

        product_review = ProductReviews.objects.filter(user=user, product=product).first()
        if product_review:
            return CustomResponse().errorResponse(data={}, description="You have already submitted a review for this product.")
        rating = ProductReviews()
        rating.product = product
        rating.rating = payload.get("rating",5)
        rating.user = user
        rating.store = request.store
        rating.review = payload.get("review","")
        rating.save()
        product.number_of_reviews += 1
        totalrating = Decimal(product.rating) + Decimal(rating.rating)
        product.total_rating = totalrating
        avg_rating = totalrating/product.number_of_reviews
        product.rating = f"{avg_rating}"
        product.save()
        return CustomResponse().successResponse(data={})


    def get(self, request):
        product_id = request.GET.get("product_id")

        if not product_id:
            return CustomResponse().errorResponse(
                description="product_id is required"
            )

        product_review = ProductReviews.objects.filter(
            product_id=product_id
        ).values()

        return CustomResponse().successResponse(data=list(product_review))


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



