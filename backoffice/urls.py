from django.urls import path

from backoffice.store import ProductAPIView, CategoriesAPIView, BannerAPIView, InventoryAPIView, \
    PinCodeAPIView, StoreAPIView, WebBannerAPIView, FlashSaleBannerAPIView, OrderStatsAPIView, \
    CartListView, OrderListAPIView, AbandonedOrderListAPIView, Login, SendOTP, TagsAPIView, UpdateOrderStatusAPIView

urlpatterns = [

    path("send-otp",SendOTP.as_view()),
    path("verify-otp",Login.as_view()),

    path("store", StoreAPIView.as_view()),
    path("store/<str:id>", StoreAPIView.as_view()),

    path("product", ProductAPIView.as_view()),
    path("product/<str:id>", ProductAPIView.as_view()),

    # path("product-variants",DisplayProductAPIView.as_view()),
    path("category",CategoriesAPIView.as_view()),
    path("category/<str:id>",CategoriesAPIView.as_view()),

    path("tag",TagsAPIView.as_view()),
    path("tag/<str:id>",TagsAPIView.as_view()),


    path("banner",BannerAPIView.as_view()),
    path("banner/<str:id>",BannerAPIView.as_view()),

    path("inventory",InventoryAPIView.as_view()),
    path("inventory/<str:id>",InventoryAPIView.as_view()),

    path("pin",PinCodeAPIView.as_view()),
    path("pin/<str:id>",PinCodeAPIView.as_view()),



    path("webbanner",WebBannerAPIView.as_view()),
    path("webbanner/<str:id>",WebBannerAPIView.as_view()),
    path("flashsale/banner",FlashSaleBannerAPIView.as_view()),
    path("flashsale/banner/<str:id>",FlashSaleBannerAPIView.as_view()),

    path("order/stats",OrderStatsAPIView.as_view()),
    path("abandoned/stats",AbandonedOrderListAPIView.as_view()),
    path("cart/total",CartListView.as_view()),
    path("orders",OrderListAPIView.as_view()),
    path("order/update",UpdateOrderStatusAPIView.as_view()),

]