from django.utils import timezone

from db.models import UserOTP


def cleanup_expired_otps():
    print(" OTP Cleanup started")

    now = timezone.now()
    print(f" Current time: {now}")

    expired_qs = UserOTP.objects.filter(
        expires_at__lt=now
    )

    count = expired_qs.count()
    print(f"Found {count} expired OTP(s)")

    deleted_count, _ = expired_qs.delete()

    print(f"Deleted {deleted_count} expired OTP(s)")
    print(" OTP Cleanup finished")

    return deleted_count