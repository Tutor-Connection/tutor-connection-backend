import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Q
from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Users
from ..permissions import IsAdminRole
from ..serializers import (
    UserProfileSerializer,
    UpdateProfileSerializer,
    AvatarUploadSerializer,
    UserListSerializer,
    UserDetailSerializer,
)


class CurrentUserView(APIView):
    """
    GET  /api/accounts/users/me/  -> xem profile
    PUT  /api/accounts/users/me/  -> cập nhật profile (UpdateProfileView gộp ở đây)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.users
        return Response(UserProfileSerializer(profile).data)

    def put(self, request):
        profile = request.user.users
        partial = request.method == 'PATCH'
        serializer = UpdateProfileSerializer(profile, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(profile).data, status=status.HTTP_200_OK)

    # cho phép PATCH dùng chung logic với PUT nếu cần partial update
    def patch(self, request):
        return self.put(request)


class UploadAvatarView(APIView):
    """POST /api/accounts/users/avatar/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        avatar_file = serializer.validated_data['avatar']

        profile = request.user.users

        # Xoá avatar cũ nếu đang lưu trong storage nội bộ
        if profile.avatar_url:
            old_path = profile.avatar_url.replace(settings.MEDIA_URL, '')
            if default_storage.exists(old_path):
                default_storage.delete(old_path)

        ext = os.path.splitext(avatar_file.name)[1]
        filename = f"avatars/{profile.account_id}_{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(filename, avatar_file)
        avatar_url = default_storage.url(saved_path)

        profile.avatar_url = avatar_url
        profile.save(update_fields=['avatar_url', 'updated_at'])

        return Response({"avatar_url": avatar_url}, status=status.HTTP_200_OK)


class UserListView(generics.ListAPIView):
    """
    GET /api/accounts/users/   (Admin)
    Query params: search, role, is_online
    """
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'full_name']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Users.objects.select_related('account').filter(deleted_at__isnull=True)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search)
                | Q(account__email__icontains=search)
                | Q(account__phone__icontains=search)
            )

        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)

        is_online = self.request.query_params.get('is_online')
        if is_online is not None:
            qs = qs.filter(is_online=is_online.lower() == 'true')

        return qs


class UserDetailView(generics.RetrieveAPIView):
    """GET /api/accounts/users/{id}/  (Admin)"""
    queryset = Users.objects.select_related('account').filter(deleted_at__isnull=True)
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    lookup_field = 'id'