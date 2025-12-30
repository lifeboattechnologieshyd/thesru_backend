from unicodedata import category
import requests
from django.db import transaction
from django.db import IntegrityError

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny

from django.conf import settings
from db.models import AddressMaster, PinCode, Product, DisplayProduct, Order, OrderProducts, Payment, OrderTimeLines, \
    Banner, Category
from enums.store import OrderStatus
from mixins.drf_views import CustomResponse
from utils.store import generate_order_id


class AddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        data = request.data
        required_fields = ["mobile","name","address_name","address_type","full_address",
                           "house_number","country","city","state","area","pin_code","landmark",
                           "is_default"

                           ]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")

        if data.get("is_default"):
            AddressMaster.objects.filter(user_id=request.user.id,is_default = True).update(is_default = False)

        AddressMaster.objects.create(
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
        if id:
            address = AddressMaster.objects.filter(id=id,user_id=request.user.id).first()
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
            "id" :str(pin.id),
            "pin":pin.pin,
            "state":pin.state,
            "city":pin.city,
            "area":pin.area
        }

        return CustomResponse.successResponse(data=[data],total=1)

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


class ProductListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category = request.query_params.get("category")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))


        queryset = DisplayProduct.objects.filter(
            is_active=True,
        )

        if category:
            queryset = queryset.filter(category__contains=[category])
        #     gender,tags,



        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        data = []
        for product in queryset:
            data.append({
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
                })

        return CustomResponse.successResponse(
            data=data,
            total=total
        )


class ProductDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, default_product_id):
        #  Fetch DisplayProduct using default_product_id
        display_product = DisplayProduct.objects.filter(
            id=default_product_id,
            is_active=True
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

        order_id = generate_order_id()
        address = payload.get("address", {})
        products = payload.get("products", [])
        selling_price = payload.get("selling_price", 0)
        coupon_discount = payload.get("coupon_discount", 0)
        wallet_paid = payload.get("wallet_paid", 0)
        amount = payload.get("amount", 0)

        if not products:
            return CustomResponse().errorResponse(description="Products required")

        try:
            with transaction.atomic():

                #  Create Order
                order = Order.objects.create(
                    order_id=order_id,
                    user_id=user.id,
                    address=address,
                    selling_price=selling_price,
                    coupon_discount=coupon_discount,
                    wallet_paid=wallet_paid,
                    amount=amount,
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

                    product_ratio = product.selling_price / selling_price
                    product_discount = coupon_discount * product_ratio
                    product_wallet = wallet_paid * product_ratio
                    product_online = amount * product_ratio

                    product_total = product.selling_price * item["qty"]
                    taxable_amount = product_total - product_discount - product_wallet
                    base_amount = taxable_amount / (1 + product.gst_percentage)
                    gst_amount = taxable_amount - base_amount

                    OrderProducts.objects.create(
                        order=order,
                        product_id=product.id,
                        sku=product.sku,
                        qty=item["qty"],
                        mrp=product.mrp,
                        selling_price=product.selling_price,
                        Apportioned_discount=product_discount,
                        Apportioned_wallet=product_wallet,
                        Apportioned_gst=gst_amount,
                        Apportioned_online=product_online
                    )

                #  Create Order Timeline
                OrderTimeLines.objects.create(
                    order=order,
                    status=OrderStatus.INITIATED,
                    remarks=payload.get("remarks", "Order initiated")
                )

                #  Create Payment
                payment = Payment.objects.create(
                    order=order,
                    amount=amount,
                    user_id=user.id,
                    mobile=user.mobile,
                    email=user.email,
                )

                payment_resp = initiateOrder(user, amount, order_id)

                payment.session_id = payment_resp["cf_order_id"]
                payment.txn_id = payment_resp["payment_session_id"]
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
            "notify_url": settings.CASHFREE_WEBHOOK,
        },
    }

    # --- Prepare headers ---
    headers = {
        "x-api-version": settings.CASHFREE_API_VERSION,
        "x-client-id": cashfree.client_id,
        "x-client-secret": cashfree.client_secret,
        "Content-Type": "application/json",
    }


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
                }
            else:
                raise Exception("Could not found cf_order_id and payment_session_id")
        else:
            raise Exception("Response code is not 200")
    except Exception as e:
        raise Exception(e)


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
        action = request.query_params.get("action")

        queryset = Banner.objects.filter(is_active=True)

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

# class CategoryListView(APIView):
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

        queryset = Category.objects.filter(is_active=True)

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
