
from django.urls import path

from user.views import MobileSendOTPView, MobileVerifyOTPView, FileUploadView, CreateAdmin, AdminLogin, ProfileUpdate

urlpatterns = [
    path("send-otp", MobileSendOTPView.as_view()),
    path("verify-otp", MobileVerifyOTPView.as_view()),
    path("createadmin", CreateAdmin.as_view()),
    path("admin-login", AdminLogin.as_view()),
    path("storage/upload", FileUploadView.as_view()),
    path("profile", ProfileUpdate.as_view()),
]