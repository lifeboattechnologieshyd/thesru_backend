import random
import string

from django.core.validators import MaxValueValidator, MinValueValidator
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from db.models import User


def GenerateRandomUsername(length=6):
    my_username = "GUEST" + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return my_username


def GenerateRandomReferral(length=6):
    characters = string.ascii_uppercase + string.digits
    random_string = "".join(random.choice(characters) for _ in range(length))
    return "RF" + random_string


class UserMasterSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(default=GenerateRandomUsername, required=False)
    referral_code = serializers.CharField(default=GenerateRandomReferral, required=False)
    password = serializers.CharField(write_only=True, default="password", required=False)
    first_name = serializers.CharField(max_length=30, allow_null=True, required=False)
    last_name = serializers.CharField(max_length=30, allow_null=True, required=False)
    profile_image = serializers.CharField(max_length=400, allow_null=True, required=False)
    email = serializers.EmailField(max_length=100, allow_null=True, required=False)
    mobile = serializers.IntegerField(allow_null=True,
        validators=[
            MinValueValidator(1000000000),
            MaxValueValidator(9999999999),
            UniqueValidator(queryset=User.objects.all()),

        ]
    )
    device_id = serializers.CharField(max_length=100,allow_null=True)




    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "password",
            "username",
            "profile_image",
            "email",
            "referral_code",
            "mobile",
            "device_id",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user