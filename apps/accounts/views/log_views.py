from apps.accounts.views.admin_views import AdminPagination

from rest_framework import generics

from ..authentication import JWTAccountAuthentication
from ..models import SystemLogs
from ..permissions import IsAdminRole
from ..serializers import (
    SystemLogSerializer,
)

class SystemLogListView(generics.ListAPIView):
    authentication_classes = [JWTAccountAuthentication]
    permission_classes = [IsAdminRole]
    serializer_class = SystemLogSerializer
    pagination_class = AdminPagination

    def get_queryset(self):
        qs = SystemLogs.objects.select_related('user', 'user__account').order_by('-created_at')

        user_id = self.request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)

        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(module=module)

        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action__icontains=action)

        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        return qs


class SystemLogDetailView(generics.RetrieveAPIView):
    authentication_classes = [JWTAccountAuthentication]
    permission_classes = [IsAdminRole]
    serializer_class = SystemLogSerializer
    queryset = SystemLogs.objects.select_related('user', 'user__account')
    lookup_field = 'id'
