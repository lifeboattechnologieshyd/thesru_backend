from django.urls import path

from store.views import PinListView, AddressAPIView, ProductDetailAPIView, ProductListAPIView, InitiateOrder, OrderView, \
    BannerListView, CategoryListView, AddToCartAPIView, CartListAPIView, UpdateCartAPIView, RemoveFromCartAPIView, \
    AddToWishlistAPIView, WishlistListAPIView, RemoveFromWishlistAPIView, MoveWishlistToCartAPIView, CartTotalAPIView, \
    FlashSaleBannerListView, WebBannerListView, Webhook, PaymentStatusAPIView, ProductReview

urlpatterns = [

    path("pin",PinListView.as_view()),
    path("address",AddressAPIView.as_view()),
    path("address/<str:id>",AddressAPIView.as_view()),
    path("products", ProductListAPIView.as_view()),
    path("product/<str:id>", ProductDetailAPIView.as_view()),
    path("banner",BannerListView.as_view()),
    path("category",CategoryListView.as_view()),
    path("web/banner",WebBannerListView.as_view()),
    path("flash/sale/banner",FlashSaleBannerListView.as_view()),
    path("web/banner/<str:id>",WebBannerListView.as_view()),
    path("flash/sale/banner/<str:id>",FlashSaleBannerListView.as_view()),


    path("initiateorder", InitiateOrder.as_view()),
    path("payment/status/update",PaymentStatusAPIView.as_view()),
    path("paymentWebhook", Webhook.as_view()),
    path("order",OrderView.as_view()),

    path("add/cart",AddToCartAPIView.as_view()),
    path("get/cart",CartListAPIView.as_view()),
    path("update/cart/<str:id>",UpdateCartAPIView.as_view()),
    path("remove/cart/<str:id>",RemoveFromCartAPIView.as_view()),
    path("add/wishlist",AddToWishlistAPIView.as_view()),
    path("get/wishlist",WishlistListAPIView.as_view()),
    path("remove/wishlist/<str:id>",RemoveFromWishlistAPIView.as_view()),
    path("wishlist/to/cart",MoveWishlistToCartAPIView.as_view()),
    path("cart/total",CartTotalAPIView.as_view()),


    path("product/review",ProductReview.as_view()),

]