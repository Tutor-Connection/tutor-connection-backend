from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from ..models import  Notifications
from ..serializers import (
    NotificationSerializer,
)
from ..utils import get_users_instance, BaseChatView


class NotificationListView(BaseChatView):
    def get(self, request):
        users_instance = get_users_instance(request)
        qs = Notifications.objects.filter(receiver_user=users_instance)

        is_read = request.query_params.get('is_read')
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == 'true')

        notif_type = request.query_params.get('type')
        if notif_type:
            qs = qs.filter(type=notif_type.upper())

        return Response(NotificationSerializer(qs, many=True).data)


class NotificationDetailView(BaseChatView):
    def get(self, request, id):
        users_instance = get_users_instance(request)
        notification = get_object_or_404(Notifications, pk=id, receiver_user=users_instance)

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])

        return Response(NotificationSerializer(notification).data)


class MarkNotificationReadView(BaseChatView):
    def patch(self, request, id):
        users_instance = get_users_instance(request)
        notification = get_object_or_404(Notifications, pk=id, receiver_user=users_instance)

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])

        return Response(NotificationSerializer(notification).data)


class MarkAllNotificationsReadView(BaseChatView):
    def patch(self, request):
        users_instance = get_users_instance(request)
        updated = Notifications.objects.filter(
            receiver_user=users_instance, is_read=False
        ).update(is_read=True)
        return Response({"marked_read": updated})


class UnreadNotificationCountView(BaseChatView):
    def get(self, request):
        users_instance = get_users_instance(request)
        count = Notifications.objects.filter(receiver_user=users_instance, is_read=False).count()
        return Response({"unread_count": count})
