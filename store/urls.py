from store.views import StoreAPIView
from django.urls import path
urlpatterns = [
    path("store",StoreAPIView.as_view())
]