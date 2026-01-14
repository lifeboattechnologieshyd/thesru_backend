import uuid
from unicodedata import category
import requests
from django.db import transaction
from django.db import IntegrityError
from django.db.models import Q
from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny

from django.conf import settings
from db.models import AddressMaster, PinCode, Product, DisplayProduct, Order, OrderProducts, Payment, OrderTimeLines, \
    Banner, Category, Cart, Wishlist, WebBanner, FlashSaleBanner, CashFree, Store, ProductReviews
from enums.store import OrderStatus, PaymentStatus
from mixins.drf_views import CustomResponse
from utils.store import generate_order_id


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

# class ProductAPIView(APIView):
#     permission_classes = [AllowAny]
#
#     def get(self, request):
#         category = request.query_params.get("category")
#
#         if not category:
#             return CustomResponse.errorResponse(
#                 description="category is required"
#             )
#
#         #  Filter display products by category
#         display_products = (
#             DisplayProduct.objects
#             .filter(is_active=True, category__contains=[category])
#             .order_by("-created_at")
#         )
#
#         if not display_products.exists():
#             return CustomResponse.successResponse(
#                 data=[],
#                 total=0,
#                 description="No products found for this category"
#             )
#
#         response_data = []
#
#         for dp in display_products:
#             #  Fetch variant products
#             variants = []
#             if dp.variant_product_id:
#                 variant_qs = Product.objects.filter(
#                     id__in=dp.variant_product_id
#                 )
#
#                 for v in variant_qs:
#                     variants.append({
#                         "id": str(v.id),
#                         "name": v.name,
#                         "size": v.size,
#                         "colour": v.colour,
#                         "mrp": v.mrp,
#                         "selling_price": v.selling_price,
#                         "gst_percentage": v.gst_percentage,
#                         "gst_amount": v.gst_amount,
#                         "current_stock": v.current_stock,
#                         "images": v.images,
#                         "videos": v.videos,
#                         "thumbnail_image": v.thumbnail_image,
#                     })
#
#             # Display product payload
#             response_data.append({
#                 "display_product_id": str(dp.id),
#                 "product_name": dp.product_name,
#                 "product_tagline": dp.product_tagline,
#                 "description": dp.description,
#                 "highlights": dp.highlights,
#                 "category": dp.category,
#                 "gender": dp.gender,
#                 "age": dp.age,
#                 "rating": dp.rating,
#                 "number_of_reviews": dp.number_of_reviews,
#                 "tags": dp.tags,
#                 "search_tags": dp.search_tags,
#                 "variants": variants,
#             })
#
#         return CustomResponse.successResponse(
#             data=response_data,
#             total=len(response_data),
#             description="Products fetched successfully"
#         )


# class ProductListAPIView(APIView):
#     permission_classes = [AllowAny]
#
#     def get(self, request):
#         category = request.query_params.get("category")
#         page = int(request.query_params.get("page", 1))
#         page_size = int(request.query_params.get("page_size", 10))
#
#
#         queryset = DisplayProduct.objects.filter(
#             is_active=True,
#         )
#
#         if category:
#             queryset = queryset.filter(category__contains=[category])
#         #     gender,tags,
#
#
#
#         total = queryset.count()
#         offset = (page - 1) * page_size
#         queryset = queryset[offset:offset + page_size]
#
#         data = []
#         for product in queryset:
#             data.append({
#                     "id": str(product.id),
#                     "default_product_id": str(product.default_product_id),
#                     "variant_product_id": product.variant_product_id or [],
#                     "category": product.category,
#                     "gender": product.gender,
#                     "tags": product.tags,
#                     "search_tags": product.search_tags,
#                     "product_name": product.product_name,
#                     "product_tagline": product.product_tagline,
#                     "age": product.age,
#                     "description": product.description,
#                     "highlights": product.highlights,
#                     "rating": product.rating,
#                     "number_of_reviews": product.number_of_reviews,
#                     "is_active": product.is_active,
#                 })
#
#         return CustomResponse.successResponse(
#             data=data,
#             total=total
#         )


