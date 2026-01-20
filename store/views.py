import uuid
from unicodedata import category
import requests
from django.contrib.admin.templatetags.admin_list import results
from django.db import transaction
from django.db import IntegrityError
from django.db.models import Q
from decimal import Decimal

from django.db.models.aggregates import Count, Avg
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny

from django.conf import settings
from db.models import AddressMaster, PinCode, Product, ProductVariant, Order, OrderProducts, Payment, OrderTimeLines, \
    Banner, Category, Cart, Wishlist, WebBanner, FlashSaleBanner, CashFree, Store, ProductReviews, ContactMessage, Tag
from enums.store import OrderStatus, PaymentStatus
from mixins.drf_views import CustomResponse
from utils.store import generate_order_id
from django.db.models import OuterRef, Subquery


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
        params = request.query_params
        # ---------- Query params ----------
        categories = params.get("category")  # comma-separated UUIDs
        gender = params.get("gender")
        tags = params.get("tags")  # comma-separated UUIDs
        min_price = params.get("min_price")
        max_price = params.get("max_price")

        page = int(params.get("page", 1))
        page_size = min(int(params.get("page_size", 10)), 50)

        # ---------- Base queryset ----------
        # queryset = ProductVariant.objects.filter(
        #     store=store,
        #     is_active=True
        # )
        queryset = ProductVariant.objects.filter(
            store=store,
            is_active=True
        ).select_related(
            "default_product"
        ).annotate(
            default_product_avg_rating=Avg("default_product__reviews__rating"),
            default_product_total_reviews=Count(
                "default_product__reviews", distinct=True
            ),
        )



        # ---------- Category filter (M2M) ----------
        if categories:
            category_ids = []
            for c in categories.split(","):
                try:
                    category_ids.append(uuid.UUID(c.strip()))
                except ValueError:
                    return CustomResponse.errorResponse(
                        description=f"Invalid category UUID: {c}"
                    )

            queryset = queryset.filter(categories__id__in=category_ids)

        # ---------- Tag filter (M2M) ----------
        if tags:
            tag_ids = []
            for t in tags.split(","):
                try:
                    tag_ids.append(uuid.UUID(t.strip()))
                except ValueError:
                    return CustomResponse.errorResponse(
                        description=f"Invalid tag UUID: {t}"
                    )

            queryset = queryset.filter(tags__id__in=tag_ids)

        # ---------- Gender ----------
        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        # ---------- Optimize relations ----------
        queryset = queryset.select_related(
            "default_product"
        ).prefetch_related(
            "default_product__media",
            "categories",
            "tags"
        ).distinct().order_by("-created_at")

        # ---------- Price filter (on default product) ----------
        if min_price:
            queryset = queryset.filter(
                default_product__selling_price__gte=min_price
            )

        if max_price:
            queryset = queryset.filter(
                default_product__selling_price__lte=max_price
            )

        # ---------- Pagination ----------
        total = queryset.count()
        offset = (page - 1) * page_size
        variants = queryset[offset: offset + page_size]

        # ---------- Response ----------
        data = []

        for v in variants:
            p = v.default_product

            thumbnail_media = [
                m.url for m in p.media.all()[:1]
            ]

            data.append({
                # ---- ProductVariant ----
                "product_variant_id": str(v.id),
                "lsin": v.lsin,
                "display_name": v.display_name,
                "description": v.description,
                "gender": v.gender,
                "is_active": v.is_active,
                # ---- Categories ----
                "categories": [
                    {"id": str(c.id), "name": c.name}
                    for c in v.categories.all()
                ],

                # ---- Tags ----
                "tags": [
                    {"id": str(t.id), "name": t.name}
                    for t in v.tags.all()
                ],

                # ---- Default Product (SKU) ----
                "default_product": {
                    "id": str(p.id),
                    "sku": p.sku,
                    "name": p.name,
                    "size": p.size,
                    "colour": p.colour,
                    "selling_price": str(p.selling_price),
                    "mrp": str(p.mrp),
                    "gst_percentage": p.gst_percentage,
                    "gst_amount": str(p.gst_amount) if p.gst_amount else None,
                    "current_stock": p.current_stock,
                    "thumbnail": thumbnail_media[0] if thumbnail_media else None,
                    "rating": round(v.default_product_avg_rating, 1)
                    if v.default_product_avg_rating else 0,
                    "number_of_reviews": v.default_product_total_reviews,
                }
            })

        return CustomResponse.successResponse(
            data=data,
            total=total
        )

