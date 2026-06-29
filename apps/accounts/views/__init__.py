from .auth_views import RegisterView, LoginView, LogoutView, RefreshTokenView,    ForgotPasswordView, ResetPasswordView, ChangePasswordView,SendEmailVerificationView, VerifyEmailView,SendPhoneOtpView, VerifyPhoneOtpView
from .user_views import CurrentUserView, UploadAvatarView, UserListView, UserDetailView
from .student_views import StudentProfileView, UpdateStudentProfileView
from .tutor_views import TutorProfileView, UpdateTutorProfileView, TutorPublicProfileView, TutorListView
from .kyc_views import SubmitKYCView, MyKYCView, KYCListView, ApproveKYCView, RejectKYCView
from .admin_views import AdminDashboardView, AdminUserListView, LockUserView, UnlockUserView
from .log_views import SystemLogListView, SystemLogDetailView