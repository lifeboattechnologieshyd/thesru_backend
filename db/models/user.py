import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from db.mixins import AuditModel


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
    mobile = models.BigIntegerField(
        validators=[MinValueValidator(1000000000), MaxValueValidator(9999999999)],
        null=False
    )
    address = models.CharField(max_length=100)
    logo = models.CharField(max_length=300)
    gst_number = models.CharField(max_length=100,unique=True, null=True)
    client_id = models.CharField(null=False, unique=True)
    client_secret = models.CharField(null=False, unique=True)
    webhook = models.CharField(max_length=100)
    url = models.CharField(max_length=100)
    product_code = models.CharField(max_length=3,null=True)

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
    identifier = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "store_client"

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
    username = models.CharField(max_length=30, unique=True)
    user_role = ArrayField(models.CharField(max_length=50, ), blank=True, null=True)
    profile_image = models.CharField(max_length=400, null=True)
    email = models.EmailField(max_length=100, null=True)
    referral_code = models.CharField(max_length=20, null=True)
    wallet_balance = models.DecimalField(max_digits=12,decimal_places=2,default=0.00)
    mobile = models.BigIntegerField(
        validators=[MinValueValidator(1000000000), MaxValueValidator(9999999999)], null=True
    )
    device_id = models.CharField(max_length=100, null=True)
    country = models.CharField(max_length=30,null=True)
    gender =  models.CharField(max_length=30, null=True)
    dob = models.DateField(null=True)


    objects = CustomUserManager()

    USERNAME_FIELD = "username"
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
        related_name="sessions"
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