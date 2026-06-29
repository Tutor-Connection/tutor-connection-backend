from django.urls import path

from .views import (
    RegisterView, LoginView, LogoutView, RefreshTokenView,
    ForgotPasswordView, ResetPasswordView, ChangePasswordView,
    SendEmailVerificationView, VerifyEmailView,
    SendPhoneOtpView, VerifyPhoneOtpView,
    CurrentUserView, UploadAvatarView, UserListView, UserDetailView,
    StudentProfileView, UpdateStudentProfileView,
    TutorProfileView, UpdateTutorProfileView,
    TutorPublicProfileView, TutorListView,
    SubmitKYCView, MyKYCView, KYCListView, ApproveKYCView, RejectKYCView,
    SystemLogListView, SystemLogDetailView , AdminDashboardView,
    AdminUserListView,
    LockUserView,
    UnlockUserView,
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
    
    
    path('users/me/', CurrentUserView.as_view(), name='current-user'),   # GET + PUT
    path('users/avatar/', UploadAvatarView.as_view(), name='upload-avatar'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:id>/', UserDetailView.as_view(), name='user-detail'),
    
    path('students/me/', StudentProfileView.as_view(), name='student-profile'),  # GET + PUT/PATCH

    path('tutors/me/', TutorProfileView.as_view(), name='tutor-profile'),        # GET + PUT/PATCH
    path('tutors/<int:id>/', TutorPublicProfileView.as_view(), name='tutor-public-detail'),
    path('tutors/', TutorListView.as_view(), name='tutor-list'),
    
    path('kyc/submit/', SubmitKYCView.as_view(), name='kyc-submit'),
    path('kyc/me/', MyKYCView.as_view(), name='kyc-me'),

    path('admin/kyc/', KYCListView.as_view(), name='kyc-list'),
    path('admin/kyc/<int:id>/approve/', ApproveKYCView.as_view(), name='kyc-approve'),
    path('admin/kyc/<int:id>/reject/', RejectKYCView.as_view(), name='kyc-reject'),
    
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/<int:id>/lock/', LockUserView.as_view(), name='admin-user-lock'),
    path('admin/users/<int:id>/unlock/', UnlockUserView.as_view(), name='admin-user-unlock'),
    path('admin/logs/', SystemLogListView.as_view(), name='admin-log-list'),
    path('admin/logs/<int:id>/', SystemLogDetailView.as_view(), name='admin-log-detail'),
]
    