class ProductDetailAPIView(APIView):
    permission_classes = [AllowAny]  # Public API

    def get(self, request, id):
        store = request.store
        try:
            variant = ProductVariant.objects.filter(
                store=store,
                id=id,
                is_active=True
            ).select_related(
                "default_product"
            ).prefetch_related(
                "products__media",
                "default_product__media",
                "categories",
                "tags"
            ).get()
        except ProductVariant.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Product not found"
            )

        # ---------- Build variants (products / SKUs) ----------
        variants_data = []

        for p in variant.products.all():
            variants_data.append({
                "id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "size": p.size,
                "colour": p.colour,
                "selling_price": str(p.selling_price),
                "mrp": str(p.mrp),
                "current_stock": p.current_stock,
                "media": [
                    {
                        "url": m.url,
                        "type": m.media_type,
                        "position": m.position
                    } for m in p.media.all()
                ]
            })

        # ---------- Final response ----------
        response_data = {
            "lsin": variant.lsin,
            "display_name": variant.display_name,
            "description": variant.description,
            "highlights": variant.highlights,
            "gender": variant.gender,
            "rating": variant.rating,
            "numbef_of_reviews": variant.number_of_reviews,
            "categories": [
                {"id": str(c.id), "name": c.name}
                for c in variant.categories.all()
            ],
            "tags": [
                {"id": str(t.id), "name": t.name}
                for t in variant.tags.all()
            ],
            "default_product": {
                "id": str(variant.default_product.id),
                "sku": variant.default_product.sku,
                "name": variant.default_product.name,
                "size": variant.default_product.size,
                "colour": variant.default_product.colour,
                "selling_price": str(variant.default_product.selling_price),
                "mrp": str(variant.default_product.mrp),
                "current_stock": variant.default_product.current_stock,
                "media": [
                    {
                        "url": m.url,
                        "type": m.media_type,
                        "position": m.position
                    } for m in variant.default_product.media.all()
                ],
            },
            "variants": variants_data,
        }
        return CustomResponse.successResponse(data=response_data)

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
            product_variant = ProductVariant.objects.get(
                store=store,
                id=product_id,
                is_active=True
            )
        except ProductVariant.DoesNotExist:
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
            product_variant = ProductVariant.objects.get(
                store=request.store,
                id=id,
                is_active=True
            )
        except ProductVariant.DoesNotExist:
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
            "product__default_product"
        ).prefetch_related(
            "product__default_product__media",
            "product__categories",
            "product__tags"
        ).order_by("-created_at")

        data = []

        for w in wishlists:
            v = w.product
            p = v.default_product

            # thumbnail
            thumbnail = None
            media_qs = p.media.all()
            if media_qs:
                thumbnail = media_qs[0].url

            data.append({
                "product_variant_id": str(v.id),
                "lsin": v.lsin,
                "display_name": v.display_name,
                "description": v.description,
                "gender": v.gender,
                "is_active": v.is_active,

                "default_product": {
                    "id": str(p.id),
                    "sku": p.sku,
                    "selling_price": str(p.selling_price),
                    "mrp": str(p.mrp),
                    "current_stock": p.current_stock,
                    "thumbnail": thumbnail
                },

                "categories": [
                    {"id": str(c.id), "name": c.name}
                    for c in v.categories.all()
                ],

                "tags": [
                    {"id": str(t.id), "name": t.name}
                    for t in v.tags.all()
                ]
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
        user = request.user
        payload = request.data
        store = request.store


        order_id = generate_order_id()
        address = payload.get("address", {})
        products = payload.get("products", [])
        selling_price = payload.get("selling_price", 0)
        coupon_discount = payload.get("coupon_discount", 0)
        wallet_paid = payload.get("wallet_paid", 0)
        amount = payload.get("amount", 0)
        mrp = payload.get("mrp", 0)
        print("DEBUG payload selling_price:", selling_price, type(selling_price))
        print("DEBUG payload coupon_discount:", coupon_discount, type(coupon_discount))
        print("DEBUG payload wallet_paid:", wallet_paid, type(wallet_paid))
        print("DEBUG payload amount:", amount, type(amount))
        print("DEBUG payload mrp:", mrp, type(mrp))



        if not products:
            return CustomResponse().errorResponse(description="Products required")

        try:
            with transaction.atomic():
                print("DEBUG order_id:", order_id, len(str(order_id)))


                #  Create Order
                order = Order.objects.create(
                    store_id=store.id,
                    order_id=order_id,
                    user_id=user.id,
                    address=address,
                    selling_price=selling_price,
                    coupon_discount=coupon_discount,
                    wallet_paid=wallet_paid,
                    amount=amount,
                    mrp = mrp,
                    status=OrderStatus.INITIATED
                )

                #  Create Order Products
                print("PRODUCTS:", products)
                print("TYPE:", type(products))

                for item in products:
                    print("ITEM:", item, type(item))

                    product = Product.objects.filter(id=item["product_id"]).first()
                    if not product:
                        raise ValueError("Invalid product selected")
                    print("DEBUG product.selling_price:", product.selling_price, type(product.selling_price))
                    print("DEBUG product.mrp:", product.mrp, type(product.mrp))
                    print("DEBUG product.gst_percentage:", product.gst_percentage, type(product.gst_percentage))
                    print("DEBUG before ratio:",
                          "product.selling_price =", product.selling_price, type(product.selling_price),
                          "selling_price =", selling_price, type(selling_price))


                    product_ratio = product.selling_price / selling_price
                    print("DEBUG coupon apportion:",
                          "coupon_discount =", coupon_discount, type(coupon_discount),
                          "product_ratio =", product_ratio, type(product_ratio))

                    product_discount = coupon_discount * product_ratio
                    product_wallet = wallet_paid * product_ratio
                    product_online = amount * product_ratio
                    print("DEBUG qty:", item.get("qty"), type(item.get("qty")))


                    product_total = product.selling_price * item["qty"]
                    print("DEBUG product_total:", product_total, type(product_total))
                    print("DEBUG product_discount:", product_discount, type(product_discount))
                    print("DEBUG product_wallet:", product_wallet, type(product_wallet))

                    taxable_amount = product_total - product_discount - product_wallet
                    gst_percentage = Decimal(product.gst_percentage)

                    base_amount = taxable_amount / (Decimal("1") + gst_percentage / Decimal("100"))
                    gst_amount = taxable_amount - base_amount



                    OrderProducts.objects.create(
                        store_id=store.id,
                        order_id=order_id,
                        product=product,
                        old_product_id=product.id,
                        sku=product.sku,
                        qty = int(item.get("qty", 0)),
                        mrp=product.mrp,
                        selling_price=product.selling_price,
                        Apportioned_discount=product_discount,
                        Apportioned_wallet=product_wallet,
                        Apportioned_gst=gst_amount,
                        Apportioned_online=product_online,



                    )

                #  Create Order Timeline
                OrderTimeLines.objects.create(
                    store_id=store.id,
                    order_id=order_id,
                    status=OrderStatus.INITIATED,
                    remarks=payload.get("remarks", "Order initiated")
                )

                #  Create Payment
                payment = Payment.objects.create(
                    store_id=store.id,
                    order_id=order_id,
                    amount=amount,
                    user_id=user.id,
                    mobile=user.mobile,
                    email=user.email,
                )
                cashfree = Store.objects.filter(
                    id=store.id
                ).first()

                if not cashfree:
                    raise ValueError("CashFree configuration not found for this store")



                payment_resp = initiateOrder(user, amount, order_id,cashfree)
                print("DEBUG cf_order_id:", payment_resp["cf_order_id"], len(payment_resp["cf_order_id"]))
                print("DEBUG payment_session_id:", payment_resp["payment_session_id"], len(payment_resp["payment_session_id"]))


                payment.session_id = payment_resp["payment_session_id"]
                payment.txn_id = payment_resp["cf_order_id"]
                payment.save(update_fields=["session_id", "txn_id"])



            return CustomResponse().successResponse(
                data=payment_resp,
                description="Order initiated. Please continue payment"
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                description=str(e) or "Failed to initiate order"
            )

def initiateOrder(user, amount, order_id,cashfree):
    """
    Initiate payment using school-specific CashFree credentials from the database.
    """
    print("DEBUG CASHFREE CLIENT ID:", cashfree.client_id)
    print("DEBUG CASHFREE CLIENT SECRET:", cashfree.client_secret)
    print("DEBUG CASHFREE URL:", cashfree.url)
    print("DEBUG CASHFREE WEBHOOK:", cashfree.webhook)

    # --- Prepare payload ---
    payload = {
        "order_currency": "INR",
        "order_amount": float(amount),
        "order_id": str(order_id),
        "customer_details": {
            "customer_id": str(user.id),
            "customer_phone": str(user.mobile),
            "customer_name": str(user.username),
        },
        "order_meta": {
            "notify_url": cashfree.webhook,
        },
    }

    # --- Prepare headers ---
    headers = {
        "x-api-version": settings.CASHFREE_API_VERSION,
        "x-client-id": cashfree.client_id,
        "x-client-secret": cashfree.client_secret,
        "Content-Type": "application/json",
    }
    print("headers",headers)
    print("payload",payload)


    try:
        # --- Send request to CashFree ---
        response = requests.post(cashfree.url, json=payload, headers=headers, timeout=15)


        # --- Validate response ---
        if response.status_code == 200:
            resp_json = response.json()
            cf_order_id = resp_json.get("cf_order_id")
            session_id = resp_json.get("payment_session_id")

            if cf_order_id and session_id:
                return {
                    "cf_order_id": cf_order_id,
                    "payment_session_id": session_id,
                    "order_id":order_id
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


class Webhook(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data

            event_type = data.get("type")
            order_id = data.get("data", {}).get("order", {}).get("order_id")

            print("Webhook received:", data)

            # Cashfree test webhook may not have real order_id
            if not order_id:
                print("Webhook test / invalid payload")
                return CustomResponse().successResponse(data={},
                    description="Webhook received"
                )

            payment = Payment.objects.filter(order_id=order_id).first()
            order = Order.objects.filter(order_id=order_id).first()

            # If no DB records → still return 200
            if not payment or not order:
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
                    order.paid_online = payment.amount
                    order.updated_by = SYSTEM_UPDATED_BY
                    order.save(update_fields=["status", "paid_online", "updated_by"])
                    # ordered_product_ids = OrderProducts.objects.filter(
                    #     order_id=order.order_id
                    # ).values_list("product_id", flat=True)
                    #
                    # Cart.objects.filter(
                    #     user_id=order.user_id,
                    #     store_id=order.store_id,
                    #     product_id__in=ordered_product_ids
                    # ).delete()

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



class PaymentStatusAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data

        order_id = data.get("order_id")
        frontend_status = data.get("status")

        if not order_id or not frontend_status:
            return CustomResponse().errorResponse(
                description="order_id and status are required"
            )

        payment = Payment.objects.filter(order_id=order_id).first()
        order = Order.objects.filter(order_id=order_id).first()

        if not payment or not order:
            return CustomResponse().errorResponse(
                description="Order or Payment not found"
            )

        # Do not override webhook-confirmed payment
        if payment.status == PaymentStatus.COMPLETED:
            return CustomResponse().successResponse(
                description="Payment already completed (webhook confirmed)"
            )

        # 🔥 FETCH CASHFREE STATUS
        cashfree = CashFree.objects.filter(store_id=order.store_id).first()
        if not cashfree:
            return CustomResponse().errorResponse(
                description="Cashfree configuration not found"
            )

        cf_response = fetch_cashfree_payment_status(order_id, cashfree)

        cf_order_status = cf_response.get("order_status")  # PAID / ACTIVE / FAILED
        verified_status = map_cashfree_status(cf_order_status)

        with transaction.atomic():

            payment.status = verified_status
            payment.save(update_fields=["status"])

            if verified_status == PaymentStatus.COMPLETED:
                order.status = OrderStatus.PLACED
                order.paid_online = payment.amount

            elif verified_status == PaymentStatus.FAILED:
                order.status = OrderStatus.FAILED

            elif verified_status == PaymentStatus.CANCELLED:
                order.status = OrderStatus.CANCELLED

            order.save(update_fields=["status", "paid_online"])

        return CustomResponse().successResponse(
            data={
                "order_id": order_id,
                "frontend_status": frontend_status,
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

def fetch_cashfree_payment_status(order_id, cashfree):
    url = f"{cashfree.url}/{order_id}"

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

    def get(self, request):
        user = request.user
        status = request.query_params.get("status")

        orders_qs = Order.objects.filter(user_id=user.id).order_by("-created_at")

        if status:
            orders_qs = orders_qs.filter(status=status)

        orders = list(orders_qs.values())

        return CustomResponse().successResponse(
            data=orders,
            total=len(orders)
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

class FlashSaleBannerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id=None):
        store = request.store
        action = request.query_params.get("action")

        queryset = FlashSaleBanner.objects.filter(
            is_active=True,
            store_id=store.id
        )

        # ACTION FILTER
        if action is not None:
            queryset = queryset.filter(action=action.lower() == "true")

        # ---------- SINGLE BANNER ----------
        if id:
            banner = queryset.filter(id=id).first()
            if not banner:
                return CustomResponse.errorResponse(
                    description="Active banner not found"
                )

            product_names = []
            if banner.product_id:
                product_names = list(
                    Product.objects.filter(
                        id__in=banner.product_id
                    ).values_list("name", flat=True)
                )

            return CustomResponse.successResponse(
                data=[{
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
                }],
                total=1
            )

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
        user_id = request.user.id
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
            store_id=store.id,
            user_id=user_id,
            product_id=product_id,
            defaults={"quantity": quantity}
        )

        new_quantity = quantity if created else cart_item.quantity + quantity

        if new_quantity > product.current_stock:
            return CustomResponse().errorResponse(
                description="Insufficient stock"
            )

        cart_item.quantity = new_quantity
        cart_item.save()

        return CustomResponse().successResponse(
            message="Product added to cart",
            data={
                "product_id": str(product_id),
                "quantity": cart_item.quantity
            }
        )






class CartListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        store = request.store



        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        if page < 1 or limit < 1:
            return CustomResponse().errorResponse(
                description="page and limit must be positive integers"
            )

        offset = (page - 1) * limit

        qs = Cart.objects.filter(user_id=user_id,store_id=store.id).order_by("-created_at")
        total = qs.count()

        cart_items = qs[offset: offset + limit]

        product_ids = [
            uuid.UUID(str(item.product_id))
            for item in cart_items
            if item.product_id
        ]

        products = Product.objects.filter(id__in=product_ids)
        product_map = {str(p.id): p for p in products}

        # 🔥 AUTO-REMOVE INVALID CART ITEMS
        invalid_cart_ids = [
            item.id for item in cart_items
            if str(item.product_id) not in product_map
        ]

        if invalid_cart_ids:
            Cart.objects.filter(id__in=invalid_cart_ids).delete()

        # BUILD RESPONSE (ONLY VALID ITEMS)
        data = []
        for item in cart_items:
            product = product_map.get(str(item.product_id))
            if not product:
                continue

            data.append({
                "cart_id": str(item.id),
                "quantity": item.quantity,
                "product": {
                    "id": str(product.id),
                    "sku": product.sku,
                    "name": product.name,
                    "size": product.size,
                    "colour": product.colour,
                    "mrp": product.mrp,
                    "selling_price": product.selling_price,
                    "inr": product.inr,
                    "gst_percentage": product.gst_percentage,
                    "gst_amount": product.gst_amount,
                    "current_stock": product.current_stock,
                    "thumbnail_image": product.thumbnail_image,
                    "images": product.images or [],
                    "videos": product.videos or [],
                }
            })

        return CustomResponse().successResponse(
            data=data,
            total=len(data)
        )




class UpdateCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        quantity = request.data.get("quantity")

        if not quantity or int(quantity) <= 0:
            return CustomResponse().errorResponse(
                description="Valid quantity is required"
            )

        try:
            cart_item = Cart.objects.get(
                id=id,
                user_id=request.user.id
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
        deleted, _ = Cart.objects.filter(
            id=id,
            user_id=request.user.id
        ).delete()

        if not deleted:
            return CustomResponse().errorResponse(
                description="Cart item not found",
            )

        return CustomResponse().successResponse(data={},
            description="Item removed from cart"
        )









class MoveWishlistToCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        store = request.store

        product_id = request.data.get("product_id")

        if not product_id:
            return CustomResponse().errorResponse(
                description="product_id is required"
            )

        wishlist_exists = Wishlist.objects.filter(
            user_id=user_id,
            product_id=product_id,
            store_id=store.id

        ).exists()

        if not wishlist_exists:
            return CustomResponse().errorResponse(
                description="Product not found in wishlist",
            )

        cart_item, created = Cart.objects.get_or_create(
            user_id=user_id,
            product_id=product_id,
            defaults={"quantity": 1}
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

        Wishlist.objects.filter(
            user_id=user_id,
            product_id=product_id
        ).delete()

        return CustomResponse().successResponse(data={},
            description="Product moved from wishlist to cart"
        )


class CartTotalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        store = request.store


        cart_items = Cart.objects.filter(user_id=user_id,store_id=store.id
)

        total_amount = 0
        items = []

        for item in cart_items:
            product = Product.objects.filter(id=item.product_id).first()
            price = product.selling_price if product else 0

            item_total = price * item.quantity
            total_amount += item_total

            items.append({
                "product_id": str(item.product_id),
                "quantity": item.quantity,
                "price": price,
                "total": item_total
            })

        return CustomResponse().successResponse(
            data={
                "items": items,
                "cart_total": total_amount
            },
            total=len(items)
        )


class Reviews(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def post(self, request):
        payload = request.data
        user = request.user
        store_id = request.store.id

        product_id = payload.get("product_id")
        if not product_id:
            return CustomResponse().errorResponse(
                description="product_id is required"
            )

        product = DisplayProduct.objects.filter(default_product_id=product_id).first()
        if not product:
            return CustomResponse().errorResponse(
                description="We couldn’t find any product with the provided ID."
            )


        has_purchased = OrderProducts.objects.filter(
            product_id=product.default_product_id,
            store_id=store_id,
            order_id__in=[
                str(order_id) for order_id in
                Order.objects.filter(user_id=user.id, status='Placed')
                .values_list("order_id", flat=True)
            ]
        ).exists()




        if not has_purchased:
            return CustomResponse().errorResponse(
                description="You can review this product only after purchasing it."
            )


        product_review = ProductReviews.objects.filter(user_id=user.id, product_id=payload["product_id"]).first()
        if product_review:
            return CustomResponse().errorResponse(data={}, description="You have already submitted a review for this product.")
        rating = ProductReviews()
        rating.product_id = payload.get("product_id","")
        rating.rating = payload.get("rating",5)
        rating.user_id = user.id
        rating.username = user.username
        rating.store_id = request.store.id
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



