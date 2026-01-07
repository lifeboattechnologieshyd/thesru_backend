import uuid
from django.http import JsonResponse

from db.models import Store


class StoreMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        # ✅ APIs that do NOT need store
        self.exempt_paths = [
            "backoffice/store",

        ]

    def __call__(self, request):
        # ✅ Skip exempt paths
        for path in self.exempt_paths:
            if request.path.startswith(path):
                return self.get_response(request)

        store_id = request.headers.get("X-STORE-ID")

        if not store_id:
            return JsonResponse(
                {
                    "success": False,
                    "errorCode": 400,
                    "description": "X-STORE-ID header is required"
                },
                status=400
            )

        try:
            store_uuid = uuid.UUID(store_id)
        except ValueError:
            return JsonResponse(
                {
                    "success": False,
                    "errorCode": 400,
                    "description": "Invalid store id"
                },
                status=400
            )

        try:
            store = Store.objects.get(id=store_uuid)
        except Store.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "errorCode": 404,
                    "description": "Store not found"
                },
                status=404
            )

        # 🔥 Attach store to request
        request.store = store

        return self.get_response(request)
