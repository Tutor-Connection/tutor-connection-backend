from django.urls import path

from .views import (
    RegisterView, LoginView, LogoutView, RefreshTokenView,
    ForgotPasswordView, ResetPasswordView, ChangePasswordView,
    SendEmailVerificationView, VerifyEmailView,
    SendPhoneOtpView, VerifyPhoneOtpView,
)

urlpatterns = [

    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),

    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),

    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),

    path(
        "refresh-token/",
        RefreshTokenView.as_view(),
        name="refresh-token",
    ),
    
    path("forgot-password/", ForgotPasswordView.as_view()),
    path("reset-password/", ResetPasswordView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),

    # Verification
    path("send-email-verification/", SendEmailVerificationView.as_view()),
    path("verify-email/", VerifyEmailView.as_view()),
    path("send-phone-otp/", SendPhoneOtpView.as_view()),
    path("verify-phone-otp/", VerifyPhoneOtpView.as_view()),
]