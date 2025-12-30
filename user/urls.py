
from django.urls import path

from user.views import MobileSendOTPView, MobileVerifyOTPView, FileUploadView

urlpatterns = [
    path("send-otp", MobileSendOTPView.as_view()),
    path("verify-otp", MobileVerifyOTPView.as_view()),
    path("storage/upload", FileUploadView.as_view()),

]