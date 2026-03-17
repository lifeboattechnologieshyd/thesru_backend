from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from db.models import User
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




