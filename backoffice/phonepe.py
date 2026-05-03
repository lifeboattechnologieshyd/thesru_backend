from django.conf import settings
from django.db import transaction
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from db.models import Order, Payment, OrderTimeLines, CouponUsage, User
from enums.store import PaymentStatus, OrderStatus, NotificationEvent
from mixins.drf_views import CustomResponse
from store.views import remove_cart_items
from utils.notification import trigger_notification
from utils.store import update_stock_after_order


def get_phonepe_client(gateway):
    client = StandardCheckoutClient.get_instance(
        client_id=gateway.client_id,
        client_secret=gateway.client_secret,
        client_version=int(settings.PHONEPE_CLIENT_VERSION),
        env=settings.PHONEPE_ENV,  # change to PRODUCTION later
        should_publish_events=False
    )
    return client

class UpdateOrderStatus(APIView):
    permission_classes = [AllowAny]


    def post(self, request):
        order_num = request.data.get("order_number")
        order = Order.objects.filter(order_number=order_num).first()
        if not order:
            return CustomResponse().errorResponse(data={}, description="NO order found")
        payment = Payment.objects.filter(order=order).first()
        if not payment:
            return CustomResponse().errorResponse(data={}, description="NO Payment found")
        if payment.status == PaymentStatus.COMPLETED:
            return CustomResponse().successResponse(
                data={
                    "order_number": order_num,
                    "final_payment_status": order.status,
                },
                description="Payment status verified with Cashfree"
            )
        client = get_phonepe_client(order.store.active_payment_gateway)
        response = client.get_order_status(order_num, details=False)
        print(response)
        state = response.state
        print(state)
        ph_status = state
        with transaction.atomic():
            payment.status = ph_status.upper()
            payment.save(update_fields=["status"])
            if ph_status.upper() == "COMPLETED":
                update_stock_after_order(order)
                order.status = OrderStatus.CREATED
                order.paid_online = payment.amount
                order.updated_by = "PAYMENT STATUS BY FE"
                order.save(update_fields=["status", "paid_online"])
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
                remove_cart_items(order.user, order.store)
            elif ph_status.upper() == "PENDING":
                pass
            else:
                order.status = OrderStatus.FAILED
                order.updated_by = "PAYMENT STATUS"
                order.save(update_fields=["status", "updated_by"])
                OrderTimeLines.objects.create(
                    order=order,
                    status=OrderStatus.CANCELLED,
                    remarks="Order Cancelled"
                )
        return CustomResponse().successResponse(
            data={
                "order_number": order_num,
                "final_payment_status": order.status,
            },
            description="Payment status verified with Phonepe and changed"
        )



