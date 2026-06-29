from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from ..models import ChatMembers, ChatMessages, ChatRooms, Notifications
from ..serializers import (
    ChatMessageSerializer,
    SendMessageSerializer,
)
from ..utils import get_users_instance, get_membership, BaseChatView


class SendMessageView(BaseChatView):
    def post(self, request):
        users_instance = get_users_instance(request)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        membership = get_membership(data['room_id'], users_instance)
        if not membership:
            return Response({"detail": "You are not a member of this room."}, status=status.HTTP_403_FORBIDDEN)

        message = ChatMessages.objects.create(
            room_id=data['room_id'],
            sender_user=users_instance,
            message_type=data['message_type'],
            content=data.get('content') or '',
            attachment_url=data.get('attachment_url') or None,
        )

        ChatRooms.objects.filter(pk=data['room_id']).update(last_message=message)

        other_member_ids = list(
            ChatMembers.objects.filter(room_id=data['room_id'])
            .exclude(user=users_instance)
            .values_list('user_id', flat=True)
        )
        if other_member_ids:
            preview = (data.get('content') or '').strip() or data['message_type']
            Notifications.objects.bulk_create([
                Notifications(
                    sender_user=users_instance,
                    receiver_user_id=rid,
                    title="New message",
                    content=preview[:255],
                    type="CHAT",
                )
                for rid in other_member_ids
            ])

        return Response(ChatMessageSerializer(message).data, status=status.HTTP_201_CREATED)


class MessageHistoryView(BaseChatView):
    def get(self, request, id):
        users_instance = get_users_instance(request)
        get_object_or_404(ChatRooms, pk=id)

        if not get_membership(id, users_instance):
            return Response({"detail": "You are not a member of this room."}, status=status.HTTP_403_FORBIDDEN)

        messages = ChatMessages.objects.filter(room_id=id, is_deleted=False).order_by('created_at')  # Meta.ordering = created_at
        return Response(ChatMessageSerializer(messages, many=True).data)


class MarkMessageSeenView(BaseChatView):
    def patch(self, request, id):
        users_instance = get_users_instance(request)
        message = get_object_or_404(ChatMessages, pk=id)

        membership = get_membership(message.room_id, users_instance)
        if not membership:
            return Response({"detail": "You are not a member of this room."}, status=status.HTTP_403_FORBIDDEN)

        # Source of truth for "seen" in any room (1:1 or group)
        if not membership.last_seen_message_id or membership.last_seen_message.created_at < message.created_at:
            membership.last_seen_message = message
            membership.save(update_fields=['last_seen_message'])

        # Legacy flag — only unambiguous in a 1:1 room
        if message.sender_user_id != users_instance.id and not message.is_seen:
            message.is_seen = True
            message.save(update_fields=['is_seen'])

        return Response(ChatMessageSerializer(message).data)


class DeleteMessageView(BaseChatView):
    def delete(self, request, id):
        users_instance = get_users_instance(request)
        message = get_object_or_404(ChatMessages, pk=id)

        if message.sender_user_id != users_instance.id:
            return Response(
                {"detail": "You can only delete your own messages."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if message.is_deleted:
            return Response(
                {"detail": "Message is already deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        message.is_deleted = True
        message.save(update_fields=['is_deleted'])
        return Response(status=status.HTTP_204_NO_CONTENT)