import json

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from phonepe.sdk.pg.payments.v2.models.request.prefill_user_login_details import PrefillUserLoginDetails
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.env import Env
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from db.models import Payment, Order, OrderTimeLines, CouponUsage, Cart
from db.models.user import WebhookLog, User
from enums.store import PaymentStatus, OrderStatus, NotificationEvent
from mixins.drf_views import CustomResponse
from utils.notification import trigger_notification
from utils.store import update_stock_after_order
from utils.user import send_order_created_admin_email

from phonepe.sdk.pg.env import Env

def get_phonepe_client(gateway):
    # Normalize env safely
    env_str = str(settings.PHONEPE_ENV).upper().strip()

    if env_str == "SANDBOX":
        env = Env.SANDBOX
    elif env_str == "PRODUCTION":
        env = Env.PRODUCTION
    else:
        raise ValueError(f"Invalid PHONEPE_ENV: {settings.PHONEPE_ENV}")

    # Optional debug (remove in prod)
    print("PHONEPE ENV:", env_str)
    print("CLIENT_ID:", gateway.client_id)

    client = StandardCheckoutClient.get_instance(
        client_id=gateway.client_id,
        client_secret=gateway.client_secret,
        client_version=int(settings.PHONEPE_CLIENT_VERSION),
        env=env,
        should_publish_events=False
    )
    return client

from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest
from phonepe.sdk.pg.common.models.request.meta_info import MetaInfo

def get_base_url(client_identifier: str) -> str:
    if not client_identifier:
        raise ValueError(f"Unknown client_identifier: {client_identifier}")
    return client_identifier.rstrip("/")

def create_phonepe_payment(user,obj,amount_paisa, gateway, identifier):
    client = get_phonepe_client(gateway)
    print(" Creating PhonePe Payment for:", obj.order_number)

    base_url = get_base_url(identifier)
    redirect_url = f"{base_url}/payment-success?{obj.order_number}"
    meta_info = MetaInfo()
    prefill_user_login_details = PrefillUserLoginDetails(phone_number=user.mobile)
    request = StandardCheckoutPayRequest.build_request(
        merchant_order_id=str(obj.order_number),
        amount=amount_paisa,  # paisa
        redirect_url=redirect_url,
        meta_info=meta_info,
        message="Payment for your order",
        expire_after=3600,
        prefill_user_login_details=prefill_user_login_details
    )
    response = client.pay(request)
    print(" SDK Response:", response)
    return {
        "redirect_url": response.redirect_url,
        "order_id": response.order_id
    }

def get_status(obj,gateway):
    client = get_phonepe_client(gateway)
    merchant_order_id = obj.order_number
    response = client.get_order_status(merchant_order_id, details=False)
    state = response.state
    return state


class PhonePeWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print("Webhook HIT")
        print("Headers:", request.headers)
        print("Raw Body:", request.body.decode("utf-8"))
        body = json.loads(request.body.decode("utf-8"))
        payload = body["payload"]
        # logs of webhook just for records...
        log = WebhookLog()
        log.event_type = "ORDER_PAYMENT_WEBHOOK"
        log.gateway = "phonepe"
        log.payload = payload
        log.save()
        with transaction.atomic():
            order = Order.objects.select_for_update().filter(order_number=payload["merchantOrderId"]).first()
            if not order:
                print("No Order Found with Order Number")
                return CustomResponse().successResponse(data={},
                                                        description="No Order Found with Order Number"
                                                        )
            payment = Payment.objects.filter(order=order).first()
            # If no DB records → still return 200
            if not payment:
                print("Order/Payment not found for order_id:")
                return CustomResponse().successResponse(data={},
                                                        description="Webhook received"
                                                        )
            try:
                txn = Payment.objects.filter(ph_order_id=payload.get("orderId", None)).first()
            except Exception as e:
                return CustomResponse.successResponse(data={}, description="Transaction not found")


            client = get_phonepe_client(txn.order.store.active_payment_gateway)
            try:
                callback_response = client.validate_callback(
                    username="charan",
                    password="Password123",
                    callback_header_data=request.headers.get("Authorization"),
                    callback_response_data=request.body.decode("utf-8")
                )
                print(" Webhook Validation Success")

            except Exception as e:
                print(" Webhook Validation Failed:", str(e))
                return CustomResponse.successResponse(data={}, description="Ignored")
            event = callback_response.type
            print("Event:", event)
            print("Payload:", payload)

            # Idempotency
            if txn.status == PaymentStatus.COMPLETED:
                return CustomResponse.successResponse(data={},description="Already processed")

            # Update status
            state = payload["state"]

            print("Payment State:", state)

            if state == "COMPLETED":
                txn.status = PaymentStatus.COMPLETED
                print("Payment COMPLETED")
                update_stock_after_order(order)
                payment.status = PaymentStatus.COMPLETED
                payment.updated_by = event
                payment.save(update_fields=["status", "updated_by"])
                order.status = OrderStatus.CREATED
                order.paid_online = order.amount
                order.updated_by = event
                order.save(update_fields=["status", "paid_online", "updated_by"])
                OrderTimeLines.objects.create(
                    order=order,
                    status=OrderStatus.CREATED,
                    remarks="Order Placed"
                )
                if order.coupon is not None:
                    CouponUsage.objects.create(
                        coupon=order.coupon,
                        user=order.user,
                        order=order
                    )
                context = {
                    "var": f"{order.user.name}|{order.order_number[-5:]}|"
                }
                trigger_notification(order.store, NotificationEvent.ORDER_PLACED, context, order.user.mobile,
                                     order.user.email)
                admins = User.objects.filter(store=order.store, user_role__contains=["ADMIN"])
                context = {
                    "var": f"#{order.order_number[-5:]}|"
                }
                for admin in admins:
                    trigger_notification(order.store, NotificationEvent.ADMIN_ORDER_RECEIVED, context, admin.mobile,
                                         admin.email)
                Cart.objects.filter(user=order.user, store=order.store).delete()

            elif state == "FAILED":
                txn.status = PaymentStatus.FAILED
                print("Payment FAILED")
            else:
                txn.status = PaymentStatus.PENDING
                print("Payment CANCELLED")
            txn.save()
            print(" Transaction updated")
            return CustomResponse.successResponse(data={},description="Webhook processed")