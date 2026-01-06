import uuid
import random
import json
import requests

from django.conf import settings

from db.models import User


def generate_username(user):
    """
    This function generates a username with combination of first name and last name and a random number.
    """
    random_suffix = uuid.uuid4().hex[:6]



    username = random_suffix
    if User.objects.filter(username=username).exists():
        return generate_username(user)
    return username

def generate_referral_code():
    """
    Generates a unique 6-character referral code (no prefix).
    """
    referral_code = uuid.uuid4().hex[:6].upper()

    if User.objects.filter(referral_code=referral_code).exists():
        return generate_referral_code()  # Retry if code already exists

    return referral_code

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]  # Get the first IP in the list
    else:
        ip = request.META.get('REMOTE_ADDR')  # Fallback to direct IP
    return ip


def generate_otp():
    # return "1234"
    return str(random.randint(1000, 9999))

def send_otp_to_mobile(otp, mobile):
    try:
        print("[OTP SMS] Sending OTP")
        print("Mobile:", mobile)
        print("OTP:", otp)

        url = "https://sms.lifeboattechnologies.com/dev/bulkV2"

        params = {
            "authorization": settings.SMS_AUTH_KEY,   # same as URL
            "route": "dlt",
            "sender_id": settings.SMS_SENDER_ID,      # THESRU
            "message": settings.SMS_DLT_TEMPLATE_ID,  # 8764
            "variables_values": f"{otp}|",
            "flash": "0",
            "numbers": str(mobile)
        }

        print("Final URL Params:")
        print(json.dumps(params, indent=2))

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        print("Response Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code == 200:
            return True

        return False

    except Exception as e:
        print("Error sending OTP SMS:", str(e))
        return False