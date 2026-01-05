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


def send_otp_to_mobile(otp, mobile):
    try:
        print("📨 [OTP SMS] Starting send_otp_to_mobile()")
        print(f"📱 Mobile: {mobile}")
        print(f"🔢 OTP: {otp}")

        url = "https://sms.lifeboattechnologies.com/dev/bulkV2"
        print(f"🌐 URL: {url}")

        payload = {
            "variables_values": str(otp),

            "route": "dlt",
            "sms_details": "1",
            "flash": "1",
            "numbers": str(mobile),
            "sender_id": settings.FULL2ADS_SENDER_ID,
            "message": settings.FULL2ADS_DLT_TEMPLATE_ID,
            "entity_id": settings.FULL2ADS_DLT_ENTITY_ID
        }
        print("🔎 variables_values =", payload["variables_values"])



        print("📦 Payload:")
        print(json.dumps(payload, indent=2))

        headers = {
            "accept": "application/json",
            "authorization": "****MASKED_AUTH_KEY****",
            "content-type": "application/json"
        }

        print("🧾 Headers:")
        print(headers)

        print("🚀 Sending SMS request...")
        response = requests.post(
            url,
            headers={
                "accept": "application/json",
                "authorization": settings.FULL2ADS_AUTH_KEY,
                "content-type": "application/json"
            },
            json=payload,
            timeout=10
        )

        print(f"📡 Response Status Code: {response.status_code}")
        print(f"📨 Raw Response Text: {response.text}")

        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ Parsed JSON Response:")
                print(json.dumps(data, indent=2))

                if data.get("status") in [True, "success", "ok"]:
                    print("🎉 OTP SMS sent successfully")
                    return True
            except Exception:
                print("⚠️ Response is not JSON, assuming success")
                return True

        print("❌ OTP SMS failed")
        return False

    except Exception as e:
        print("🔥 Exception occurred while sending OTP SMS")
        print(str(e))
        return False