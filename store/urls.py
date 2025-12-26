from django.urls import path

from store.views import PinListView, AddressAPIView, ProductDetailAPIView, ProductListAPIView, InitiateOrder, OrderView, \
    BannerListView, CategoryListView

urlpatterns = [

    path("pin",PinListView.as_view()),
    path("address",AddressAPIView.as_view()),
    path("address/<str:id>",AddressAPIView.as_view()),
    path("products", ProductListAPIView.as_view()),
    path("product/<str:id>", ProductDetailAPIView.as_view()),
    path("banner",BannerListView.as_view()),
    path("category",CategoryListView.as_view()),


    path("initiateorder", InitiateOrder.as_view()),
    path("order",OrderView.as_view()),

]