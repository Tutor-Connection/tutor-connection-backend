from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from ..models import ChatMembers, ChatRooms
from ..serializers import (
    AddMemberSerializer,
    ChatMemberSerializer,
)
from ..utils import get_users_instance, get_membership, BaseChatView, notify

class ChatRoomMembersView(BaseChatView):
    """
    GET  -> MemberListView
    POST -> AddMemberView
    Combined: both live at /api/chat/rooms/{id}/members/.
    """

    def get(self, request, id):
        users_instance = get_users_instance(request)
        get_object_or_404(ChatRooms, pk=id)

        if not get_membership(id, users_instance):
            return Response({"detail": "You are not a member of this room."}, status=status.HTTP_403_FORBIDDEN)

        members = ChatMembers.objects.filter(room_id=id).select_related('user')
        return Response(ChatMemberSerializer(members, many=True).data)

    def post(self, request, id):
        users_instance = get_users_instance(request)
        room = get_object_or_404(ChatRooms, pk=id)

        membership = get_membership(id, users_instance)
        if not membership:
            return Response({"detail": "You are not a member of this room."}, status=status.HTTP_403_FORBIDDEN)

        if room.room_type == 'PRIVATE':
            return Response(
                {"detail": "Cannot add members to a private (1:1) room."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if membership.role != 'ADMIN':
            return Response({"detail": "Only admins can add members."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_user_id = serializer.validated_data['user_id']
        role = serializer.validated_data['role']

        try:
            member = ChatMembers.objects.create(room_id=id, user_id=new_user_id, role=role)
        except IntegrityError:
            return Response({"detail": "User is already a member."}, status=status.HTTP_400_BAD_REQUEST)

        notify(
            sender_users_instance=users_instance,
            receiver_user_id=new_user_id,
            title="Added to chat",
            content=f"You were added to '{room.name or 'a chat'}'.",
            type_="CHAT",
        )

        return Response(ChatMemberSerializer(member).data, status=status.HTTP_201_CREATED)


class RemoveMemberView(BaseChatView):
    def delete(self, request, id, user_id):
        users_instance = get_users_instance(request)
        get_object_or_404(ChatRooms, pk=id)

        membership = get_membership(id, users_instance)
        if not membership:
            return Response({"detail": "You are not a member of this room."}, status=status.HTTP_403_FORBIDDEN)

        target = get_object_or_404(ChatMembers, room_id=id, user_id=user_id)

        is_self_removal = target.user_id == users_instance.id
        if not is_self_removal and membership.role != 'ADMIN':
            return Response({"detail": "Only admins can remove other members."}, status=status.HTTP_403_FORBIDDEN)

        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
