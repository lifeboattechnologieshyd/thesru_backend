from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.db import IntegrityError, transaction

from db.models import Store
from db.models.user import StorePaymentGateway
from mixins.drf_views import CustomResponse


class StorePaymentGatewayCreateAPIView(APIView, CustomResponse):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        store_id = data.get("store_id")
        provider = data.get("provider")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        is_active = data.get("is_active", True)
        if not store_id or not provider:
            return CustomResponse().errorResponse(data={}, description="store id and provider are required")
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return CustomResponse().errorResponse(data={}, description="store not found")
        valid_providers = [choice[0] for choice in StorePaymentGateway.PAYMENT_GATEWAY_CHOICES]
        if provider not in valid_providers:
            return CustomResponse().errorResponse(data={}, description=f"Invalid provider. Allowed: {valid_providers}")
        try:
            with transaction.atomic():
                # ⚡ If only one active gateway needed
                if is_active:
                    StorePaymentGateway.objects.filter(
                        store=store,
                        is_active=True
                    ).update(is_active=False)
                gateway = StorePaymentGateway.objects.create(
                    store=store,
                    provider=provider,
                    client_id=client_id,
                    client_secret=client_secret,
                    is_active=is_active,
                )
        except IntegrityError:
            return CustomResponse().errorResponse(data={}, description=f"{provider} already exists for this store")

        return CustomResponse().successResponse(data=
            {
                "id": gateway.id,
                "store_id": str(store.id),
                "provider": gateway.provider,
                "is_active": gateway.is_active,
            },
            description="Payment gateway added successfully"
        )
    def get(self, request):
        store_id = request.query_params.get("store_id")
        provider = request.query_params.get("provider")
        if not store_id:
            return CustomResponse().errorResponse(data={}, description="store id is required")
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return CustomResponse().errorResponse(data={}, description="store not found")
        queryset = StorePaymentGateway.objects.filter(store=store)
        if provider:
            queryset = queryset.filter(provider=provider)
        data = []
        for obj in queryset:
            data.append({
                "id": obj.id,
                "provider": obj.provider,
                "client_id": obj.client_id,
                "is_active": obj.is_active,
            })
        return CustomResponse().successResponse(data=
            data,
            description="Payment gateways fetched successfully"
        )
    def put(self, request, gateway_id):
        data = request.data

        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        is_active = data.get("is_active")
        try:
            gateway = StorePaymentGateway.objects.get(id=gateway_id)
        except StorePaymentGateway.DoesNotExist:
            return CustomResponse().successResponse(
                data={},
                description="Payment gateway not found")
        try:
            with transaction.atomic():
                if is_active is True:
                    StorePaymentGateway.objects.filter(
                        store=gateway.store,
                        is_active=True
                    ).exclude(id=gateway.id).update(is_active=False)

                if client_id is not None:
                    gateway.client_id = client_id

                if client_secret is not None:
                    gateway.client_secret = client_secret

                if is_active is not None:
                    gateway.is_active = is_active

                gateway.save()

        except Exception as e:
            return CustomResponse().successResponse(data={},
                description=str(e)
            )

        return CustomResponse().successResponse(data={},
            description="Payment gateway updated successfully"
        )

