from phonepe.sdk.pg.payments.v2.models.request.prefill_user_login_details import PrefillUserLoginDetails
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.env import Env
from django.conf import settings


def get_phonepe_client(gateway):
    client = StandardCheckoutClient.get_instance(
        client_id=gateway.client_id,
        client_secret=gateway.client_secret,
        client_version=int(settings.PHONEPE_CLIENT_VERSION),
        env=settings.PHONEPE_ENV,  # change to PRODUCTION later
        should_publish_events=False
    )
    return client

from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest
from phonepe.sdk.pg.common.models.request.meta_info import MetaInfo


def create_phonepe_payment(user,obj,amount_paisa, gateway):
    client = get_phonepe_client(gateway)
    print(" Creating PhonePe Payment for:", obj.order_number)
    meta_info = MetaInfo()
    prefill_user_login_details = PrefillUserLoginDetails(phone_number=user.mobile)
    request = StandardCheckoutPayRequest.build_request(
        merchant_order_id=str(obj.order_number),
        amount=amount_paisa,  # paisa
        redirect_url=f"http://localhost:5173/payment-success?{obj.order_number}",
        meta_info=meta_info,
        message="Payment for onboarding",
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