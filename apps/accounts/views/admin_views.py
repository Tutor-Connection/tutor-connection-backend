from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from ..authentication import JWTAccountAuthentication
from ..models import Accounts, KycDocuments, StudentProfiles, SystemLogs, TutorProfiles, Users
from ..permissions import IsAdminRole
from ..serializers import (
    AdminDashboardSerializer,
    AdminUserListSerializer,
    LockUnlockUserSerializer
)


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class AdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ---------- 6. Admin ----------

class AdminDashboardView(APIView):
    authentication_classes = [JWTAccountAuthentication]
    permission_classes = [IsAdminRole]

    def get(self, request):
        seven_days_ago = timezone.now() - timedelta(days=7)

        data = {
            'total_users': Users.objects.count(),
            'total_students': StudentProfiles.objects.count(),
            'total_tutors': TutorProfiles.objects.count(),
            'total_admins': Users.objects.filter(role='ADMIN').count(),
            'active_accounts': Accounts.objects.filter(status='ACTIVE').count(),
            'locked_accounts': Accounts.objects.filter(status='BANNED').count(),
            'pending_kyc': KycDocuments.objects.filter(status='PENDING').count(),
            'approved_kyc': KycDocuments.objects.filter(status='APPROVED').count(),
            'rejected_kyc': KycDocuments.objects.filter(status='REJECTED').count(),
            'new_users_last_7_days': Accounts.objects.filter(created_at__gte=seven_days_ago).count(),
            'recent_logs': SystemLogs.objects
                .select_related('user', 'user__account')
                .order_by('-created_at')[:10],
        }
        serializer = AdminDashboardSerializer(data)
        return Response(serializer.data)


class AdminUserListView(generics.ListAPIView):
    authentication_classes = [JWTAccountAuthentication]
    permission_classes = [IsAdminRole]
    serializer_class = AdminUserListSerializer
    pagination_class = AdminPagination

    def get_queryset(self):
        qs = Accounts.objects.select_related('users').order_by('-created_at')

        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(users__role=role)

        acc_status = self.request.query_params.get('status')
        if acc_status:
            qs = qs.filter(status=acc_status)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(users__full_name__icontains=search)
            )

        return qs.distinct()


class LockUserView(APIView):
    authentication_classes = [JWTAccountAuthentication]
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        serializer = LockUnlockUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = Accounts.objects.get(id=id)
        except Accounts.DoesNotExist:
            return Response({'detail': 'Không tìm thấy người dùng.'}, status=status.HTTP_404_NOT_FOUND)

        if account.id == request.user.id:
            return Response(
                {'detail': 'Không thể tự khóa tài khoản của chính mình.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if account.status == 'BANNED':
            return Response({'detail': 'Tài khoản đã bị khóa trước đó.'}, status=status.HTTP_400_BAD_REQUEST)

        account.status = 'BANNED'
        account.updated_at = timezone.now()
        account.save(update_fields=['status', 'updated_at'])

        SystemLogs.objects.create(
            user=getattr(request.user, 'users', None),
            action='LOCK_USER',
            module='admin',
            description=f"Locked account #{account.id} ({account.email}). "
                         f"Reason: {serializer.validated_data.get('reason', '')}",
            ip_address=_get_client_ip(request),
            created_at=timezone.now(),
        )

        return Response({'detail': 'Đã khóa tài khoản thành công.'})


class UnlockUserView(APIView):
    authentication_classes = [JWTAccountAuthentication]
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        serializer = LockUnlockUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = Accounts.objects.get(id=id)
        except Accounts.DoesNotExist:
            return Response({'detail': 'Không tìm thấy người dùng.'}, status=status.HTTP_404_NOT_FOUND)

        if account.status != 'BANNED':
            return Response({'detail': 'Tài khoản hiện không bị khóa.'}, status=status.HTTP_400_BAD_REQUEST)

        account.status = 'ACTIVE'
        account.updated_at = timezone.now()
        account.save(update_fields=['status', 'updated_at'])

        SystemLogs.objects.create(
            user=getattr(request.user, 'users', None),
            action='UNLOCK_USER',
            module='admin',
            description=f"Unlocked account #{account.id} ({account.email}). "
                         f"Reason: {serializer.validated_data.get('reason', '')}",
            ip_address=_get_client_ip(request),
            created_at=timezone.now(),
        )

        return Response({'detail': 'Đã mở khóa tài khoản thành công.'})