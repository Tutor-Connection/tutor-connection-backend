from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from ..models import ChatMembers, ChatRooms
from ..serializers import (
    ChatRoomSerializer,
    CreateChatRoomSerializer,
)

from ..utils import get_users_instance, get_membership, BaseChatView

# ---------- Chat Rooms ----------

class ChatRoomListCreateView(BaseChatView):
    """
    GET  -> MyChatRoomsView
    POST -> CreateChatRoomView
    Combined: both live at /api/chat/rooms/.
    """

    def get(self, request):
        users_instance = get_users_instance(request)
        rooms = ChatRooms.objects.filter(members__user=users_instance).order_by('-updated_at')
        return Response(ChatRoomSerializer(rooms, many=True, context={'request': request}).data)

    def post(self, request):
        users_instance = get_users_instance(request)
        serializer = CreateChatRoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data['room_type'] == 'PRIVATE':
            other_id = data['member_ids'][0]
            # Two separate .filter() calls (not one combined filter) so we correctly
            # match "a room where user A is a member AND user B is a member" rather
            # than requiring a single ChatMembers row to satisfy both.
            existing = (
                ChatRooms.objects.filter(room_type='PRIVATE', members__user=users_instance)
                .filter(members__user_id=other_id)
                .first()
            )
            if existing:
                return Response(
                    ChatRoomSerializer(existing, context={'request': request}).data,
                    status=status.HTTP_200_OK,
                )

        room = ChatRooms.objects.create(
            room_type=data['room_type'],
            name=data.get('name') or None,
            avatar_url=data.get('avatar_url') or None,
            created_by=users_instance,
        )
        ChatMembers.objects.create(room=room, user=users_instance, role='ADMIN')

        for uid in data.get('member_ids', []):
            ChatMembers.objects.get_or_create(room=room, user_id=uid, defaults={'role': 'MEMBER'})

        return Response(
            ChatRoomSerializer(room, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class ChatRoomDetailView(BaseChatView):
    def get(self, request, id):
        users_instance = get_users_instance(request)
        room = get_object_or_404(ChatRooms, pk=id)

        if not get_membership(id, users_instance):
            return Response({"detail": "You are not a member of this room."}, status=status.HTTP_403_FORBIDDEN)

        return Response(ChatRoomSerializer(room, context={'request': request}).data)

