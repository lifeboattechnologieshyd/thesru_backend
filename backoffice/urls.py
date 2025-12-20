from django.urls import path

from backoffice.store import ProductAPIView, DisplayProductAPIView, CategoriesAPIView, BannerAPIView, InventoryAPIView, \
    PinCodeAPIView

urlpatterns = [
    path("product",ProductAPIView.as_view()),
    path("product/<str:id>",ProductAPIView.as_view()),
    path("display/product",DisplayProductAPIView.as_view()),
    path("display/product/<str:id>",DisplayProductAPIView.as_view()),
    path("category",CategoriesAPIView.as_view()),
    path("category/<str:id>",CategoriesAPIView.as_view()),
    path("banner",BannerAPIView.as_view()),
    path("banner/<str:id>",BannerAPIView.as_view()),
    path("inventory",InventoryAPIView.as_view()),
    path("inventory/<str:id>",InventoryAPIView.as_view()),
    path("pin",PinCodeAPIView.as_view()),
    path("pin/<str:id>",PinCodeAPIView.as_view()),
]