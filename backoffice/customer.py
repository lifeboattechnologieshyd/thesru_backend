from django.utils import timezone

from django.db.models import Q, OuterRef, Subquery, Count, Sum
from django.forms import model_to_dict
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from db.models import User, AddressMaster
from mixins.drf_views import CustomResponse
from utils.user import generate_referral_code


class CustomerCreation(APIView):

    permission_classes = [IsAuthenticated]
    def post(self, request):
        data = request.data
        store = request.store
        user = request.user
        if "ADMIN" not in user.user_role:
            return CustomResponse().errorResponse(data={}, description="You don't have access to add customer")
        customer = User.objects.filter(mobile=data.get("mobile"), store=store).first()
        if customer:
            return CustomResponse().errorResponse(data={}, description="Customer with same mobile number already Exists")
        username = User.objects.filter(username=data.get("name"), store=store).first()
        if username:
            return CustomResponse().errorResponse(data={}, description="this username is not available")
        new_customer = User.objects.create(
            mobile=data.get("mobile"),
            store=request.store,
            username=data.get("name"),
            name=data.get("name"),
            referral_code=generate_referral_code(),
            created_by='ADMIN - '+ user.mobile,
        )
        new_customer.save()
        return CustomResponse().successResponse(
            data=model_to_dict(new_customer),
            description="Customer created successfully"
        )


class UserAddress(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if "ADMIN" not in user.user_role:
            return CustomResponse().errorResponse(data={}, description="You don't have access to add customer")

        mobile = request.query_params.get("mobile")
        store = request.store
        address = AddressMaster.objects.filter(store_id=store.id, mobile=mobile, is_default=True).values()
        if address:
            return CustomResponse().successResponse(data=address.first())
        else:
            return CustomResponse().errorResponse(data={}, description="No Address found for this user")

    def post(self, request):
        data = request.data
        user = request.user
        store = request.store

        if "ADMIN" not in user.user_role:
            return CustomResponse().errorResponse(data={}, description="You don't have access to add customer")

        required_fields = [
            "mobile", "name", "address_name", "address_type", "full_address",
            "house_number", "country", "city", "state", "area", "pin_code",
            "is_default", "user_id"
        ]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(description=f"{field} is required")
        customer = User.objects.filter(id=data.get("user_id"), store=store).first()
        if not customer:
            return CustomResponse.errorResponse(description="no customer with given id found")

        AddressMaster.objects.create(
            store_id=store.id,
            user_id=customer.id,
            mobile=data.get("mobile"),
            name=data.get("name"),
            address_name=data.get("address_name"),
            address_type=data.get("address_type"),
            full_address=data.get("full_address"),
            house_number=data.get("house_number"),
            country=data.get("country"),
            city=data.get("city"),
            state=data.get("state"),
            area=data.get("area"),
            pin_code=data.get("pin_code"),
            landmark=data.get("landmark", ""),
            is_default=data.get("is_default"),
        )
        return CustomResponse.successResponse(data={}, description="shipping address added successfully")



class BackofficeCustomerListAPI(APIView):

    def get(self, request):

        roles = request.user.user_role or []
        if "ADMIN" not in roles:
            return CustomResponse().errorResponse(
                description="Access denied"
            )

        store_id = request.store.id

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        search = request.query_params.get("search")
        state = request.query_params.get("state")
        district = request.query_params.get("district")
        paid_user = request.query_params.get("paid_user")

        users = User.objects.filter(store_id=store_id)
        # users = User.objects.all()

        # ---------------- search ----------------

        if search:
            users = users.filter(
                Q(name__icontains=search) |
                Q(mobile__icontains=search)
            )

        # ---------------- address subquery ----------------

        address_qs = AddressMaster.objects.filter(
            user_id=OuterRef("id"),
            store_id=store_id,
            is_default=True
        )

        users = users.annotate(
            state_name=Subquery(address_qs.values("state")[:1]),
            district_name=Subquery(address_qs.values("city")[:1])
        )

        # ---------------- filters ----------------

        if state:
            users = users.filter(state_name=state)

        if district:
            users = users.filter(district_name=district)

        # ---------------- orders aggregation ----------------

        users = users.annotate(
            total_orders=Count(
                "orders",
                filter=Q(
                    orders__store_id=store_id,
                    orders__status__in=[
                        "PACKED",
                        "DELIVERED",
                        "SHIPPED",
                        "CREATED"
                    ]
                )
            ),
            total_amount_paid=Sum(
                "orders__amount",
                filter=Q(
                    orders__store_id=store_id,
                    orders__status__in=[
                        "CREATED",
                        "PACKED",
                        "DELIVERED",
                        "SHIPPED",
                    ]
                )
            )
        )

        # ---------------- paid filter ----------------

        if paid_user == "true":
            users = users.filter(total_orders__gt=0)

        if paid_user == "false":
            users = users.filter(
                Q(total_orders=0) | Q(total_orders__isnull=True)
            )

        total_count = users.count()

        start = (page - 1) * page_size
        end = start + page_size

        users = users[start:end]

        data = []

        for u in users:
            data.append({
                "id": u.id,
                "name": u.name,
                "mobile": u.mobile,
                "state": u.state_name,
                "district": u.district_name,
                "is_paid_user": (u.total_orders or 0) > 0,
                "total_orders": u.total_orders or 0,
                "total_amount_paid": u.total_amount_paid or 0,
            })

        return CustomResponse().successResponse(
            description="Customer list",
            total=total_count,
            data=data
        )