class ProductListAPIView(APIView):
    permission_classes = [AllowAny]


    def get(self, request):
        store_id = request.store.id

        # ---------- Query params ----------
        categories = request.query_params.get("category")
        gender = request.query_params.get("gender")
        tags = request.query_params.get("tags")  # comma-separated
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        # ---------- DisplayProduct base queryset ----------
        queryset = DisplayProduct.objects.filter(is_active=True,store_id=store_id)


        if categories:
            category_list = []

            for c in categories.split(","):
                c = c.strip()
                if not c:
                    continue
                try:
                    # Validate UUID
                    uuid.UUID(c)
                    category_list.append(c)
                except ValueError:
                    return CustomResponse.errorResponse(
                        description=f"Invalid category UUID: {c}"
                    )

            queryset = queryset.filter(category__overlap=category_list)


        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            queryset = queryset.filter(tags__overlap=tag_list)

        # ---------- Pagination ----------
        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        # ---------- Fetch related products ----------
        product_ids = queryset.values_list("default_product_id", flat=True)

        product_qs = Product.objects.filter(id__in=product_ids,store_id=store_id)

        # ---------- Price filters (Product table) ----------
        if min_price:
            product_qs = product_qs.filter(selling_price__gte=min_price)

        if max_price:
            product_qs = product_qs.filter(selling_price__lte=max_price)

        products = list(product_qs)
        product_map = {str(p.id): p for p in products}

        data = []

        for display in queryset:
            product = product_map.get(str(display.default_product_id))

            # Skip if price filter excluded the product
            if (min_price or max_price) and not product:
                continue

            data.append({
                # ---------- unified product identity ----------
                "default_product_id": str(display.default_product_id),

                # ---------- DisplayProduct fields ----------
                "category": display.category,
                "gender": display.gender,
                "tags": display.tags,
                "search_tags": display.search_tags,
                "product_name": display.product_name,
                "product_tagline": display.product_tagline,
                "age": display.age,
                "description": display.description,
                "highlights": display.highlights,
                "rating": display.rating,
                "number_of_reviews": display.number_of_reviews,
                "is_active": display.is_active,

                # ---------- Product fields ----------
                "name": product.name if product else None,
                "size": product.size if product else None,
                "colour": product.colour if product else None,

                "selling_price": str(product.selling_price) if product else None,
                "mrp": str(product.mrp) if product else None,

                "gst_percentage": product.gst_percentage if product else None,
                "gst_amount": str(product.gst_amount) if product else None,

                "current_stock": product.current_stock if product else 0,
                "images": product.images if product else [],
                "videos": product.videos if product else [],
                "thumbnail_image": product.thumbnail_image if product else None,
            })

        return CustomResponse.successResponse(
            data=data,
            total=total
        )


# class WishlistListAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         user_id = request.user.id
#
#         page = int(request.query_params.get("page", 1))
#         limit = int(request.query_params.get("limit", 10))
#
#         if page < 1 or limit < 1:
#             return CustomResponse().errorResponse(
#                 description="page and limit must be positive integers"
#             )
#
#         offset = (page - 1) * limit
#
#         # ---------- WISHLIST QUERY ----------
#         qs = Wishlist.objects.filter(user_id=user_id).order_by("-created_at")
#         total = qs.count()
#
#         wishlist_items = qs[offset: offset + limit]
#
#         # ---------- FETCH PRODUCTS (ONE QUERY) ----------
#         product_ids = [item.product_id for item in wishlist_items]
#
#         products = Product.objects.filter(id__in=product_ids)
#         product_map = {str(p.id): p for p in products}
#
#         # ---------- BUILD RESPONSE ----------
#         data = []
#         for item in wishlist_items:
#             product = product_map.get(str(item.product_id))
#
#             data.append({
#                 "wishlist_id": str(item.id),
#
#                 # ---- PRODUCT DETAILS ----
#                 "product": {
#                     "id": str(product.id) if product else None,
#                     "sku": product.sku if product else None,
#                     "name": product.name if product else None,
#                     "size": product.size if product else None,
#                     "colour": product.colour if product else None,
#                     "mrp": product.mrp if product else None,
#                     "selling_price": product.selling_price if product else None,
#                     "inr": product.inr if product else None,
#                     "gst_percentage": product.gst_percentage if product else None,
#                     "gst_amount": product.gst_amount if product else None,
#                     "current_stock": product.current_stock if product else None,
#                     "thumbnail_image": product.thumbnail_image if product else None,
#                     "images": product.images if product else [],
#                     "videos": product.videos if product else [],
#
#                 }
#             })
#
#         return CustomResponse().successResponse(
#             data=data,
#             total=total
#         )


class WishlistListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        store = request.store


        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse.errorResponse(
                description="page and page_size must be positive integers"
            )

        offset = (page - 1) * page_size

        # ------------------------------------------------
        # 1️⃣ Wishlist
        # ------------------------------------------------
        wishlist_qs = Wishlist.objects.filter(
            user_id=user_id,store_id=store.id

        ).order_by("-created_at")

        wishlist_items = wishlist_qs[offset: offset + page_size]

        product_ids = [str(w.product_id) for w in wishlist_items]

        if not product_ids:
            return CustomResponse.successResponse(data=[], total=0)

        # ------------------------------------------------
        # 2️⃣ Products (default + variants)
        # ------------------------------------------------
        products = Product.objects.filter(id__in=product_ids)

        product_map = {
            str(p.id): p for p in products
        }

        # ------------------------------------------------
        # 3️⃣ DisplayProducts (MATCH DEFAULT OR VARIANT)
        # ------------------------------------------------
        display_products = DisplayProduct.objects.filter(
            Q(default_product_id__in=product_ids) |
            Q(variant_product_id__overlap=product_ids),
            is_active=True
        )

        # Build lookup:
        # product_id -> display_product
        display_map = {}

        for dp in display_products:
            # default product
            display_map[str(dp.default_product_id)] = dp

            # variant products
            if dp.variant_product_id:
                for vid in dp.variant_product_id:
                    display_map[str(vid)] = dp

        # ------------------------------------------------
        # 4️⃣ RESPONSE
        # ------------------------------------------------
        data = []

        for item in wishlist_items:
            pid = str(item.product_id)

            product = product_map.get(pid)
            if not product:
                continue  # product truly missing (rare)

            display = display_map.get(pid)  # may be same DP for both

            data.append({
                # Wishlist
                "wishlist_id": str(item.id),

                # DisplayProduct (same for default + variant)
                "product_id": pid,
                "category": display.category if display else [],
                "gender": display.gender if display else None,
                "tags": display.tags if display else [],
                "search_tags": display.search_tags if display else [],
                "product_name": display.product_name if display else product.name,
                "product_tagline": display.product_tagline if display else None,
                "age": display.age if display else 0,
                "description": display.description if display else None,
                "highlights": display.highlights if display else [],
                "rating": display.rating if display else None,
                "number_of_reviews": display.number_of_reviews if display else 0,
                "is_active": display.is_active if display else False,

                #  Product (DIFFERENT for default & variant)
                "sku": product.sku,
                "name": product.name,
                "size": product.size,
                "colour": product.colour,
                "selling_price": str(product.selling_price),
                "mrp": str(product.mrp),
                "gst_percentage": product.gst_percentage,
                "gst_amount": str(product.gst_amount),
                "current_stock": product.current_stock,
                "images": product.images or [],
                "videos": product.videos or [],
                "thumbnail_image": product.thumbnail_image,
            })


        return CustomResponse.successResponse(
            data=data,
            total=len(data)
        )

class ProductDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        store = request.store

        #  Fetch DisplayProduct using default_product_id
        display_product = DisplayProduct.objects.filter(
            default_product_id=id,
            is_active=True,
            store_id=store.id

        ).first()

        if not display_product:
            return CustomResponse.errorResponse(
                description="Product not found"
            )

        #  Fetch Variant Products
        variants = Product.objects.filter(
            id__in=display_product.variant_product_id or []
        )

        variant_data = []
        for v in variants:
            variant_data.append({
                "id": str(v.id),
                "sku": v.sku,
                "name": v.name,
                "size": v.size,
                "colour": v.colour,
                "mrp": v.mrp,
                "selling_price": v.selling_price,
                "mrp_others": v.mrp_others,
                "selling_price_others": v.selling_price_others,
                "inr": v.inr,
                "gst_percentage": v.gst_percentage,
                "gst_amount": v.gst_amount,
                "current_stock": v.current_stock,
                "images": v.images,
                "videos": v.videos,
                "thumbnail_image": v.thumbnail_image,
            })

        return CustomResponse.successResponse(
            data={
                #  DISPLAY PRODUCT
                "id": str(display_product.id),
                "default_product_id": str(display_product.default_product_id),
                "variant_product_id": display_product.variant_product_id or [],
                "is_active": display_product.is_active,
                "category": display_product.category,
                "gender": display_product.gender,
                "tags": display_product.tags,
                "search_tags": display_product.search_tags,
                "product_name": display_product.product_name,
                "product_tagline": display_product.product_tagline,
                "age": display_product.age,
                "description": display_product.description,
                "highlights": display_product.highlights,
                "rating": display_product.rating,
                "number_of_reviews": display_product.number_of_reviews,

                #  VARIANTS
                "variants": variant_data
            },
            description="Product details fetched successfully"
        )

