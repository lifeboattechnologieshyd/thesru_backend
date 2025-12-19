from datetime import timedelta

from django.utils import timezone

from django.contrib.auth.hashers import make_password, check_password
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
import random

from db.models import User, UserOTP
from mixins.drf_views import CustomResponse
from serializers.user import UserMasterSerializer

from rest_framework import status

from utils.user import generate_username, generate_referral_code


class MobileSendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        mobile = request.data.get("mobile")

        if not mobile:
            return CustomResponse().errorResponse(
                description="Mobile number is required",
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check user by mobile
        user = User.objects.filter(mobile=mobile).first()
        is_new_user = False

        if not user:
            #  Create new user
            user = User.objects.create(
                mobile=mobile,
            )
            is_new_user = True

        #  Generate OTP
        otp = str(random.randint(1000, 9999))

        expires_at = timezone.now() + timedelta(minutes=5)

        # Invalidate old OTPs
        UserOTP.objects.filter(mobile=mobile, is_used=False).update(is_used=True)

        #  Save OTP
        UserOTP.objects.create(
            mobile=mobile,
            otp=otp,
            expires_at=expires_at
        )


        #  Generate JWT token (temporary access)

        return CustomResponse().successResponse(
            description="OTP sent successfully",
            data={
                "is_new_user": is_new_user,
                "mobile": mobile,
                "otp": otp,
            },
            status=status.HTTP_200_OK
        )


class MobileVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        mobile = request.data.get("mobile")
        otp = request.data.get("otp")
        device_id = request.data.get("device_id")

        # Validate input
        if not mobile or not otp:
            return CustomResponse().errorResponse(
                description="Mobile and OTP are required",
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate OTP
        otp_obj = (
            UserOTP.objects
            .filter(mobile=mobile, otp=otp, is_used=False)
            .order_by("-expires_at")
            .first()
        )

        if not otp_obj:
            return CustomResponse().errorResponse(
                description="Invalid OTP",
                status=status.HTTP_401_UNAUTHORIZED
            )

        if timezone.now() > otp_obj.expires_at:
            return CustomResponse().errorResponse(
                description="OTP has expired",
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Mark OTP as used
        otp_obj.is_used = True
        otp_obj.save(update_fields=["is_used"])

        # Fetch or create user
        user = User.objects.filter(mobile=mobile).first()
        is_new_user = False

        if not user:
            user = User.objects.create(
                mobile=mobile,
                device_id=device_id
            )
            is_new_user = True

        # Ensure username & referral code
        updated = False
        if not user.username:
            user.username = generate_username(user)
            updated = True

        if not user.referral_code:
            user.referral_code = generate_referral_code()
            updated = True

        if device_id and user.device_id != device_id:
            user.device_id = device_id
            updated = True

        if updated:
            user.save()

        #  Generate JWT tokens
        refresh = RefreshToken.for_user(user)


        #  Final response
        return CustomResponse().successResponse(
            description="OTP verified successfully",
            data={
                "is_new_user": is_new_user,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": str(user.id),
                    "mobile": user.mobile,
                    "username": user.username,
                    "referral_code": user.referral_code,
                    "device_id": user.device_id,
                }
            },
            status=status.HTTP_200_OK
        )






#