from django.db import transaction
from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import KycDocuments, TutorProfiles, Users
from ..permissions import IsAdminRole
from ..serializers import (
    SubmitKYCSerializer, KYCDocumentSerializer, KYCDocumentAdminSerializer,
    RejectKYCSerializer, REQUIRED_DOCUMENT_TYPES,
)


def get_users_record(account):
    try:
        return account.users
    except Users.DoesNotExist:
        return None


def maybe_mark_tutor_verified(user):
    """Nếu user là tutor và đủ bộ document bắt buộc đều approved -> set is_kyc_verified=True."""
    try:
        tutor = user.tutorprofiles
    except TutorProfiles.DoesNotExist:
        return

    approved_types = set(
        KycDocuments.objects.filter(user=user, status='APPROVED')
        .values_list('document_type', flat=True)
    )
    if REQUIRED_DOCUMENT_TYPES.issubset(approved_types):
        tutor.is_kyc_verified = True
        tutor.save(update_fields=['is_kyc_verified', 'updated_at'])


class SubmitKYCView(APIView):
    """POST /api/accounts/kyc/submit/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = get_users_record(request.user)
        if user is None:
            return Response({"detail": "Không tìm thấy hồ sơ người dùng."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubmitKYCSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        documents = serializer.validated_data['documents']

        requested_types = {doc['document_type'] for doc in documents}
        pending_existing = KycDocuments.objects.filter(
            user=user, document_type__in=requested_types, status='PENDING'
        )
        if pending_existing.exists():
            blocked = list(pending_existing.values_list('document_type', flat=True))
            return Response(
                {"detail": f"Các loại giấy tờ sau đang chờ duyệt, không thể nộp lại: {blocked}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        with transaction.atomic():
            for doc in documents:
                obj = KycDocuments.objects.create(
                    user=user,
                    document_type=doc['document_type'],
                    file_url=doc['file_url'],
                    status='PENDING',
                )
                created.append(obj)

        return Response(KYCDocumentSerializer(created, many=True).data, status=status.HTTP_201_CREATED)


class MyKYCView(APIView):
    """GET /api/accounts/kyc/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_users_record(request.user)
        if user is None:
            return Response({"detail": "Không tìm thấy hồ sơ người dùng."}, status=status.HTTP_404_NOT_FOUND)

        docs = KycDocuments.objects.filter(user=user).order_by('-created_at')
        if not docs.exists():
            return Response({"detail": "Bạn chưa nộp hồ sơ KYC."}, status=status.HTTP_404_NOT_FOUND)

        statuses = set(docs.values_list('status', flat=True))
        if 'PENDING' in statuses:
            overall_status = 'PENDING'
        elif statuses == {'APPROVED'}:
            overall_status = 'APPROVED'
        elif 'REJECTED' in statuses:
            overall_status = 'REJECTED'
        else:
            overall_status = 'PENDING'

        return Response({
            "overall_status": overall_status,
            "documents": KYCDocumentSerializer(docs, many=True).data,
        })


class KYCListView(generics.ListAPIView):
    """
    GET /api/accounts/admin/kyc/   (Admin)
    Query params: status (pending/approved/rejected), document_type
    """
    serializer_class = KYCDocumentAdminSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = KycDocuments.objects.select_related('user', 'user__account')
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        doc_type = self.request.query_params.get('document_type')
        if doc_type:
            qs = qs.filter(document_type=doc_type)
        return qs


class ApproveKYCView(APIView):
    """POST /api/accounts/admin/kyc/{id}/approve/  (Admin) — id = KycDocuments.id"""
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, id):
        try:
            print("Fetching KYC document with ID:", id)
            doc = KycDocuments.objects.select_related('user').get(id=id)
        except KycDocuments.DoesNotExist:
            return Response({"detail": "Không tìm thấy document."}, status=status.HTTP_404_NOT_FOUND)

        if doc.status == 'APPROVED':
            return Response({"detail": "Document này đã được duyệt."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            doc.status = 'APPROVED'
            doc.admin_note = None
            doc.save(update_fields=['status', 'admin_note', 'updated_at'])
            maybe_mark_tutor_verified(doc.user)

        return Response(KYCDocumentSerializer(doc).data, status=status.HTTP_200_OK)


class RejectKYCView(APIView):
    """POST /api/accounts/admin/kyc/{id}/reject/  (Admin) — id = KycDocuments.id"""
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, id):
        try:
            doc = KycDocuments.objects.get(id=id)
        except KycDocuments.DoesNotExist:
            return Response({"detail": "Không tìm thấy document."}, status=status.HTTP_404_NOT_FOUND)

        if doc.status == 'APPROVED':
            return Response(
                {"detail": "Document đã được duyệt, không thể từ chối."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RejectKYCSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc.status = 'REJECTED'
        doc.admin_note = serializer.validated_data['admin_note']
        doc.save(update_fields=['status', 'admin_note', 'updated_at'])

        return Response(KYCDocumentSerializer(doc).data, status=status.HTTP_200_OK)