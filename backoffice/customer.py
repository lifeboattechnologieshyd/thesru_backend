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
            store=request.store
        )
        new_customer.username = data.get("name")
        new_customer.referral_code = generate_referral_code()
        new_customer.save()
        return CustomResponse().successResponse(data={}, description="Customer created successfully")


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



