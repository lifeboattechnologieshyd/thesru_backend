from django.contrib.auth.hashers import make_password, check_password
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from db.models import User, Student
from mixins.drf_views import CustomResponse
from serializers.user import UserMasterSerializer


class SignUpAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self,request):
        mobile = request.data.get("mobile")
        username = request.data.get("name")
        password = request.data.get("password")
        if User.objects.filter(mobile=mobile).exists():
            return CustomResponse.successResponse("mobile already exists.please login with password")

        if not mobile and username:
            return CustomResponse.errorResponse(description="mobile,name are required")
        user = User(mobile=mobile,username=username)
        user.password = make_password(password)
        user.save()


        return CustomResponse.successResponse(data={},description="successful")

class SignInAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self,request):
        mobile = request.data.get("mobile")
        password= request.data.get("password")

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            return CustomResponse().errorResponse(description="Invalid mobile or password")

        if check_password(password, user.password):
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            user_data = UserMasterSerializer(user).data
            return CustomResponse().successResponse(
                data={
                    "user": user_data,
                    "access": access_token,
                    "refresh": refresh_token,
                },
                description="Login successful"
            )
        else:
            return CustomResponse().errorResponse(description="Invalid mobile or password")



class StudentAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self,request):
        data = request.data

        Student.objects.create(
            name = data.get("name")
        )

        return CustomResponse.successResponse(data={},description="data saved")