from django.db.models import F, FloatField, ExpressionWrapper
from django.db.models.functions import Sqrt, Power
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import TutorProfiles, Users
from ..serializers import (
    TutorProfileSerializer, UpdateTutorProfileSerializer,
    TutorListSerializer, TutorPublicProfileSerializer,
)

def get_users_record(account):
    """request.user là Accounts; lấy bản ghi Users tương ứng (1-1)."""
    try:
        return account.users
    except Users.DoesNotExist:
        return None


# ---------- Tutor ----------

class TutorProfileView(APIView):
    """
    GET   /api/accounts/tutors/me/
    PUT   /api/accounts/tutors/me/
    PATCH /api/accounts/tutors/me/
    (UpdateTutorProfileView gộp chung class này vì cùng path /me/)
    """
    permission_classes = [IsAuthenticated]

    def _get_profile(self, request):
        user = get_users_record(request.user)
        if user is None:
            return None
        try:
            return user.tutorprofiles
        except TutorProfiles.DoesNotExist:
            return None

    def get(self, request):
        profile = self._get_profile(request)
        if profile is None:
            return Response({"detail": "Bạn chưa có hồ sơ gia sư."}, status=status.HTTP_404_NOT_FOUND)
        return Response(TutorProfileSerializer(profile).data)

    def put(self, request):
        return self._update(request, partial=False)

    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, partial):
        profile = self._get_profile(request)
        if profile is None:
            return Response({"detail": "Bạn chưa có hồ sơ gia sư."}, status=status.HTTP_404_NOT_FOUND)
        serializer = UpdateTutorProfileSerializer(profile, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TutorProfileSerializer(profile).data)


UpdateTutorProfileView = TutorProfileView


class TutorPublicProfileView(generics.RetrieveAPIView):
    """GET /api/accounts/tutors/{id}/  (public, không cần auth)"""
    queryset = TutorProfiles.objects.select_related('user', 'user__account').filter(
        user__deleted_at__isnull=True,
        user__account__status='ACTIVE',
        user__account__deleted_at__isnull=True,
    )
    serializer_class = TutorPublicProfileSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'


class TutorListView(generics.ListAPIView):
    """
    GET /api/accounts/tutors/   (public)
    Query params: subject, rating (min), fee_min, fee_max, lat, lng, distance (km), ordering
    """
    serializer_class = TutorListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = TutorProfiles.objects.select_related('user', 'user__account').filter(
            user__deleted_at__isnull=True,
            user__account__status='ACTIVE',
            user__account__deleted_at__isnull=True,
        )

        params = self.request.query_params

        # --- subject filter ---
        # TODO: cần xác nhận schema thật cho subject. Tạm giả định bảng trung gian
        # TutorSubjects(tutor -> TutorProfiles, subject -> Subjects) tồn tại:
        subject = params.get('subject')
        if subject:
            qs = qs.filter(tutorsubjects__subject_id=subject).distinct()
            # Nếu schema khác (ví dụ subject là CharField đơn trên TutorProfiles),
            # đổi thành: qs = qs.filter(subject__iexact=subject)

        # --- rating filter ---
        min_rating = params.get('rating')
        if min_rating:
            qs = qs.filter(rating_avg__gte=float(min_rating))

        # --- fee filter ---
        fee_min = params.get('fee_min')
        fee_max = params.get('fee_max')
        if fee_min:
            qs = qs.filter(teaching_fee__gte=float(fee_min))
        if fee_max:
            qs = qs.filter(teaching_fee__lte=float(fee_max))

        # --- distance filter ---
        lat = params.get('lat')
        lng = params.get('lng')
        max_distance = params.get('distance')  # km
        if lat and lng:
            lat, lng = float(lat), float(lng)
            # Euclidean approx (đủ dùng cho phạm vi 1 tỉnh/thành).
            # Nếu cần chính xác toàn cầu, dùng Haversine hoặc PostGIS.
            qs = qs.annotate(
                distance_km=ExpressionWrapper(
                    Sqrt(
                        Power((F('user__latitude') - lat) * 111.0, 2)
                        + Power((F('user__longitude') - lng) * 111.0, 2)
                    ),
                    output_field=FloatField(),
                )
            )
            if max_distance:
                qs = qs.filter(distance_km__lte=float(max_distance))

        # --- ordering ---
        ordering = params.get('ordering')
        allowed_orderings = {
            'rating_avg', '-rating_avg',
            'teaching_fee', '-teaching_fee',
            'distance_km', '-distance_km',
            'experience_years', '-experience_years',
        }
        if ordering in allowed_orderings:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-rating_avg', '-total_reviews')

        return qs