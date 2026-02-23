
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import ShippingPlan, ShippingRule
from mixins.drf_views import CustomResponse


class ShippingPlanAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        store = request.store
        user = request.user
        data = request.data

        flat_rate = data.get("flat_rate")
        free_above_amount = data.get("free_above_amount")
        if flat_rate is None:
            return CustomResponse().errorResponse(
                description="flat_rate is required"
            )

        plan = ShippingPlan.objects.filter(store=store).first()
        if not plan:
            plan = ShippingPlan.objects.create(
                store=store,
                name=data.get("name"),
                flat_rate=flat_rate,
                free_above_amount=free_above_amount,
                created_by=user.id,
                is_active=True
            )
        else:
            plan.flat_rate = flat_rate
            plan.free_above_amount = free_above_amount
            plan.updated_by = user.id
            plan.save()
        return CustomResponse().successResponse(data={}, description="Shipping plan saved successfully")

    def get(self, request):
        store = request.store
        plan = ShippingPlan.objects.filter(store=store).values(
            "id", "name", "flat_rate", "free_above_amount", "is_active"
        ).first()
        return CustomResponse().successResponse(data=plan, description="Shipping plan fetched")


class ShippinPlanCrud(APIView):
    permission_classes = [IsAuthenticated]


    def post(self, request):
        store = request.store
        user = request.user
        data = request.data

        plan_id = data.get("plan_id")
        pincode = data.get("pincode")
        rate = data.get("rate")

        if not plan_id or not pincode or rate is None:
            return CustomResponse().errorResponse(
                description="plan_id, pincode, rate are required"
            )
        plan = ShippingPlan.objects.filter(id=plan_id).first()
        if not plan:
            return CustomResponse().errorResponse(
                description="plan id is invalid"
            )
        existing = plan.rules.filter(pincode=pincode).first()
        if existing:
            existing.rate=rate
            existing.updated_by = user.id
            existing.save()
        else:
            rule = plan.rules.create(
                pincode=pincode,
                rate=rate,
                created_by=user.id,
            )
        return CustomResponse().successResponse(data={}, description="Shipping rule saved successfully")

    def get(self,request):
        plan_id = request.GET.get("plan_id")
        if not plan_id:
            return CustomResponse().errorResponse(
                description="plan_id is required"
            )

        rules = ShippingRule.objects.filter(plan_id=plan_id)
        data = []
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        offset = (page - 1) * page_size
        rules = rules[offset: offset + page_size]
        for rule in rules:
            data.append({
                "id": rule.id,
                "pincode": rule.pincode,
                "rate": float(rule.rate)
            })
        return CustomResponse().successResponse(data=data, description="Shipping rule fetched successfully")










