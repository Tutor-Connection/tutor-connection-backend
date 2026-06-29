from datetime import date

from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from rest_framework import serializers

from .models import Accounts, Users, StudentProfiles, TutorProfiles, AdminProfiles, KycDocuments, SystemLogs

REQUIRED_DOCUMENT_TYPES = {
    "ID_CARD",
    "STUDENT_CARD",
    "DEGREE",
    "CERTIFICATE",
}

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
        
        if role == "STUDENT":
            StudentProfiles.objects.create(
                user=user,
                grade="",
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

        elif role == "TUTOR":
            TutorProfiles.objects.create(
                user=user,
                teaching_fee=0,
                rating_avg=0,
                total_reviews=0,
                response_rate=0,
                trusted_badge=False,
                is_kyc_verified=False,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

        elif role == "ADMIN":
            AdminProfiles.objects.create(
                user=user,
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
    
class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='account.email', read_only=True)
    phone = serializers.CharField(source='account.phone', read_only=True)
    account_status = serializers.CharField(source='account.status', read_only=True)
    email_verified = serializers.BooleanField(source='account.email_verified', read_only=True)
    phone_verified = serializers.BooleanField(source='account.phone_verified', read_only=True)

    class Meta:
        model = Users
        fields = [
            'id', 'full_name', 'gender', 'birth_date', 'avatar_url',
            'address', 'latitude', 'longitude', 'bio', 'role', 'is_online',
            'email', 'phone', 'account_status', 'email_verified', 'phone_verified',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'role', 'is_online', 'created_at', 'updated_at']


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['full_name', 'gender', 'birth_date', 'address', 'latitude', 'longitude', 'bio']
        extra_kwargs = {'full_name': {'required': False}}

    def validate_birth_date(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Ngày sinh không hợp lệ.")
        return value


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField(required=True)

    def validate_avatar(self, value):
        max_size = 5 * 1024 * 1024  # 5MB
        if value.size > max_size:
            raise serializers.ValidationError("Kích thước ảnh tối đa 5MB.")
        if value.content_type not in ('image/jpeg', 'image/png', 'image/webp'):
            raise serializers.ValidationError("Chỉ hỗ trợ JPEG, PNG, WebP.")
        return value


class UserListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='account.email', read_only=True)
    phone = serializers.CharField(source='account.phone', read_only=True)
    account_status = serializers.CharField(source='account.status', read_only=True)

    class Meta:
        model = Users
        fields = ['id', 'full_name', 'avatar_url', 'role', 'is_online',
                  'email', 'phone', 'account_status', 'created_at']


class UserDetailSerializer(UserProfileSerializer):
    last_login_at = serializers.DateTimeField(source='account.last_login_at', read_only=True)
    login_provider = serializers.CharField(source='account.login_provider', read_only=True)

    class Meta(UserProfileSerializer.Meta):
        fields = UserProfileSerializer.Meta.fields + ['last_login_at', 'login_provider']
    
class StudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    avatar_url = serializers.CharField(source='user.avatar_url', read_only=True)

    class Meta:
        model = StudentProfiles
        fields = ['id', 'full_name', 'avatar_url', 'grade', 'parent_name',
                  'parent_phone', 'learning_goal', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UpdateStudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfiles
        fields = ['grade', 'parent_name', 'parent_phone', 'learning_goal']

    def validate_parent_phone(self, value):
        if value and not value.replace('+', '').isdigit():
            raise serializers.ValidationError("Số điện thoại không hợp lệ.")
        return value


# ---------- Tutor ----------

class TutorProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    avatar_url = serializers.CharField(source='user.avatar_url', read_only=True)
    bio = serializers.CharField(source='user.bio', read_only=True)
    address = serializers.CharField(source='user.address', read_only=True)
    # TODO: thêm `subjects` ở đây khi có model Subjects/TutorSubjects chính thức

    class Meta:
        model = TutorProfiles
        fields = [
            'id', 'full_name', 'avatar_url', 'bio', 'address',
            'experience_years', 'teaching_fee', 'rating_avg', 'total_reviews',
            'response_rate', 'trusted_badge', 'education_level', 'university',
            'major', 'is_kyc_verified', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'rating_avg', 'total_reviews', 'response_rate',
            'trusted_badge', 'is_kyc_verified', 'created_at', 'updated_at',
        ]


class UpdateTutorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorProfiles
        fields = ['experience_years', 'teaching_fee', 'education_level', 'university', 'major']
        # rating_avg, total_reviews, response_rate, trusted_badge, is_kyc_verified:
        # đây là field hệ thống tự cập nhật (qua review/KYC flow), không cho user tự sửa.

    def validate_teaching_fee(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Học phí không thể âm.")
        return value


class TutorListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    avatar_url = serializers.CharField(source='user.avatar_url', read_only=True)
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfiles
        fields = [
            'id', 'full_name', 'avatar_url', 'experience_years', 'teaching_fee',
            'rating_avg', 'total_reviews', 'trusted_badge', 'is_kyc_verified', 'distance_km',
        ]

    def get_distance_km(self, obj):
        val = getattr(obj, 'distance_km', None)
        return round(val, 2) if val is not None else None


class TutorPublicProfileSerializer(TutorProfileSerializer):
    pass  # public profile dùng chung field set; ẩn thêm field nếu sau này có dữ liệu nhạy cảm

class KYCDocumentInputSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=sorted(REQUIRED_DOCUMENT_TYPES))
    file_url = serializers.URLField()


class SubmitKYCSerializer(serializers.Serializer):
    documents = KYCDocumentInputSerializer(many=True)

    def validate_documents(self, value):
        types = [doc['document_type'] for doc in value]
        if len(types) != len(set(types)):
            raise serializers.ValidationError("Không thể nộp trùng loại giấy tờ trong 1 lần gửi.")
        return value


class KYCDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KycDocuments
        fields = ['id', 'document_type', 'file_url', 'status', 'admin_note',
                  'created_at', 'updated_at']
        read_only_fields = fields


class KYCDocumentAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.EmailField(source='user.account.email', read_only=True)

    class Meta:
        model = KycDocuments
        fields = ['id', 'user', 'full_name', 'email', 'document_type', 'file_url',
                  'status', 'admin_note', 'created_at', 'updated_at']
        read_only_fields = fields


class RejectKYCSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=True, allow_blank=False, max_length=1000)
    
    
class SystemLogSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = SystemLogs
        fields = [
            'id', 'user', 'user_email', 'user_full_name',
            'action', 'module', 'description', 'ip_address', 'created_at',
        ]

    def get_user_email(self, obj):
        return obj.user.account.email if obj.user_id else None

    def get_user_full_name(self, obj):
        return obj.user.full_name if obj.user_id else None


class AdminDashboardSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_tutors = serializers.IntegerField()
    total_admins = serializers.IntegerField()
    active_accounts = serializers.IntegerField()
    locked_accounts = serializers.IntegerField()
    pending_kyc = serializers.IntegerField()
    approved_kyc = serializers.IntegerField()
    rejected_kyc = serializers.IntegerField()
    new_users_last_7_days = serializers.IntegerField()
    recent_logs = serializers.SerializerMethodField()

    def get_recent_logs(self, obj):
        return SystemLogSerializer(obj['recent_logs'], many=True).data


class AdminUserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='users.full_name', read_only=True)
    role = serializers.CharField(source='users.role', read_only=True)
    avatar_url = serializers.CharField(source='users.avatar_url', read_only=True)
    is_kyc_verified = serializers.SerializerMethodField()

    class Meta:
        model = Accounts
        fields = [
            'id', 'email', 'phone', 'full_name', 'role', 'avatar_url',
            'status', 'email_verified', 'phone_verified',
            'is_kyc_verified', 'last_login_at', 'created_at',
        ]

    def get_is_kyc_verified(self, obj):
        try:
            return obj.users.tutorprofiles.is_kyc_verified
        except Exception:
            return None


class LockUnlockUserSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)