from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.authentication import JWTAccountAuthentication
from .models import Notifications, ChatMembers


def notify(sender_users_instance, receiver_user_id, title, content, type_):
    """
    Single-target notification helper (used where there's one recipient,
    e.g. AddMemberView). For fan-out to many recipients (e.g. a new chat
    message to a whole room) use Notifications.objects.bulk_create directly —
    see SendMessageView — to avoid one INSERT per member.
    """
    if sender_users_instance and sender_users_instance.id == receiver_user_id:
        return None
    return Notifications.objects.create(
        sender_user=sender_users_instance,
        receiver_user_id=receiver_user_id,
        title=title,
        content=content,
        type=type_,
    )
    
def get_users_instance(request):
    """Two-hop: Accounts (request.user) -> Users"""
    return request.user.users


def get_membership(room_id, users_instance):
    return ChatMembers.objects.filter(room_id=room_id, user=users_instance).first()


class BaseChatView(APIView):
    authentication_classes = [JWTAccountAuthentication]
    permission_classes = [IsAuthenticated]