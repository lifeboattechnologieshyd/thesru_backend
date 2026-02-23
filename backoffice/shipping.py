
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

    def put(self, request, id=None):
        store = request.store
        user = request.user
        data = request.data

        if not id:
            return CustomResponse().errorResponse(
                description="plan id is required"
            )

        plan = ShippingPlan.objects.filter(id=id, store=store).first()
        if not plan:
            return CustomResponse().errorResponse(
                description="Shipping plan not found"
            )

        plan.name = data.get("name", plan.name)
        plan.flat_rate = data.get("flat_rate", plan.flat_rate)
        plan.free_above_amount = data.get(
            "free_above_amount", plan.free_above_amount
        )
        plan.is_active = data.get("is_active", plan.is_active)
        plan.updated_by = user.id
        plan.save()

        return CustomResponse().successResponse(
            data={},
            description="Shipping plan updated successfully"
        )


    def delete(self, request, id=None):
        store = request.store

        if not id:
            return CustomResponse().errorResponse(
                description="plan id is required"
            )

        plan = ShippingPlan.objects.filter(id=id, store=store).first()
        if not plan:
            return CustomResponse().errorResponse(
                description="Shipping plan not found"
            )

        plan.delete()

        return CustomResponse().successResponse(
            data={},
            description="Shipping plan deleted successfully"
        )


class ShippingRuleAPIView(APIView):
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

        plan = ShippingPlan.objects.filter(
            id=plan_id,
            store=store
        ).first()

        if not plan:
            return CustomResponse().errorResponse(
                description="Invalid plan id"
            )

        rule = ShippingRule.objects.create(
            plan=plan,
            pincode=pincode,
            rate=rate,
            created_by=user.id
        )

        return CustomResponse().successResponse(
            data={"id": rule.id},
            description="Shipping rule created successfully"
        )


    def get(self, request):
        plan_id = request.GET.get("plan_id")
        if not plan_id:
            return CustomResponse().errorResponse(
                description="plan_id is required"
            )

        rules = ShippingRule.objects.filter(plan_id=plan_id)
        data = []

        for rule in rules:
            data.append({
                "id": rule.id,
                "pincode": rule.pincode,
                "rate": float(rule.rate)
            })

        return CustomResponse().successResponse(
            data=data,
            description="Shipping rules fetched successfully"
        )


    def put(self, request, id=None):
        user = request.user
        data = request.data

        if not id:
            return CustomResponse().errorResponse(
                description="rule id is required"
            )

        rule = ShippingRule.objects.filter(id=id).first()
        if not rule:
            return CustomResponse().errorResponse(
                description="Shipping rule not found"
            )

        rule.pincode = data.get("pincode", rule.pincode)
        rule.rate = data.get("rate", rule.rate)
        rule.updated_by = user.id
        rule.save()

        return CustomResponse().successResponse(
            data={},
            description="Shipping rule updated successfully"
        )


    def delete(self, request, id=None):
        if not id:
            return CustomResponse().errorResponse(
                description="rule id is required"
            )

        rule = ShippingRule.objects.filter(id=id).first()
        if not rule:
            return CustomResponse().errorResponse(
                description="Shipping rule not found"
            )

        rule.delete()

        return CustomResponse().successResponse(
            data={},
            description="Shipping rule deleted successfully"
        )










