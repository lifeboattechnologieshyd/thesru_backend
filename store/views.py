from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from db.models import Store
from mixins.drf_views import CustomResponse


# Create your views here.
class StoreAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self,request):
        data = request.data

        Store.objects.create(
            name = data.get("name")
        )

        return CustomResponse.successResponse(data={},description="data saved")