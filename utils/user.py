import uuid
import random
import json
import requests
from django.core.mail import send_mail
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

def send_sms_to_mobile(var1, mobile, store, msg):
    try:
        url = "https://sms.lifeboattechnologies.com/dev/bulkV2"
        params = {
            "authorization": store.sms_auth_key,   # same as URL
            "route": "dlt",
            "sender_id": store.sms_sender_id,      # THESRU
            "message": msg,  # 8764
            "variables_values": f"{var1}|",
            "flash": "0",
            "numbers": str(mobile)
        }
        response = requests.get(
            url,
            params=params,
            timeout=10
        )
        if response.status_code == 200:
            return True
        return False

    except Exception as e:
        print("Error sending OTP SMS:", str(e))
        return False


from django.conf import settings

def get_storage_path_from_url(url):
    if not url:
        return None

    media_url = settings.MEDIA_URL.rstrip("/")

    if url.startswith(media_url):
        return url.replace(media_url, "", 1).lstrip("/")

    if "/media/" in url:
        return url.split("/media/", 1)[1]

    return None

def version_to_tuple(version):
    return tuple(map(int, version.split(".")))


def send_otp_email(email, otp):
    send_mail(
        subject="Your OTP Code",
        message=f"Use OTP {otp} to login to thesapphire house. OTP is valid for 10 minutes. Do not share this OTP with anyone.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

# ldvq myjr huxg ekco
# Use OTP {#numeric#} to login to FamiliFirst. OTP is valid for 10 minutes. Do not share this OTP with anyone.