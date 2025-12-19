import uuid
import random

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



