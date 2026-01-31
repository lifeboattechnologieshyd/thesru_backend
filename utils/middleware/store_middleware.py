import uuid
from urllib.parse import urlparse

from django.http import JsonResponse
from django.apps import apps

class StoreMiddleware:
    def __init__(self, get_response):
        """
           Resolves store from:
           1. X-Client-Identifier (mobile / internal)
           2. Origin header (browser)
           3. Host header (fallback)
           """
        self.get_response = get_response
        self.exempt_paths = (
            "/store/paymentWebhook",
            "/admin/",
            "/api/auth/",
            "/health/",
            "/backoffice/store",
            "/user/createadmin",
            "/user/admin-login",
            "/user/storage/upload",
            "/user/update-users"
        )


    def __call__(self, request):
        print("MIDDLEWARE PATH:", request.path)
        if any(request.path.startswith(p) for p in self.exempt_paths):
            return self.get_response(request)
        request.store = None
        identifier = None
        client_type = None

        # 1️⃣ Mobile / explicit header (highest priority)
        client_identifier = request.headers.get("X-Client-Identifier")
        if client_identifier:
            identifier = client_identifier
        x_client_type = request.headers.get("X-Client-Type")
        if x_client_type:
            client_type = x_client_type
        # 2️⃣ Browser origin
        if not identifier:
            origin = request.headers.get("Origin")
            if origin:
                identifier = urlparse(origin).netloc

        # 3️⃣ Host header (fallback)
        if not identifier:
            host = request.get_host()
            if host:
                identifier = host.split(":")[0]

            # 🚫 No identifier → public / health APIs
        if not identifier:
            return None
        StoreClient = apps.get_model("db", "StoreClient")
        try:
            store_client = StoreClient.objects.select_related("store").get(
                identifier=identifier,
                is_active=True
            )
            request.store = store_client.store
            request.store_client = store_client
            request.client_type = client_type
        except StoreClient.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid store or client"
                },
                status=401
            )
        return self.get_response(request)
