from datetime import timedelta, datetime

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from psutil import users
from rest_framework.parsers import FormParser, MultiPartParser
from django.conf import settings

from django.contrib.auth.hashers import make_password, check_password
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
import random

from config.settings.common import DEBUG
from db.models import User, UserOTP, TempUser, Store, UserSession
from db.models.user import AppVersionConfig, Visitor, Enrollments, IftarBookings
from enums.store import NotificationEvent
from mixins.drf_views import CustomResponse
from serializers.user import UserMasterSerializer

from rest_framework import status

from utils.notification import trigger_notification
from utils.storage import add_unique_suffix_to_filename, sanitize_filename, StoreS3Storage
from utils.user import generate_username, generate_referral_code, generate_otp, version_to_tuple, \
    send_otp_email


class MobileSendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        store = request.store
        mobile = request.data.get("mobile")
        if not mobile:
            return CustomResponse().errorResponse(
                description="Mobile number is required",
                status=status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.filter(mobile=mobile).first()
        is_new_user = not bool(user)

        # if is_new_user:
        #     TempUser.objects.update_or_create(mobile=mobile, store=request.store)

        if  mobile == "9014083090":
            otp = 1234
        else:
            otp = generate_otp()
        context = {
               "var": f"{otp}|"
        }
        trigger_notification(store,
                            NotificationEvent.OTP_AUTHENTICATION,
                            context,
                            mobile)

        expires_at = timezone.now() + timedelta(minutes=15)
        UserOTP.objects.filter(
            store=request.store,
            mobile=mobile,
            is_used=False
        ).update(is_used=True)

        # Save OTP with store
        UserOTP.objects.create(
            store=request.store,
            mobile=mobile,
            otp=otp,
            expires_at=expires_at
        )

        return CustomResponse().successResponse(
            description="OTP sent successfully",
            data={
                "is_new_user": is_new_user,
                "mobile": mobile,
                "otp": otp,
            },
            status=status.HTTP_200_OK
        )


class AdminLogin(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        mobile = request.data.get("mobile")
        user = User.objects.filter(mobile=mobile).first()
        if user and 'SUPERADMIN' in user.user_role:
            refresh = RefreshToken.for_user(user)
            data = {
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            }
            return CustomResponse().successResponse(data=data)
        else:
            return CustomResponse().errorResponse(data={}, description="Login Failed")


class CreateAdmin(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        user = User.objects.create(
            mobile="9014083090",
            device_id="123456",
        )
        user.username = generate_username(user)
        user.user_role = ['SUPERADMIN']
        user.referral_code = generate_referral_code()
        user.save()
        return CustomResponse().successResponse(
            description="Admin Created Successfully",
            data={},
            status=status.HTTP_200_OK
        )

class MobileVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        mobile = request.data.get("mobile")
        otp = request.data.get("otp")
        device_id = request.data.get("device_id")

        if not mobile or not otp:
            return CustomResponse().errorResponse(
                description="Mobile and OTP are required",
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------- Validate OTP ----------------
        otp_obj = (
            UserOTP.objects
            .filter(
                store=request.store,
                mobile=mobile,
                otp=otp,
                is_used=False
            )
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

        # ---------------- Check existing user ----------------
        user = User.objects.filter(
            mobile=mobile,
            store=request.store
        ).first()

        is_new_user = False

        # If user does not exist → CREATE directly
        if not user:
            user = User.objects.create(
                mobile=mobile,
                device_id=device_id,
                store=request.store
            )

            user.username = generate_username(user)
            user.referral_code = generate_referral_code()
            user.save()

            is_new_user = True

        else:
            # Update device if changed
            if device_id and user.device_id != device_id:
                user.device_id = device_id

            if not user.username:
                user.username = generate_username(user)

            if not user.referral_code:
                user.referral_code = generate_referral_code()

            user.last_login = timezone.now()
            user.save()

        # ---------------- Generate Tokens ----------------
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)

        UserSession.objects.create(
            user=user,
            store=request.store,
            session_token=access,
            refresh_token=refresh_token,
            device_id=device_id,
            device_type=request.client_type,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT"),
            expires_at=timezone.now() + timedelta(days=7)
        )

        return CustomResponse().successResponse(
            description="OTP verified successfully",
            data={
                "is_new_user": is_new_user,
                "access": access,
                "refresh": refresh_token,
                "user": {
                    "id": str(user.id),
                    "mobile": user.mobile,
                    "username": user.username,
                    "name": user.name,
                    "referral_code": user.referral_code,
                    "device_id": user.device_id,
                    "store_id": user.store.id,
                    "gender": user.gender,
                    "dob": user.dob,
                    "wallet_balance": user.wallet_balance,
                    "email": user.email,
                    "profile_image": user.profile_image,
                }
            },
            status=status.HTTP_200_OK
        )


class ProfileUpdate(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return CustomResponse().successResponse(data={
            "name": user.name,
            "gender": user.gender,
            "dob": user.dob,
            "referral_code": user.referral_code,
            "wallet_balance": user.wallet_balance,
            "email": user.email,
            "profile_image": user.profile_image,
        })

    def post(self, request):
        user = request.user
        data = request.data
        if "name" in data:
            user.name = data["name"]
        if "email" in data:
            user.email = data["email"]
        if "profile_pic" in data:
            user.profile_image = data["profile_pic"]
        if "dob" in data:
            user.dob = data["dob"]
        if "gender" in data:
            user.gender = data["gender"]
        user.save()
        return CustomResponse().successResponse(data={
            "name":user.name,
            "gender":user.gender,
            "dob":user.dob,
            "referral_code":user.referral_code,
            "wallet_balance":user.wallet_balance,
            "email":user.email,
            "profile_image":user.profile_image,
        })



# class FileUploadView(APIView):
#     permission_classes = [AllowAny]
#     parser_classes = [MultiPartParser, FormParser]
#
#     def post(self, request, *args, **kwargs):
#         files = request.FILES.getlist("files")
#         path = request.data.get("path", "temp")
#
#         if not files:
#             return CustomResponse().successResponse(
#                 {"error": "No file was provided."}, status=status.HTTP_400_BAD_REQUEST
#             )
#
#         uploaded_files = []
#
#         try:
#             for file_obj in files:
#                 # Save each file to the default storage
#                 sanitized_filename = add_unique_suffix_to_filename(sanitize_filename(file_obj.name))
#
#                 file_path = default_storage.save(f"{path}/{sanitized_filename}", ContentFile(file_obj.read()))
#                 file_url = settings.MEDIA_URL + file_path
#                 uploaded_files.append(
#                     {"original_filename": file_obj.name, "file_url": file_url, "file_path": file_path}
#                 )
#
#             return CustomResponse().successResponse(uploaded_files, status=status.HTTP_201_CREATED)
#
#         except Exception as e:
#             return CustomResponse().errorResponse(
#                 {"error": str(e)}, description="File upload failed", status=status.HTTP_400_BAD_REQUEST
#             )


class FileUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist("files")
        path = request.data.get("path", "temp")
        store = request.store

        if not store.aws_bucket_name:
            return CustomResponse().errorResponse(
                description="Store S3 bucket not configured"
            )

        if not files:
            return CustomResponse().errorResponse(
                description="No file was provided"
            )

        storage = StoreS3Storage(bucket_name=store.aws_bucket_name)
        uploaded_files = []

        for file_obj in files:
            filename = add_unique_suffix_to_filename(
                sanitize_filename(file_obj.name)
            )

            file_path = storage.save(
                f"{path}/{filename}",
                ContentFile(file_obj.read())
            )

            file_url = storage.url(file_path)

            uploaded_files.append({
                "original_filename": file_obj.name,
                "file_path": file_path,
                "file_url": file_url
            })

        return CustomResponse().successResponse(
            data=uploaded_files,
            description="Files uploaded successfully"
        )

from rest_framework.views import APIView
from rest_framework.response import Response


class AppVersionCheckAPI(APIView):
    authentication_classes = []  # public
    permission_classes = []

    def post(self, request):
        version = request.data.get("version")
        os = request.header.get("x-client-type")

        if not os or not version:
            return CustomResponse().errorResponse(data={}, description="os and version are required")

        config = (
            AppVersionConfig.objects
            .filter(os=os, is_active=True)
            .order_by("-updated_at")
            .first()
        )

        if not config:
            return Response({"update_required": False})

        app_version = version_to_tuple(version)
        min_version = version_to_tuple(config.min_supported_version)
        latest_version = version_to_tuple(config.latest_version)

        # 🚨 Force update condition
        if app_version < min_version or config.force_update:
            return CustomResponse().successResponse(data={
                "update_required": True,
                "force_update": True,
                "latest_version": config.latest_version,
                "title": config.update_title,
                "message": config.update_message,
            })

        # 🔔 Normal update
        if app_version < latest_version:
            return CustomResponse().successResponse(data={
                "update_required": True,
                "force_update": False,
                "latest_version": config.latest_version,
                "title": config.update_title,
                "message": config.update_message,
            })

        return CustomResponse().successResponse(data={
            "update_required": False,
        })


class EmailSendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        store = request.store

        if not email:
            return CustomResponse().errorResponse(
                description="Email is required",
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(email=email).first()
        is_new_user = not bool(user)

        if is_new_user:
            TempUser.objects.update_or_create(
                email=email,
                store=store
            )

        otp = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=15)

        UserOTP.objects.filter(
            store=store,
            email=email,
            is_used=False
        ).update(is_used=True)

        UserOTP.objects.create(
            store=store,
            email=email,
            otp=otp,
            expires_at=expires_at
        )

        send_otp_email(email, otp)

        return CustomResponse().successResponse(
            description="OTP sent successfully",
            data={
                "is_new_user": is_new_user,
                "email": email
            }
        )


class EmailVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        device_id = request.data.get("device_id")

        if not email or not otp:
            return CustomResponse().errorResponse(
                description="Email and OTP are required",
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------- Validate OTP (STORE-SCOPED) ----------------
        otp_obj = (
            UserOTP.objects
            .filter(
                store=request.store,
                email=email,
                otp=otp,
                is_used=False
            )
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

        # ---------------- Check or Create User ----------------
        user, created = User.objects.get_or_create(
            email=email,
            store=request.store,
            defaults={
                "device_id": device_id,
            }
        )

        is_new_user = created

        # Update device_id if changed
        if device_id and user.device_id != device_id:
            user.device_id = device_id

        # Ensure required fields exist
        if not user.username:
            user.username = generate_username(user)

        if not user.referral_code:
            user.referral_code = generate_referral_code()

        if not user.store:
            user.store = request.store

        user.last_login = timezone.now()
        user.save()

        # ---------------- Tokens ----------------
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)

        UserSession.objects.create(
            user=user,
            store=request.store,
            session_token=access,
            refresh_token=refresh_token,
            device_id=device_id,
            device_type=request.client_type,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT"),
            expires_at=timezone.now() + timedelta(days=7)
        )

        return CustomResponse().successResponse(
            description="OTP verified successfully",
            data={
                "is_new_user": is_new_user,
                "access": access,
                "refresh": refresh_token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "referral_code": user.referral_code,
                    "device_id": user.device_id,
                    "store_id": str(user.store.id)
                }
            },
            status=status.HTTP_200_OK
        )


class VisitorCreateAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data

        visitor_id = data.get("visitor_id")   # UUID (web) or device_id (app)
        platform = data.get("platform")       # WEB / ANDROID / IOS
        fcm_id = data.get("fcm_id")
        store = request.store
        user = request.user if request.user.is_authenticated else None

        if not visitor_id or not platform:
            return CustomResponse().errorResponse(
                description="visitor_id and platform are required"
            )

        # Get request metadata
        ip_address = ""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT")

        # Create or update visitor
        visitor, created = Visitor.objects.get_or_create(
            store=store,
            visitor_id=visitor_id,
            defaults={
                "platform": platform,
                "user": user,
                "fcm_id": fcm_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "visit_count": 1
            }
        )

        if not created:
            # Update visit count & last visit
            visitor.visit_count += 1
            visitor.last_visited_at = timezone.now()

            if fcm_id and visitor.fcm_id != fcm_id:
                visitor.fcm_id = fcm_id

            # Attach user after login
            if user and not visitor.user:
                visitor.user = user

            visitor.save()

        return CustomResponse().successResponse(
            data={
                "visitor_id": visitor.visitor_id,
                "platform": visitor.platform,
                "fcm_id": visitor.fcm_id,
                "visit_count": visitor.visit_count,
                "store_id": str(visitor.store.id),
                "user_id": str(visitor.user.id) if visitor.user else None,
                "first_visited_at": visitor.first_visited_at,
                "last_visited_at": visitor.last_visited_at,
            },
            description="Visitor tracked successfully"
        )


class DeleteUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user

        return CustomResponse().successResponse(
            data={},
            description=(
                "You are logged out successfully. "
                "If you do not log in again within 15 days, "
                "your account and all associated data will be permanently deleted."
            )
        )

class EnrolPlatinumJubli(APIView):

    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data
        enroll = Enrollments()
        enroll.payload = data
        enroll.save()
        return CustomResponse().successResponse(data={})

def fetch_cashfree_payment_status(order_number):
    url = f"{settings.CASHFREE_URL}/{order_number}"

    if settings.ENV == 'prod':
        CASHFREE_APP_ID = "623429ab66400ca4e318370c2d924326"
        CASHFREE_SECRET_KEY = "cfsk_ma_prod_4e9093365c5c98638e736183cf187d9b_4ec3d2ca"
    else:
        CASHFREE_APP_ID = "TEST1011734049bd1500ed13dfd6b93404371101"
        CASHFREE_SECRET_KEY = "cfsk_ma_test_1cc088db20df08421499959882252953_28b9a0f4"

    # --- Prepare headers ---
    headers = {
        "x-api-version": settings.CASHFREE_API_VERSION,
        "x-client-id": CASHFREE_APP_ID,
        "x-client-secret": CASHFREE_SECRET_KEY,
        "Content-Type": "application/json",
    }
    print("headers", headers)
    print("settings.CASHFREE_URL ", settings.CASHFREE_URL)
    response = requests.get(url, headers=headers, timeout=10)
    print(f"settings.CASHFREE_URL {response.json()}", )
    if response.status_code != 200:
        raise Exception("Failed to fetch order status from Cashfree")
    return response.json()

class IftarWebhook(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data
        print("Webhook triggered")
        print(data)
        event_type = data.get("type")
        order_id = data.get("data", {}).get("order", {}).get("order_id")
        order_amount = data.get("data", {}).get("order", {}).get("order_amount")
        print("Webhook received:", data)
        if not order_id:
            print("Webhook test / invalid payload")
            return CustomResponse().successResponse(data={},
                                                    description="Webhook received"
                                                    )
        print(order_id)
        order = IftarBookings.objects.select_for_update().filter(booking_id=order_id).first()
        if not order:
            print("No Order Found with Order Number")
            return CustomResponse().successResponse(data={},
                                                    description="No Order Found with Order Number"
                                                    )
        if order.status != "INITIATED":
            print("Payment status verified with Cashfree and updated Already")
            return CustomResponse().successResponse(
                data={
                    "order_number": order.order_number,
                    "final_payment_status": order.status,
                },
                description="Payment status verified with Cashfree and updated"
            )
        if event_type == "PAYMENT_SUCCESS_WEBHOOK":
            order.status = "PAID"
            order.updated_by = event_type
            order.save(update_fields=["status", "updated_by"])
        elif event_type == "PAYMENT_FAILED_WEBHOOK":
            order.status = "FAILED"
            order.updated_by = event_type
            order.save(update_fields=["status", "updated_by"])
        else:
            order.status = "PENDING"
            order.updated_by = event_type
            order.save(update_fields=["status", "updated_by"])
        return CustomResponse().successResponse(
            data={
                "order_number": order.booking_id,
                "final_payment_status": order.status,
            },
            description="Payment status verified with Cashfree and updated"
        )

class IftarENoorUpdatePayment(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        print(data)
        required_fields = ["order_number", "status"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(
                    description=f"{field} is required"
                )
        order_number = data.get("order_number")
        if not order_number:
            return CustomResponse().errorResponse(
                description="order number  required"
            )
        order = IftarBookings.objects.filter(booking_id=order_number).first()
        if not order:
            return CustomResponse().errorResponse(
                description="Order Details Mismatched"
            )
        if order.status == "COMPLETED":
            return CustomResponse().successResponse(
                data={
                    "order_number": order_number,
                    "final_payment_status": order.status,
                },
                description="Payment status verified with Cashfree and updated"
            )
        print("contacting CF for status update")

        cf_response = fetch_cashfree_payment_status(order_number)
        cf_order_status = cf_response.get("order_status")  # PAID / ACTIVE / FAILED
        order.status = cf_order_status
        order.save(update_fields=["status"])
        return CustomResponse().successResponse(
            data={
                "order_number": order_number,
                "final_payment_status": order.status,
            },
            description="Payment status verified with Cashfree and updated"
        )


class IftarENoor(APIView):

    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data
        # 1. Required fields
        required_fields = ["mobile", "email", "age", "name"]
        for field in required_fields:
            if not data.get(field):
                return CustomResponse.errorResponse(
                    description=f"{field} is required"
                )

        booking_id = "IEN-"+str(generate_otp())
        booking = IftarBookings()
        booking.mobile = data["mobile"]
        booking.email = data["email"]
        booking.age = data["age"]
        booking.name = data["name"]
        booking.booking_id = booking_id
        booking.status = "INITIATED"
        booking.save()

        # connect to payment gateway
        payment_resp = self.initatepayment(550.00, booking)
        booking.cf_session_id = payment_resp["payment_session_id"]
        booking.cf_id = payment_resp["cf_order_id"]
        booking.save(
            update_fields=["cf_session_id", "cf_id"]
        )
        return CustomResponse.successResponse(
            data={
                "order_number": booking.booking_id,
                "payment_session_id": booking.cf_session_id,
                "cf_order_id": booking.cf_id,
                "amount": str(550.00)
            },
            description="Order initiated successfully"
        )

    def initatepayment(self, amount, booking):

        # --- Prepare payload ---
        payload = {
            "order_currency": "INR",
            "order_amount": float(amount),
            "order_id": str(booking.booking_id),
            "customer_details": {
                "customer_id": str(booking.id),
                "customer_phone": str(booking.mobile),
                "customer_name": str(booking.name),
            },
            "order_meta": {
                "notify_url": settings.CASHFREE_IFTAR_WEBHOOK,
            },
        }
        if settings.ENV == 'prod':
            CASHFREE_APP_ID = "623429ab66400ca4e318370c2d924326"
            CASHFREE_SECRET_KEY = "cfsk_ma_prod_4e9093365c5c98638e736183cf187d9b_4ec3d2ca"
        else:
            CASHFREE_APP_ID = "TEST1011734049bd1500ed13dfd6b93404371101"
            CASHFREE_SECRET_KEY = "cfsk_ma_test_1cc088db20df08421499959882252953_28b9a0f4"

        # --- Prepare headers ---
        headers = {
            "x-api-version": settings.CASHFREE_API_VERSION,
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "Content-Type": "application/json",
        }
        print("headers", headers)
        print("payload", payload)
        print("settings.CASHFREE_URL ", settings.CASHFREE_URL)
        print("payload", payload)

        try:
            # --- Send request to CashFree ---
            response = requests.post(settings.CASHFREE_URL, json=payload, headers=headers, timeout=15)

            # --- Validate response ---
            if response.status_code == 200:
                resp_json = response.json()
                print(resp_json)
                order_id = resp_json.get("cf_order_id")
                session_id = resp_json.get("payment_session_id")

                if order_id and session_id:
                    return {
                        "cf_order_id": order_id,
                        "payment_session_id": session_id,
                        "order_number": booking.booking_id
                    }
                else:
                    raise Exception("Could not found cf_order_id and payment_session_id")
            else:
                raise Exception(
                    f"Cashfree response code {response.status_code}: {response.text}"
                )
        except Exception as e:
            print(e)
            raise Exception(e)