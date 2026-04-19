import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from db.mixins import AuditModel
from enums.store import PaymentStatus


class CustomUserManager(BaseUserManager):
    def create_user(self, mobile, password="password", **extra_fields):
        if not mobile:
            raise ValueError("The Mobile Number must be set")

        # extra_fields.setdefault("is_active", True)
        # extra_fields.setdefault("is_staff", False)
        # extra_fields.setdefault("is_superuser", False)

        user = self.model(mobile=mobile, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

class Store(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    primary_color = models.CharField(max_length=100, default="FFFFFF")
    secondary_color = models.CharField(max_length=100, default="FFFFFF")
    mobile = models.BigIntegerField(
        validators=[MinValueValidator(1000000000), MaxValueValidator(9999999999)],
        null=False
    )
    address = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True)
    logo = models.CharField(max_length=300,null=True)
    gst_number = models.CharField(max_length=100,unique=True, null=True)
    client_id = models.CharField(null=True)
    client_secret = models.CharField(null=True)
    product_code = models.CharField(max_length=3,null=True)
    email_login = models.BooleanField(default=True)
    mobile_login = models.BooleanField(default=True)
    aws_bucket_name = models.CharField(max_length=50, null=True, blank=True)
    cloudfront_domain = models.CharField(max_length=50, null=True, blank=True)

    # bo_title = models.CharField(max_length=50, null=True, blank=True)
    # bo_subtitle = models.CharField(max_length=50, null=True, blank=True)
    # highlights = ArrayField(models.CharField(max_length=50, ), blank=True, null=True)
    is_active = models.BooleanField(default=True)


    class Meta:
        db_table = "store"


class StoreClient(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="clients")
    CLIENT_TYPE_CHOICES = [
        ("WEB", "Web"),
        ("ANDROID", "Android"),
        ("IOS", "iOS"),
        ("POS", "POS"),
    ]

    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES)
    identifier = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "store_client"
        constraints = [
            models.UniqueConstraint(
                fields=['store', 'identifier'],
                name='unique_identifier_per_store'
            )
        ]

