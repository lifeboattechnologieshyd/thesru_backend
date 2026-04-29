import json

from django.forms import model_to_dict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.db import IntegrityError, transaction

from db.models import Store
from db.models.user import StorePaymentGateway, StoreClient
from mixins.drf_views import CustomResponse
from utils.user import create_bucket_and_upload_logo


class StoreAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        import json
        clients = json.loads(request.data.get("clients", "[]"))

        bucket_name = data.get("aws_bucket_name")
        logo_file = request.FILES.get("logo")

        #  STEP 1: CREATE BUCKET + UPLOAD LOGO FIRST
        success, result = create_bucket_and_upload_logo(bucket_name, logo_file)

        if not success:
            return CustomResponse.errorResponse(
                description="S3 bucket creation failed",
                data={"error": result}
            )

        logo_url = result

        #  STEP 2: CREATE STORE ONLY IF S3 SUCCESS
        try:
            store = Store.objects.create(
                name=data.get("name"),
                mobile=data.get("mobile"),
                email=data.get("email"),
                address=data.get("address"),
                logo=logo_url,
                aws_bucket_name=bucket_name,
                product_code=data.get("product_code"),
                email_login=data.get("email_login"),
                mobile_login=data.get("mobile_login"),
                primary_color=data.get("primary_color"),
                secondary_color=data.get("secondary_color"),
                client_id=data.get("client_id"),
                client_secret=data.get("client_secret"),
            )
            # payment config added while creating store from super admin.
            gateway = StorePaymentGateway.objects.create(
                store=store,
                provider=data.get("provider"),
                client_id=data.get("client_id"),
                client_secret=data.get("client_secret"),
                is_active=True,
            )

            for item in clients:
                StoreClient.objects.create(
                    store=store,
                    identifier=item.get("identifier"),
                    client_type=item.get("client_type"),
                    is_active=True
                )

            return CustomResponse.successResponse(
                data={
                    "bucket_name": bucket_name,
                    "logo_url": logo_url
                },
                description="Store and bucket created successfully"
            )

        except Exception as e:
            return CustomResponse.errorResponse(
                description="Store creation failed",
                data={"error": str(e)}
            )
    # ---------------- GET STORE / LIST ----------------
    def get(self, request, id=None):
        # ---------- SINGLE STORE ----------
        if id:
            store = Store.objects.filter(id=id).values().first()
            if not store:
                return CustomResponse.errorResponse(
                    description="store not found"
                )

            return CustomResponse.successResponse(
                data=[store],
                total=1
            )

        # ---------- PAGINATION ----------
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        if page < 1 or page_size < 1:
            return CustomResponse.errorResponse(
                description="page and page_size must be positive integers"
            )
        queryset = Store.objects.prefetch_related("clients").all().order_by("-created_at")
        total = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset: offset + page_size]
        data = []
        for query in queryset:
            client_list = []
            for client in query.clients.all():
                client_list.append({
                    "id": client.id,
                    "client_type": client.client_type,
                    "identifier": client.identifier,
                    "is_active": client.is_active
                })
            resp = model_to_dict(query)
            resp["id"] = str(query.id)
            data.append({
                "client": client_list,
                "store": resp
            })
        return CustomResponse.successResponse(
            data=data,
            total=total
        )

    # ---------------- UPDATE STORE ----------------
    def put(self, request, id=None):
        store_id = id
        data = request.data
        if not store_id:
            return CustomResponse.errorResponse(description="store_id required")

        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return CustomResponse.errorResponse(description="Store not found")


        if isinstance(data, str):
            data = json.loads(data)

        clients = data.get("clients", [])

        if isinstance(clients, str):
            clients = json.loads(clients)

        try:
            with transaction.atomic():

                # ---------------- UPDATE STORE ----------------

                store.name = data.get("name", store.name)
                store.mobile = data.get("mobile", store.mobile)
                store.email = data.get("email", store.email)
                store.address = data.get("address", store.address)
                store.product_code = data.get("product_code", store.product_code)
                store.aws_bucket_name = data.get("aws_bucket_name", store.aws_bucket_name)
                store.email_login = data.get("email_login", store.email_login)
                store.mobile_login = data.get("mobile_login", store.mobile_login)
                store.primary_color = data.get("primary_color", store.primary_color)
                store.secondary_color = data.get("secondary_color", store.secondary_color)
                store.client_id = data.get("client_id", store.client_id)
                store.client_secret = data.get("client_secret", store.client_secret)

                store.save()

                # ---------------- CLEAN CLIENTS (remove duplicates) ----------------

                clean_clients = []
                seen = set()

                for c in clients:
                    identifier = str(c.get("identifier", "")).strip()
                    client_type = c.get("client_type")

                    if not identifier:
                        continue

                    if identifier in seen:
                        continue

                    seen.add(identifier)
                    clean_clients.append({
                        "identifier": identifier,
                        "client_type": client_type
                    })
                clients = clean_clients
                # ---------------- EXISTING ----------------
                existing_qs = StoreClient.objects.filter(store=store)
                existing_map = {
                    x.identifier: x for x in existing_qs
                }
                request_identifiers = set()
                # ---------------- UPSERT ----------------
                for item in clients:
                    identifier = item["identifier"]
                    client_type = item.get("client_type")
                    request_identifiers.add(identifier)
                    if identifier in existing_map:
                        obj = existing_map[identifier]
                        obj.client_type = client_type
                        obj.is_active = True
                        obj.save()
                    else:
                        StoreClient.objects.create(
                            store=store,
                            identifier=identifier,
                            client_type=client_type,
                            is_active=True
                        )

                # ---------------- DELETE REMOVED ----------------

                existing_identifiers = set(existing_map.keys())

                delete_ids = existing_identifiers - request_identifiers

                if delete_ids:
                    StoreClient.objects.filter(
                        store=store,
                        identifier__in=delete_ids
                    ).delete()

            return CustomResponse.successResponse(data={},description="Store updated successfully")

        except IntegrityError as error:
            return CustomResponse.errorResponse(
                description=f"Database error {error}"
            )

    # ---------------- DELETE STORE ----------------
    def delete(self, request, id=None):
        if not id:
            return CustomResponse.errorResponse(
                description="store id required"
            )

        store = Store.objects.filter(id=id)
        if not store.exists():
            return CustomResponse.errorResponse(
                description="store not found"
            )

        store.delete()

        return CustomResponse.successResponse(
            data={},
            description="store deleted successfully"
        )



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

