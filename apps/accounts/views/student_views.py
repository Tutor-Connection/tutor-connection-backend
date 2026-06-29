from django.db.models import F, FloatField, ExpressionWrapper
from django.db.models.functions import Sqrt, Power
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import StudentProfiles, TutorProfiles, Users
from ..serializers import (
    StudentProfileSerializer, UpdateStudentProfileSerializer,
    TutorProfileSerializer, UpdateTutorProfileSerializer,
    TutorListSerializer, TutorPublicProfileSerializer,
)


def get_users_record(account):
    """request.user là Accounts; lấy bản ghi Users tương ứng (1-1)."""
    try:
        return account.users
    except Users.DoesNotExist:
        return None


# ---------- Student ----------

class StudentProfileView(APIView):
    """
    GET   /api/accounts/students/me/
    PUT   /api/accounts/students/me/
    PATCH /api/accounts/students/me/
    (UpdateStudentProfileView gộp chung class này vì cùng path /me/)
    """
    permission_classes = [IsAuthenticated]

    def _get_profile(self, request):
        user = get_users_record(request.user)
        if user is None:
            return None
        try:
            return user.studentprofiles
        except StudentProfiles.DoesNotExist:
            return None

    def get(self, request):
        profile = self._get_profile(request)
        if profile is None:
            return Response({"detail": "Bạn chưa có hồ sơ học viên."}, status=status.HTTP_404_NOT_FOUND)
        return Response(StudentProfileSerializer(profile).data)

    def put(self, request):
        return self._update(request, partial=False)

    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, partial):
        profile = self._get_profile(request)
        if profile is None:
            return Response({"detail": "Bạn chưa có hồ sơ học viên."}, status=status.HTTP_404_NOT_FOUND)
        serializer = UpdateStudentProfileSerializer(profile, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StudentProfileSerializer(profile).data)


# alias để giữ tên view như spec ban đầu, cùng trỏ về 1 class (cùng path /me/)
UpdateStudentProfileView = StudentProfileView

