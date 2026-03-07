import uuid
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from db.models.user import SubscriptionPlan, StoreSubscription, WebhookLog, SubscriptionPayment
from mixins.drf_views import CustomResponse


class CreateSubscriptionPlanAPI(APIView):

    permission_classes = [AllowAny]
    def post(self, request):

        name = request.data.get("name")
        code = request.data.get("code")
        amount = request.data.get("amount")
        billing_cycle = request.data.get("billing_cycle", "monthly")
        trial_days = request.data.get("trial_days", 0)
        features = request.data.get("features", {})

        if not name or not code or not amount:
            return CustomResponse.errorResponse(
                description="name, code and amount are required"
            )
        plan = SubscriptionPlan.objects.create(
            id=uuid.uuid4(),
            name=name,
            code=code,
            amount=amount,
            billing_cycle=billing_cycle,
            trial_days=trial_days,
            features=features
        )
        # Cashfree API call (example)
        payload = {
            "plan_id": f"{plan.id}",
            "plan_name": plan.name,
            "plan_type": "PERIODIC",
            "plan_currency": "INR",
            "plan_recurring_amount": 2416,
            "plan_max_amount": 3000,
            "plan_max_cycles": 60,
            "plan_intervals": 1,
            "plan_interval_type": "MONTH",
            "plan_note": ""
        }

        headers = {
            "x-api-version": "2025-01-01",
            "x-client-id": settings.CASHFREE_APP_ID,
            "x-client-secret": settings.CASHFREE_SECRET_KEY,
            "Content-Type": "application/json"
        }

        response = requests.post(
            settings.CASHFREE_PLAN_URL,
            json=payload,
            headers=headers
        )
        data = response.json()
        print(data)
        print(data["plan_id"])
        plan.cashfree_plan_id = data["plan_id"]
        plan.save()
        return CustomResponse.successResponse(
            data=data,
            description="Plan created successfully"
        )

    def get(self, request):
        queryset = (
            SubscriptionPlan.objects
            .filter(is_active=True)
            .values(
                "id",
                "name",
                "code",
                "amount",
                "billing_cycle",
                "features"
            )
            .order_by("amount")
        )

        return CustomResponse.successResponse(
            data=list(queryset)
        )

class CreateSubscriptionAPI(APIView):

    def post(self, request):

        store = request.user.store
        plan_id = request.data.get("plan_id")

        if not plan_id:
            return CustomResponse.errorResponse(
                description="plan_id is required"
            )
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Invalid plan"
            )
        subscription = StoreSubscription.objects.create(
            store=store,
            plan=plan,
            status="pending"
        )
        # Cashfree API call (example)
        payload = {
            "subscription_id": str(subscription.id),
            "plan_id": plan.cashfree_plan_id,
            "customer_details": {
                "customer_name": store.name,
                "customer_email": store.email,
                "customer_phone": store.mobile
            }
        }
        # these are lifeboat client-id and client secret
        headers = {
            "x-api-version": "2025-01-01",
            "x-client-id": settings.CASHFREE_APP_ID,
            "x-client-secret": settings.CASHFREE_SECRET_KEY,
            "Content-Type": "application/json"
        }
        response = requests.post(
            settings.CASHFREE_SUBSCRIPTION_URL,
            json=payload,
            headers=headers
        )
        data = response.json()
        subscription.cashfree_subscription_id = data.get("subscription_session_id")
        subscription.save()
        return CustomResponse.successResponse(
            data={
                "payment_link": data.get("subscription_url")
            }
        )


class SubscriptionWebhookLog:
    pass


class CashfreeWebhookAPI(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        payload = request.data
        event = payload.get("type")

        WebhookLog.objects.create(
            event_type=event,
            payload=payload
        )

        subscription_id = payload.get("data", {}).get("subscription_id")

        if not subscription_id:
            return CustomResponse.errorResponse(
                data=payload,
                description="Invalid Event"
            )
        try:
            subscription = StoreSubscription.objects.get(
                id=subscription_id
            )
        except StoreSubscription.DoesNotExist:
            return CustomResponse.errorResponse(
                data=payload,
                description="StoreSubscription not found"
            )

        if event == "SUBSCRIPTION_ACTIVATED":
            subscription.status = "active"
            subscription.start_date = timezone.now()
            subscription.next_billing_date = timezone.now() + timedelta(days=30)
            subscription.save()
        elif event == "SUBSCRIPTION_PAYMENT_SUCCESS":
            SubscriptionPayment.objects.create(
                subscription=subscription,
                amount=payload["data"]["amount"],
                status="success"
            )
            subscription.next_billing_date = timezone.now() + timedelta(days=30)
            subscription.save()
        elif event == "SUBSCRIPTION_PAYMENT_FAILED":
            subscription.status = "past_due"
            subscription.save()

        return CustomResponse.successResponse(
            data=payload,
            description="OK"
        )

class GetMySubscriptionAPI(APIView):

    def get(self, request):
        store = request.store
        subscription = (
            StoreSubscription.objects
            .filter(store=store)
            .values(
                "id",
                "status",
                "start_date",
                "next_billing_date",
                "plan__name",
                "plan__amount"
            )
            .order_by("-created_at")
            .first()
        )

        return CustomResponse.successResponse(
            data=subscription
        )