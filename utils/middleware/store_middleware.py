import uuid
from django.http import JsonResponse
from django.apps import apps


# class StoreMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#         self.exempt_paths = [
#
#         ]
#
#     def __call__(self, request):
#         # Skip exempt paths
#         for path in self.exempt_paths:
#             if request.path.startswith(path):
#                 return self.get_response(request)
#
#         store_id = request.headers.get("X-STORE-ID")
#
#         if not store_id:
#             return JsonResponse(
#                 {
#                     "success": False,
#                     "errorCode": 400,
#                     "description": "X-STORE-ID header is required"
#                 },
#                 status=400
#             )
#
#         try:
#             store_uuid = uuid.UUID(store_id)
#         except ValueError:
#             return JsonResponse(
#                 {
#                     "success": False,
#                     "errorCode": 400,
#                     "description": "Invalid store id"
#                 },
#                 status=400
#             )
#
#         # ✅ LAZY LOAD Store model (NO circular import)
#         Store = apps.get_model("db", "Store")
#
#         try:
#             store = Store.objects.get(id=store_uuid)
#         except Store.DoesNotExist:
#             return JsonResponse(
#                 {
#                     "success": False,
#                     "errorCode": 404,
#                     "description": "Store not found"
#                 },
#                 status=404
#             )
#
#         request.store = store
#         return self.get_response(request)


# class StoreMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#         self.exempt_paths = (
#             "/admin/",
#             "/api/auth/",
#             "/health/",
#         )
#
#     def __call__(self, request):
#         for path in self.exempt_paths:
#             if request.path.startswith(path):
#                 return self.get_response(request)
#
#         request.store = None
#         store_id = request.headers.get("X-STORE-ID")
#
#         if not store_id:
#             return self.get_response(request)
#
#         try:
#             store_uuid = uuid.UUID(store_id)
#         except ValueError:
#             return self.get_response(request)
#
#         Store = apps.get_model("db", "Store")
#
#         try:
#             store = Store.objects.get(id=store_uuid)
#         except Store.DoesNotExist:
#             return self.get_response(request)
#
#         request.store = store
#         return self.get_response(request)


class StoreMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = (
            "/store/paymentWebhook",
            "/admin/",
            "/api/auth/",
            "/health/",
        )


    def __call__(self, request):
        print("MIDDLEWARE PATH:", request.path)

        if any(request.path.startswith(p) for p in self.exempt_paths):
            return self.get_response(request)

        store_id = request.headers.get("X-STORE-ID")

        if not store_id:
            return JsonResponse(
                {"error": "X-STORE-ID header is required"},
                status=400
            )

        try:
            store_uuid = uuid.UUID(store_id)
        except ValueError:
            return JsonResponse(
                {"error": "Invalid X-STORE-ID format"},
                status=400
            )

        Store = apps.get_model("db", "Store")

        try:
            store = Store.objects.get(id=store_uuid)
        except Store.DoesNotExist:
            return JsonResponse(
                {"error": "Store not found"},
                status=400
            )

        request.store = store
        return self.get_response(request)
