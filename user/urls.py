
from django.urls import path

from user.views import SignUpAPIView, SignInAPIView, StudentAPIView

urlpatterns = [
    path("signUp", SignUpAPIView.as_view()),
    path("signin", SignInAPIView.as_view()),
    path("student",StudentAPIView.as_view())
]