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


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30, null=True)
    username = models.CharField(max_length=30, unique=True)
    user_role = ArrayField(models.CharField(max_length=50, ), blank=True, null=True)
    profile_image = models.CharField(max_length=400, null=True)
    email = models.EmailField(max_length=100, null=True)
    referral_code = models.CharField(max_length=20, null=True)
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
            models.Index(fields=["username"]),
        ]

    def __str__(self):
        return f"{self.mobile}"


class UserOTP(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(null=True)
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
            models.Index(fields=["mobile", "expires_at", "otp"]),
            models.Index(fields=["email", "expires_at", "otp"]),
        ]