#
# class InitiateOrder(APIView):
#
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request):
#         user = request.user
#         order_id = generate_order_id()
#         payload = request.data
#         address = payload.get("address", {})
#         products = payload.get("products", [])
#         selling_price = payload.get("selling_price", 0)
#         coupon_discount = payload.get("coupon_discount", 0)
#         wallet_paid = payload.get("wallet_paid", 0)
#         amount = payload.get("amount", 0)
#         # create record in order table
#         order = Order()
#         order.order_id = order_id
#         order.user_id = user.id
#         order.address = address
#         order.selling_price = selling_price
#         order.coupon_discount = coupon_discount
#         order.wallet_paid = wallet_paid
#         order.amount = amount
#         order.status = OrderStatus.INITIATED
#         # create record in order_products
#         for item in products:
#             o_product = OrderProducts()
#             o_product.order_id = order_id
#             product = Product.object.filter(id=item["product_id"]).first()
#             if not product:
#                 return CustomResponse().errorResponse(data={}, description="Something wrong with product selection")
#             product_ratio = product.selling_price / selling_price
#             product_discount = coupon_discount * product_ratio
#             product_wallet = wallet_paid * product_ratio
#             product_online = amount * product_ratio
#             product_total = product.selling_price * item["qty"]
#             taxable_amount = product_total - product_discount - product_wallet
#             base_amount = taxable_amount / (1 + product.gst_percentage)
#             gst_amount = taxable_amount - base_amount
#             o_product.product_id = product.id
#             o_product.sku = product.sku
#             o_product.qty = item["qty"]
#             o_product.mrp = item.mrp
#             o_product.selling_price = product.selling_price
#             o_product.Apportioned_discount = product_discount
#             o_product.Apportioned_wallet = product_wallet
#             o_product.Apportioned_gst = gst_amount
#             o_product.Apportioned_online = product_online
#             o_product.save()
#         order.save()
#
#         # create record in payment table
#         payment = Payment()
#         payment.order_id = order_id
#         payment.amount = amount
#         payment.user_id = user.id
#         payment.mobile = user.mobile
#         payment.email = user.email
#         # contact cashfree
#         payment_resp = initiateOrder(user, amount, order_id,)
#         payment.session_id = payment_resp["cf_order_id"]
#         payment.txn_id = payment_resp["payment_session_id"]
#         payment.save()
#         # create record in timeline
#
#         timeline = OrderTimeLines()
#         timeline.order_id = order_id
#         timeline.status = OrderStatus.INITIATED
#         timeline.remarks = payload.get("remarks")
#
#
#
#         # prepare the response
#         return CustomResponse().successResponse(data=payment_resp, description="Order initiated. Please continue the payment flow")

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
                        product_id=product.id,
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


# class BannerListView(APIView):
#     permission_classes = [AllowAny]
#
#     def get(self, request, id=None):
#         action = request.query_params.get("action")
#
#         # BASE QUERY → only active banners
#         queryset = Banner.objects.filter(is_active=True)
#
#         #  ACTION FILTER (optional)
#         if action is not None:
#             if action.lower() == "true":
#                 queryset = queryset.filter(action=True)
#             elif action.lower() == "false":
#                 queryset = queryset.filter(action=False)
#
#         #  SINGLE BANNER (active only)
#         if id:
#             banner = (
#                 queryset
#                 .filter(id=id)
#                 .values()
#                 .first()
#             )
#
#             if not banner:
#                 return CustomResponse.errorResponse(
#                     description="Active banner not found"
#                 )
#
#             return CustomResponse.successResponse(
#                 data=[banner],
#                 total=1
#             )
#
#         # LIST BANNERS
#         banners = queryset.order_by("-created_at").values()
#         data = list(banners)
#
#         return CustomResponse.successResponse(
#             data=data,
#             total=len(data)
#         )

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

