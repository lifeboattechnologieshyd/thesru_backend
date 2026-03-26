import uuid
import random
import json
import requests
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import get_connection
from django.core.exceptions import ImproperlyConfigured
from db.models import User, NotificationChannelConfig
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ImproperlyConfigured

# def generate_username(user):
#     """
#     This function generates a username with combination of first name and last name and a random number.
#     """
#     random_suffix = uuid.uuid4().hex[:6]
#
#
#
#     username = random_suffix
#     if User.objects.filter(username=username).exists():
#         return generate_username(user)
#     return username

def generate_username():
    """
    Generates a unique username using random UUID
    """
    while True:
        username = uuid.uuid4().hex[:6]   # short random string

        if not User.objects.filter(username=username).exists():
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

def send_sms_to_mobile(var1, mobile, config, msg):
    try:
        url = "https://sms.lifeboattechnologies.com/dev/bulkV2"
        params = {
            "authorization": config.api_key,
            "route": "dlt",
            "sender_id": config.sender_id,      # THESRU
            "message": msg,  # 8764
            "variables_values": var1,
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




def get_email_connection_from_config(config):
    print(" Creating SMTP connection...", flush=True)

    if not all([
        config.smtp_host,
        config.smtp_port,
        config.smtp_user,
        config.smtp_password,
    ]):
        print(" SMTP config missing", flush=True)
        raise ImproperlyConfigured(
            f"SMTP not configured for store: {config.store.name}"
        )

    print(f"SMTP Config Found: {config.smtp_host}:{config.smtp_port}", flush=True)

    connection = get_connection(
        host=config.smtp_host,
        port=config.smtp_port,
        username=config.smtp_user,
        password=config.smtp_password,
        use_tls=True,
        use_ssl=False,
        timeout=20,
    )

    print(" SMTP Connection object created", flush=True)
    return connection

def send_order_created_admin_email(order):
    print(" EMAIL FUNCTION STARTED", flush=True)

    store = order.store

    #  Get EMAIL config
    config = NotificationChannelConfig.objects.filter(
        store=store,
        channel="EMAIL",
        is_active=True
    ).first()

    if not config:
        print(" No EMAIL config found", flush=True)
        return

    print(" EMAIL config found", flush=True)

    #  Get admins
    admins = User.objects.filter(
        store=store,
        user_role__icontains="ADMIN",
        email__isnull=False
    ).exclude(email="")

    if not admins.exists():
        print(" No admin users found", flush=True)
        return

    recipients = [a.email for a in admins]
    print(f" Recipients: {recipients}", flush=True)

    subject = f"New Order Created | {order.order_number}"
    print(f" Subject: {subject}", flush=True)

    context = {
        "order": order,
        "store": store,
    }

    print(" Rendering HTML template...", flush=True)
    html_body = render_to_string(
        "store/admin_order_created.html",
        context
    )

    text_body = f"""
New order created

Order Number: {order.order_number}
Customer: {order.user.username}
Amount: ₹{order.amount}
"""

    from_email = f"{store.name} <{config.smtp_user}>"
    print(f"From Email: {from_email}", flush=True)

    try:
        connection = get_email_connection_from_config(config)

        print("Creating email object...", flush=True)
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=recipients,
            connection=connection
        )

        email.attach_alternative(html_body, "text/html")

        print(" Sending email...", flush=True)
        email.send(fail_silently=False)

        print(" EMAIL SENT SUCCESSFULLY", flush=True)

    except Exception as e:
        print(f" EMAIL FAILED: {str(e)}", flush=True)