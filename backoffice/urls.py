from django.urls import path

from backoffice.shipping import  ShippingPlanAPIView, ShippinPlanCrud
from backoffice.store import ProductAPIView, CategoriesAPIView, BannerAPIView, InventoryAPIView, \
    PinCodeAPIView, StoreAPIView, WebBannerAPIView, FlashSaleBannerAPIView, OrderStatsAPIView, \
    CartListView, OrderListAPIView, AbandonedOrderListAPIView, Login, SendOTP, TagsAPIView, AdminOrderDetailAPIView, \
    AdminCreateCouponAPIView, UserAddress, UserAPIView, CreateAppVersionConfigAPI, OrderShippingSlipAPIView, \
    StoreAnalyticsAPIView, EmailSendOTPView, EmailVerifyOTPView, ClientInfo, NotificationConfig, \
    NotificationTemplateConfig, SuperAdminSendOTPAPIView, SuperAdminVerifyOTPAPIView, StoreListAPIView, \
    DashboardStatsAPIView, DiscountAPIView, CreateStoreSubscriptionAPIView, SubscriptionPlanAPIView

urlpatterns = [

    path("send-otp",SendOTP.as_view()),
    path("verify-otp",Login.as_view()),

    path("email-send-otp",EmailSendOTPView.as_view()),
    path("email-verify-otp",EmailVerifyOTPView.as_view()),

    path("user/search",UserAPIView.as_view()),
    path("user/address",UserAddress.as_view()),

    path("store", StoreAPIView.as_view()),
    path("store/<str:id>", StoreAPIView.as_view()),

    path("product", ProductAPIView.as_view()),
    path("product/<str:id>", ProductAPIView.as_view()),

    # path("product-variants",DisplayProductAPIView.as_view()),
    path("category",CategoriesAPIView.as_view()),
    path("category/<str:id>",CategoriesAPIView.as_view()),

    path("tag",TagsAPIView.as_view()),

    path("appversion",CreateAppVersionConfigAPI.as_view()),
    path("appversion/<str:id>",CreateAppVersionConfigAPI.as_view()),

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
    path("orders/<str:id>",OrderListAPIView.as_view()),
    path("order/details",AdminOrderDetailAPIView.as_view()),

    path("coupon",AdminCreateCouponAPIView.as_view()),
    path("shippingslip/<str:id>",OrderShippingSlipAPIView.as_view()),
    path("analytics",StoreAnalyticsAPIView.as_view()),
    path("client_info",ClientInfo.as_view()),

    path("notification/config",NotificationConfig.as_view()),
    path("notification/config/<str:id>",NotificationConfig.as_view()),


    path("notification/template/config",NotificationTemplateConfig.as_view()),
    path("notification/template/config/<str:id>",NotificationTemplateConfig.as_view()),

    path("superadmin/send-otp",SuperAdminSendOTPAPIView.as_view()),
    path("superadmin/verify-otp",SuperAdminVerifyOTPAPIView.as_view()),

    path("get/store",StoreListAPIView.as_view()),


    path("shipping/plan",ShippingPlanAPIView.as_view()),# create, get, edit

    path("shipping/rule",ShippinPlanCrud.as_view()), # create, get, edit

    path("dashboard",DashboardStatsAPIView.as_view()),

    path("discount",DiscountAPIView.as_view()),
    path("discount/<str:id>",DiscountAPIView.as_view()),

    path("plan",SubscriptionPlanAPIView.as_view()),
    path("plan/<str:id>",SubscriptionPlanAPIView.as_view()),


    path("create/subscription",CreateStoreSubscriptionAPIView.as_view()),

]