# # class CategoryListView(APIView):
#     permission_classes = [AllowAny]
#
#     def get(self, request, id=None):
#
#         #  SINGLE CATEGORY (only active)
#         if id:
#             category = (
#                 Category.objects
#                 .filter(id=id, is_active=True)
#                 .values()
#                 .first()
#             )
#
#             if not category:
#                 return CustomResponse.errorResponse(
#                     description="Active category not found"
#                 )
#
#             return CustomResponse.successResponse(
#                 data=[category],
#                 total=1
#             )
#
#         #  LIST ALL ACTIVE CATEGORIES
#         categories = (
#             Category.objects
#             .filter(is_active=True)
#             .order_by("-created_at")
#             .values()
#         )
#
#         data = list(categories)
#
#         return CustomResponse.successResponse(
#             data=data,
#             total=len(data)
#         )

class CategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id=None):
        store = request.store


        queryset = Category.objects.filter(is_active=True,store_id=store.id
)

        # SINGLE CATEGORY
        if id:
            category = queryset.filter(id=id).first()

            if not category:
                return CustomResponse.errorResponse(
                    description="Active category not found"
                )

            return CustomResponse.successResponse(
                data=[{
                    "id": str(category.id),
                    "name": category.name,
                    "icon": category.icon,
                    "search_tags": category.search_tags,
                    "is_active": category.is_active,

                }],
                total=1
            )

        #  LIST ALL CATEGORIES
        data = []
        for category in queryset.order_by("-created_at"):
            data.append({
                "id": str(category.id),
                "name": category.name,
                "icon": category.icon,
                "search_tags": category.search_tags,
                "is_active": category.is_active,

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


#
# class CartListAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         user_id = request.user.id
#         page = int(request.query_params.get("page", 1))
#         limit = int(request.query_params.get("limit", 10))
#         offset = (page - 1) * limit
#
#         qs = Cart.objects.filter(user_id=user_id)
#         total = qs.count()
#
#         data = qs.values(
#             "id", "product_id", "quantity"
#         )[offset:offset + limit]
#
#         return CustomResponse().successResponse(
#             data=list(data),
#             total=total
#         )




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

class AddToWishlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        store = request.store
        product_id = request.data.get("product_id")

        if not product_id:
            return CustomResponse().errorResponse(
                description="product_id is required"
            )

        obj, created = Wishlist.objects.get_or_create(
            store_id=store.id,
            user_id=user_id,
            product_id=product_id
        )

        if not created:
            return CustomResponse().successResponse(data={},
                description="Product already in wishlist"
            )

        return CustomResponse().successResponse(data={},
            description="Product added to wishlist"
        )


# class WishlistListAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         user_id = request.user.id
#         page = int(request.query_params.get("page", 1))
#         limit = int(request.query_params.get("limit", 10))
#         offset = (page - 1) * limit
#
#         qs = Wishlist.objects.filter(user_id=user_id)
#         total = qs.count()
#
#         data = qs.values(
#             "id", "product_id"
#         )[offset:offset + limit]
#
#         return CustomResponse().successResponse(
#             data=list(data),
#             total=total
#         )



class RemoveFromWishlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        deleted, _ = Wishlist.objects.filter(
            id=id,
            user_id=request.user.id
        ).delete()

        if not deleted:
            return CustomResponse().errorResponse(
                description="Wishlist item not found",
            )

        return CustomResponse().successResponse(data={},
            description="Item removed from wishlist"
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
    permission_classes = [IsAuthenticated]

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
        user = request.user
        product_id = request.GET.get("product_id")

        if not product_id:
            return CustomResponse().errorResponse(
                description="product_id is required"
            )

        product_review = ProductReviews.objects.filter(
            user_id=user.id,
            product_id=product_id
        ).values()

        return CustomResponse().successResponse(data=list(product_review))





