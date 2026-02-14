import uuid
import random
import json
import requests
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import get_connection
from django.core.exceptions import ImproperlyConfigured
from db.models import User
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ImproperlyConfigured

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




def get_store_email_connection(store):
    """
    Returns SMTP connection for the store.
    Raises error if SMTP is not configured.
    """
    if not all([
        store.smtp_host,
        store.smtp_port,
        store.smtp_username,
        store.smtp_password,
    ]):
        raise ImproperlyConfigured(
            f"SMTP not configured for store: {store.name}"
        )

    return get_connection(
        host=store.smtp_host,
        port=store.smtp_port,
        username=store.smtp_username,
        password=store.smtp_password,
        use_tls=store.smtp_use_tls,
    )


def send_order_created_admin_email(order):
    store = order.store

    admins = User.objects.filter(
        store=store,
        user_role__contains=["ADMIN"],
        email__isnull=False
    ).exclude(email="")

    if not admins.exists():
        return

    recipients = [a.email for a in admins]

    subject = f"New Order Created | {order.order_number}"

    context = {
        "order": order,
        "store": store,
    }

    html_body = render_to_string(
        "store/admin_order_created.html",
        context
    )

    text_body = f"""
New order created

Order Number: {order.order_number}
Amount: ₹{order.amount}
"""

    from_email = f"{store.name} <{store.smtp_username}>"

    connection = get_store_email_connection(store)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=recipients,
        connection=connection
    )

    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)