class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=30, null=True)
    # username = models.CharField(max_length=30, unique=True)
    user_role = ArrayField(models.CharField(max_length=50, ), blank=True, null=True)
    profile_image = models.CharField(max_length=400, null=True)
    email = models.EmailField(max_length=100, null=True)
    referral_code = models.CharField(max_length=20, null=True)
    wallet_balance = models.DecimalField(max_digits=12,decimal_places=2,default=0.00)
    mobile = models.CharField(
    max_length=15,
    db_index=True,
        null=True
    )
    device_id = models.CharField(max_length=100, null=True)
    fcm_id = models.CharField(max_length=500,blank=True, null=True)

    country = models.CharField(max_length=30,null=True)
    gender =  models.CharField(max_length=30, null=True)
    dob = models.DateField(null=True)
    created_by = models.CharField(
        max_length=255,
        null=True,
    )
    updated_by = models.CharField(
        max_length=255,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    objects = CustomUserManager()

    USERNAME_FIELD = "id"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "user"
        indexes = [
            models.Index(fields=["mobile"]),
            models.Index(fields=["email"]),
            models.Index(fields=["store"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['store', 'mobile'],
                name='unique_mobile_per_store'
            )
        ]

    def __str__(self):
        return f"{self.mobile}"


class UserOTP(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="user_otps"
    )

    mobile = models.BigIntegerField(
        null=True, validators=[MinValueValidator(1000000000), MaxValueValidator(9999999999)]
    )
    email = models.EmailField(max_length=100, null=True)
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "user_otp"
        indexes = [
            models.Index(fields=["store","mobile", "expires_at", "otp"]),
            models.Index(fields=["store","email", "expires_at", "otp"]),
        ]






class TempUser(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="temp_users"
    )
    mobile = models.BigIntegerField(
        null=True, validators=[MinValueValidator(1000000000), MaxValueValidator(9999999999)]
    )
    email = models.EmailField(max_length=100, null=True)
    device_id = models.CharField(max_length=100,null=True)


    class Meta:
        db_table = "temp_user"
        indexes = [
            models.Index(fields=["mobile"]),
            models.Index(fields=["email"]),
        ]


class ContactMessage(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True)
    email = models.CharField(max_length=100,null=True)
    subject = models.CharField(max_length=200,null=True)
    message = models.TextField(null=True)

    class Meta:
        db_table = "contact_message"



class UserSession(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="sessions",
        null=True
    )

    session_token = models.CharField(max_length=500, unique=True)
    refresh_token = models.CharField(max_length=500, unique=True)

    device_id = models.CharField(max_length=100, null=True, blank=True)
    device_type = models.CharField(
        max_length=20,
        choices=[
            ("WEB", "Web"),
            ("ANDROID", "Android"),
            ("IOS", "iOS")
        ]
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "user_session"
        indexes = [
            models.Index(fields=["user", "store"]),
            models.Index(fields=["session_token"]),
            models.Index(fields=["refresh_token"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.user_id} | {self.device_type}"


# core/models.py

class AppVersionConfig(AuditModel):
    OS_CHOICES = (
        ("android", "Android"),
        ("ios", "iOS"),
    )
    os = models.CharField(max_length=10, choices=OS_CHOICES)
    min_supported_version = models.CharField(max_length=20)
    latest_version = models.CharField(max_length=20)
    force_update = models.BooleanField(default=False)
    update_title = models.CharField(max_length=100, blank=True, null=True)
    update_message = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "version_configuration"
        indexes = [
            models.Index(fields=["os", "latest_version", "is_active"]),
        ]

    def __str__(self):
        return f"{self.os} | {self.latest_version}"


class Visitor(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="UUID for web, Device ID for mobile app"
    )


    # Store mapping
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="visitors"
    )

    #  Platform info
    platform = models.CharField(
        max_length=20,
        choices=[
            ("WEB", "Web"),
            ("ANDROID", "Android"),
            ("IOS", "iOS"),
        ]
    )

    #  link after login
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visits"
    )

    #  Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    #  Analytics
    visit_count = models.PositiveIntegerField(default=1)
    first_visited_at = models.DateTimeField(auto_now_add=True)
    last_visited_at = models.DateTimeField(auto_now=True)

    fcm_id = models.CharField(max_length=500, blank=True,null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)



    class Meta:
        db_table = "visitor"
        unique_together = ("store", "visitor_id")
        indexes = [
            models.Index(fields=["visitor_id"]),
            models.Index(fields=["platform"]),
            models.Index(fields=["store"]),
        ]

    def __str__(self):
        return f"{self.platform} | {self.visitor_id}"


class SubscriptionPlan(AuditModel):
    PLAN_TYPE_CHOICES = (
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    # Example: Basic, Pro, Advanced
    code = models.CharField(max_length=50, unique=True)
    # Example: BASIC, PRO, ADVANCED
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # 2000, 4000 etc
    billing_cycle = models.CharField(
        max_length=10,
        choices=PLAN_TYPE_CHOICES,
        default="monthly"
    )
    cashfree_plan_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    features = models.JSONField(default=dict, blank=True)
    # plan id returned by Cashfree
    trial_days = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "subscription_plans"
        ordering = ["amount"]

    def __str__(self):
        return f"{self.name} - ₹{self.amount}"


class StoreSubscription(AuditModel):

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        "Store",
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT
    )
    cashfree_subscription_id = models.CharField(
        max_length=120,
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    start_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    class Meta:
        db_table = "store_subscriptions"

class SubscriptionPayment(AuditModel):

    PAYMENT_STATUS = (
        ("success", "Success"),
        ("failed", "Failed"),
        ("pending", "Pending"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    subscription = models.ForeignKey(
        StoreSubscription,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    cashfree_payment_id = models.CharField(
        max_length=120,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS
    )

    payment_date = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "subscription_payments"

class WebhookLog(AuditModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)

    class Meta:
        db_table = "webhook_logs"


# this is being used for GPW Alumni
class Enrollments(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payload = models.JSONField()

    class Meta:
        db_table = "gpt_enrolls"

class BusinessOnboarding(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_email = models.EmailField(max_length=255)
    business_phone = models.CharField(max_length=15)
    mobile_number = models.CharField(max_length=15)
    payment_status = models.CharField( max_length=20,choices=PaymentStatus.choices,default=PaymentStatus.INITIATED)
    payment_url = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "business_onboarding"


class PaymentTransaction(AuditModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    onboarding = models.ForeignKey(
        BusinessOnboarding,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    merchant_transaction_id = models.CharField(max_length=255, unique=True)

    phonepe_transaction_id = models.CharField(max_length=255, null=True, blank=True)

    amount = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.INITIATED
    )

    payment_url = models.TextField(null=True, blank=True)

    response_data = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "payment_transaction"





