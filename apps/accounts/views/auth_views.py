import random

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.utils import timezone
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import Accounts
from ..authentication import JWTAccountAuthentication
from ..serializers import (RegisterSerializer, LoginSerializer,
                           ForgotPasswordSerializer,
                            ResetPasswordSerializer,
                            ChangePasswordSerializer,
                            EmailSerializer,
                            VerifyEmailSerializer,
                            PhoneSerializer,
                            VerifyPhoneSerializer,)


class RegisterView(APIView):

    permission_classes = []

    def post(self, request):

        serializer = RegisterSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()

        return Response(
            {
                "message": "Register successfully."
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):

    permission_classes = []

    def post(self, request):

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = serializer.validated_data["account"]

        account.last_login_at = timezone.now()
        account.save(update_fields=["last_login_at"])

        refresh = RefreshToken()

        refresh["account_id"] = account.id
        refresh["email"] = account.email

        access = refresh.access_token

        return Response({
            "message": "Login successfully.",
            "access": str(access),
            "refresh": str(refresh),
            "user": {
                "id": account.id,
                "email": account.email,
                "phone": account.phone,
                "status": account.status,
                "email_verified": account.email_verified,
                "phone_verified": account.phone_verified,
            }
        })

class LogoutView(APIView):

    authentication_classes = [JWTAccountAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):

        refresh_token = request.data.get("refresh")

        try:

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"message": "Logout successfully."},
                status=status.HTTP_200_OK,
            )

        except Exception:

            return Response(
                {"message": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RefreshTokenView(APIView):

    permission_classes = []

    def post(self, request):

        refresh_token = request.data.get("refresh")

        try:

            refresh = RefreshToken(refresh_token)

            return Response(
                {
                    "access": str(refresh.access_token)
                }
            )

        except Exception:

            return Response(
                {
                    "message": "Refresh token invalid."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
            
# =====================================================
# PASSWORD
# =====================================================

class ForgotPasswordView(APIView):
    """Gửi link reset password qua email (token có hạn 15 phút)."""
    permission_classes = []

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        account = Accounts.objects.get(
        email=email,
        deleted_at__isnull=True
    )

        signer = TimestampSigner(salt="password-reset")
        token = signer.sign(account.id)
        print(token)

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        send_mail(
            subject="Yêu cầu đặt lại mật khẩu",
            message=(
                f"Nhấn vào link sau để đặt lại mật khẩu: {reset_link}\n"
                "Link có hiệu lực trong 15 phút."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response(
            {"message": "Đã gửi link đặt lại mật khẩu tới email."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """Đặt lại mật khẩu bằng token nhận được từ email."""
    permission_classes = []

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["password"]

        signer = TimestampSigner(salt="password-reset")
        try:
            account_id = int(signer.unsign(token, max_age=900))  # 15 phút
        except SignatureExpired:
            return Response(
                {"message": "Link đặt lại mật khẩu đã hết hạn."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except BadSignature:
            return Response(
                {"message": "Token không hợp lệ."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            account = Accounts.objects.get(id=account_id)
        except Accounts.DoesNotExist:
            return Response(
                {"message": "Tài khoản không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )

        account.password_hash = make_password(new_password)
        account.updated_at = timezone.now()
        account.save(update_fields=["password_hash", "updated_at"])

        return Response(
            {"message": "Đặt lại mật khẩu thành công."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """Đổi mật khẩu khi đã đăng nhập."""
    authentication_classes = [JWTAccountAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = request.user  # Accounts instance, từ JWTAccountAuthentication
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not check_password(old_password, account.password_hash):
            return Response(
                {"message": "Mật khẩu cũ không đúng."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account.password_hash = make_password(new_password)
        account.updated_at = timezone.now()
        account.save(update_fields=["password_hash", "updated_at"])

        return Response(
            {"message": "Đổi mật khẩu thành công."},
            status=status.HTTP_200_OK,
        )


# =====================================================
# VERIFICATION - EMAIL
# =====================================================

class SendEmailVerificationView(APIView):
    """Gửi link xác thực email (token có hạn 30 phút)."""
    permission_classes = []

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            account = Accounts.objects.get(email=email)
        except Accounts.DoesNotExist:
            return Response(
                {"message": "Email không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if account.email_verified:
            return Response(
                {"message": "Email đã được xác thực trước đó."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        signer = TimestampSigner(salt="email-verification")
        token = signer.sign(account.id)
        verify_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        send_mail(
            subject="Xác thực địa chỉ email",
            message=(
                f"Nhấn vào link sau để xác thực email: {verify_link}\n"
                "Link có hiệu lực trong 30 phút."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response(
            {"message": "Đã gửi email xác thực."},
            status=status.HTTP_200_OK,
        )


class VerifyEmailView(APIView):
    """Xác thực email bằng token."""
    permission_classes = []

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        signer = TimestampSigner(salt="email-verification")
        try:
            account_id = int(signer.unsign(token, max_age=1800))  # 30 phút
        except SignatureExpired:
            return Response(
                {"message": "Link xác thực đã hết hạn."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except BadSignature:
            return Response(
                {"message": "Token không hợp lệ."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            account = Accounts.objects.get(id=account_id)
        except Accounts.DoesNotExist:
            return Response(
                {"message": "Tài khoản không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )

        account.email_verified = True
        account.updated_at = timezone.now()
        account.save(update_fields=["email_verified", "updated_at"])

        return Response(
            {"message": "Xác thực email thành công."},
            status=status.HTTP_200_OK,
        )


# =====================================================
# VERIFICATION - PHONE OTP
# =====================================================

OTP_CACHE_PREFIX = "phone_otp_"
OTP_TTL_SECONDS = 300  # 5 phút


class SendPhoneOtpView(APIView):
    """Gửi OTP 6 số tới số điện thoại (lưu tạm trong cache 5 phút)."""
    permission_classes = []

    def post(self, request):
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]

        try:
            account = Accounts.objects.get(phone=phone)
        except Accounts.DoesNotExist:
            return Response(
                {"message": "Số điện thoại không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if account.phone_verified:
            return Response(
                {"message": "Số điện thoại đã được xác thực trước đó."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = f"{random.randint(0, 999999):06d}"
        cache.set(f"{OTP_CACHE_PREFIX}{phone}", otp, timeout=OTP_TTL_SECONDS)

        # TODO: tích hợp nhà cung cấp SMS thực tế (eSMS, Twilio, Speed SMS...)
        print(f"[DEBUG] OTP cho {phone}: {otp}")

        return Response(
            {"message": "Đã gửi mã OTP tới số điện thoại."},
            status=status.HTTP_200_OK,
        )


class VerifyPhoneOtpView(APIView):
    """Xác thực OTP đã gửi tới số điện thoại."""
    permission_classes = []

    def post(self, request):
        serializer = VerifyPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        otp = serializer.validated_data["otp"]

        cache_key = f"{OTP_CACHE_PREFIX}{phone}"
        cached_otp = cache.get(cache_key)

        if cached_otp is None:
            return Response(
                {"message": "OTP đã hết hạn hoặc chưa được gửi. Vui lòng yêu cầu lại."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cached_otp != otp:
            return Response(
                {"message": "Mã OTP không đúng."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            account = Accounts.objects.get(phone=phone)
        except Accounts.DoesNotExist:
            return Response(
                {"message": "Số điện thoại không tồn tại."},
                status=status.HTTP_404_NOT_FOUND,
            )

        account.phone_verified = True
        account.updated_at = timezone.now()
        account.save(update_fields=["phone_verified", "updated_at"])

        cache.delete(cache_key)

        return Response(
            {"message": "Xác thực số điện thoại thành công."},
            status=status.HTTP_200_OK,
        )