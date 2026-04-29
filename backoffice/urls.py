from django.urls import path

from backoffice.customer import CustomerCreation, UserAddress, BackofficeCustomerListAPI, CustomerDetails, \
    UpdateUserDetails
from backoffice.inventory import StockInAPIView, BulkInventory, StockOutAPI
from backoffice.shipping import  ShippingPlanAPIView, ShippinPlanCrud
from backoffice.store import ProductAPIView, CategoriesAPIView, BannerAPIView, \
    PinCodeAPIView, WebBannerAPIView, FlashSaleBannerAPIView, OrderStatsAPIView, \
    CartListView, OrderListAPIView, AbandonedOrderListAPIView, Login, SendOTP, TagsAPIView, AdminOrderDetailAPIView, \
    AdminCreateCouponAPIView, UserAPIView, CreateAppVersionConfigAPI, OrderShippingSlipAPIView, \
    StoreAnalyticsAPIView, EmailSendOTPView, EmailVerifyOTPView, ClientInfo, NotificationConfig, \
    NotificationTemplateConfig, SuperAdminSendOTPAPIView, SuperAdminVerifyOTPAPIView, StoreListAPIView, \
    DashboardStatsAPIView, PinCodeStatesAPIView, PinCodeDistrictAPIView, S3BucketAPIView, BusinessOnboardingAPIView, \
    PhonePeWebhookAPIView
from backoffice.subscriptions import CreateSubscriptionPlanAPI
from backoffice.superadmin import StorePaymentGatewayCreateAPIView, StoreAPIView

urlpatterns = [

    #####################################
    ## User Authentication API's       ##
    #####################################

    path("send-otp",SendOTP.as_view()),
    path("verify-otp",Login.as_view()),

    path("email-send-otp",EmailSendOTPView.as_view()),
    path("email-verify-otp",EmailVerifyOTPView.as_view()),



    ### DASHBOARD - ADMIN
    path("dashboard", DashboardStatsAPIView.as_view()),
    path("analytics", StoreAnalyticsAPIView.as_view()),

    #####################################
    ## User Search & Address API's     ##
    #####################################

    path("user/search",UserAPIView.as_view()),
    path("user/details/<str:id>",CustomerDetails.as_view()),
    path("user/address",UserAddress.as_view()), #post n get
    path("merchant/customer/add", CustomerCreation.as_view()),
    path("merchant/customer/update", UpdateUserDetails.as_view()),
    path("merchant/users", BackofficeCustomerListAPI.as_view()),



    #####################################
    ## Product  API's                    ##
    #####################################
    path("product", ProductAPIView.as_view()),
    path("product/<str:id>", ProductAPIView.as_view()),

    path("category",CategoriesAPIView.as_view()),
    path("category/<str:id>",CategoriesAPIView.as_view()),

    path("tag",TagsAPIView.as_view()),
    path("tag/<str:id>",TagsAPIView.as_view()),

    path("appversion",CreateAppVersionConfigAPI.as_view()),
    path("appversion/<str:id>",CreateAppVersionConfigAPI.as_view()),

    #####################################
    ## Mobile banner  API's            ##
    #####################################
    path("banner",BannerAPIView.as_view()),
    path("banner/<str:id>",BannerAPIView.as_view()),

    #####################################
    ##    -- Pincode -- API's          ##
    #####################################

    path("pin",PinCodeAPIView.as_view()),
    path("pin/<str:id>",PinCodeAPIView.as_view()),

    path("states",PinCodeStatesAPIView.as_view()),
    path("districts",PinCodeDistrictAPIView.as_view()),

    path("webbanner",WebBannerAPIView.as_view()),
    path("webbanner/<str:id>",WebBannerAPIView.as_view()),
    path("flashsale/banner",FlashSaleBannerAPIView.as_view()),
    path("flashsale/banner/<str:id>",FlashSaleBannerAPIView.as_view()),

    #####################################
    ## Order  API's                    ##
    #####################################
    path("orders",OrderListAPIView.as_view()),
    path("orders/<str:id>",OrderListAPIView.as_view()),
    path("order/details",AdminOrderDetailAPIView.as_view()),

    path("order/stats",OrderStatsAPIView.as_view()),
    path("abandoned/stats",AbandonedOrderListAPIView.as_view()),
    path("cart/total",CartListView.as_view()),

    path("coupon",AdminCreateCouponAPIView.as_view()),
    path("shippingslip/<str:id>",OrderShippingSlipAPIView.as_view()),
    path("client_info",ClientInfo.as_view()),


    path("get/store",StoreListAPIView.as_view()),


    path("shipping/plan",ShippingPlanAPIView.as_view()),# create, get, edit

    path("shipping/rule",ShippinPlanCrud.as_view()), # create, get, edit
    #####################################
    ## stock related apis -- INVENTORY ##
    #####################################
    path("stock-in",StockInAPIView.as_view()),
    path("stock-out",StockOutAPI.as_view()),
    path("bulk/stock-in",BulkInventory.as_view()),

    #####################################
    ## SUPER ADMIN                     ##
    #####################################
    path("superadmin/send-otp", SuperAdminSendOTPAPIView.as_view()),
    path("superadmin/verify-otp", SuperAdminVerifyOTPAPIView.as_view()),


    path("store", StoreAPIView.as_view()),
    path("store/<str:id>", StoreAPIView.as_view()),

    path("config/payment-gateway", StorePaymentGatewayCreateAPIView.as_view()),
    path("config/payment-gateway/<uuid:gateway_id>/", StorePaymentGatewayCreateAPIView.as_view()),

    path("notification/config", NotificationConfig.as_view()),
    path("notification/config/<str:id>", NotificationConfig.as_view()),

    path("notification/template/config", NotificationTemplateConfig.as_view()),
    path("notification/template/config/<str:id>", NotificationTemplateConfig.as_view()),

    path("subscription/plan",CreateSubscriptionPlanAPI.as_view()),
    path("create/bucket",S3BucketAPIView.as_view()),

    # path("business/onboarding",BusinessOnboardingAPIView.as_view()),
    # path("webhook",PhonePeWebhookAPIView.as_view()),



]
