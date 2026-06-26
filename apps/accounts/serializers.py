from django.contrib.auth.hashers import make_password, check_password
from rest_framework import serializers
from django.utils import timezone

from .models import Accounts, Users


class RegisterSerializer(serializers.Serializer):

    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(max_length=255)
    role = serializers.ChoiceField(
        choices=["student", "tutor", "admin"]
    )

    def validate_email(self, value):
        if Accounts.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate_phone(self, value):
        if Accounts.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone already exists.")
        return value

    def create(self, validated_data):

        password = validated_data.pop("password")

        account = Accounts.objects.create(
            email=validated_data["email"],
            phone=validated_data["phone"],
            password_hash=make_password(password),
            login_provider="LOCAL",
            status="ACTIVE",
            email_verified=False,
            phone_verified=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        role = validated_data["role"].upper()

        user = Users.objects.create(
            account=account,
            full_name=validated_data["full_name"],
            role=role,
            is_online=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"]
        password = attrs["password"]

        try:
            account = Accounts.objects.get(
                email=email,
                deleted_at__isnull=True
            )
        except Accounts.DoesNotExist:
            raise serializers.ValidationError(
                "Email hoặc mật khẩu không đúng."
            )

        if not check_password(password, account.password_hash):
            raise serializers.ValidationError(
                "Email hoặc mật khẩu không đúng."
            )

        # chỉ cho ACTIVE đăng nhập
        if account.status != "ACTIVE":
            raise serializers.ValidationError(
                f"Tài khoản đang ở trạng thái {account.status}."
            )
        if account.deleted_at is not None:
            raise serializers.ValidationError(
                "Account has been deleted."
            )
        attrs["account"] = account
        return attrs
    
    
    
# ==========================
# Forgot Password
# ==========================

class ForgotPasswordSerializer(serializers.Serializer):

    email = serializers.EmailField()

    def validate_email(self, value):

        if not Accounts.objects.filter(email=value).exists():

            raise serializers.ValidationError(
                "If this email exists, a reset link has been sent."
            )

        return value


# ==========================
# Reset Password
# ==========================

class ResetPasswordSerializer(serializers.Serializer):

    token = serializers.CharField()

    password = serializers.CharField(min_length=6)


# ==========================
# Change Password
# ==========================

class ChangePasswordSerializer(serializers.Serializer):

    old_password = serializers.CharField()

    new_password = serializers.CharField(min_length=6)


# ==========================
# Email Verification
# ==========================

class EmailSerializer(serializers.Serializer):

    email = serializers.EmailField()


class VerifyEmailSerializer(serializers.Serializer):

    token = serializers.CharField()


# ==========================
# Phone OTP
# ==========================

class PhoneSerializer(serializers.Serializer):

    phone = serializers.CharField(max_length=20)


class VerifyPhoneSerializer(serializers.Serializer):

    phone = serializers.CharField(max_length=20)

    otp = serializers.CharField(max_length=6)