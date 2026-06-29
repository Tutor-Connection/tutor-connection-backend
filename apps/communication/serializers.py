from django.db import IntegrityError
from rest_framework import serializers

from .models import ChatMembers, ChatMessages, ChatRooms, Notifications
from apps.accounts.models import Users


# ---------- Chat Rooms ----------

class ChatMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField( read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatMembers
        fields = ['id', 'user_id', 'full_name', 'role', 'last_seen_message', 'joined_at']
        read_only_fields = ['id', 'joined_at']

    def get_full_name(self, obj):
        return getattr(obj.user, 'full_name', str(obj.user_id))


class ChatRoomSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = ChatRooms
        fields = [
            'id', 'room_type', 'name', 'avatar_url', 'created_by',
            'display_name', 'member_count', 'last_message_preview',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.members.count()

    def get_display_name(self, obj):
        if obj.room_type == 'GROUP':
            return obj.name
        # PRIVATE room: surface the other participant's name instead of a blank room name
        request = self.context.get('request')
        if not request:
            return obj.name
        current_users_id = request.user.users.id
        other = obj.members.exclude(user_id=current_users_id).select_related('user').first()
        if other:
            return getattr(other.user, 'full_name', f"User {other.user_id}")
        return obj.name

    def get_last_message_preview(self, obj):
        if obj.last_message_id and not obj.last_message.is_deleted:
            return {
                'id': obj.last_message_id,
                'content': obj.last_message.content[:120],
                'message_type': obj.last_message.message_type,
                'created_at': obj.last_message.created_at,
            }
        return None


class CreateChatRoomSerializer(serializers.Serializer):
    room_type = serializers.ChoiceField(choices=['PRIVATE', 'GROUP'], default='PRIVATE')
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    avatar_url = serializers.CharField(required=False, allow_blank=True)
    member_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    def validate(self, attrs):
        room_type = attrs.get('room_type', 'PRIVATE')
        member_ids = attrs.get('member_ids', [])

        if room_type == 'GROUP' and not attrs.get('name'):
            raise serializers.ValidationError({"name": "Group rooms require a name."})

        if room_type == 'PRIVATE' and len(member_ids) != 1:
            raise serializers.ValidationError(
                {"member_ids": "A private room must include exactly one other member."}
            )

        for uid in member_ids:
            if not Users.objects.filter(pk=uid).exists():
                raise serializers.ValidationError({"member_ids": f"User {uid} does not exist."})

        return attrs


class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=['MEMBER', 'ADMIN'], default='MEMBER')

    def validate_user_id(self, value):
        if not Users.objects.filter(pk=value).exists():
            raise serializers.ValidationError("User does not exist.")
        return value


# ---------- Messages ----------

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender_user_id', read_only=True)

    class Meta:
        model = ChatMessages
        fields = [
            'id', 'room', 'sender_id', 'message_type', 'content',
            'attachment_url', 'is_seen', 'is_deleted', 'edited_at', 'created_at',
        ]
        read_only_fields = ['id', 'sender_id', 'is_seen', 'edited_at', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data['content'] = "This message was deleted."
            data['attachment_url'] = None
        return data


class SendMessageSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    message_type = serializers.ChoiceField(
        choices=['TEXT', 'IMAGE', 'FILE', 'VOICE', 'VIDEO'], default='TEXT'
    )
    content = serializers.CharField(required=False, allow_blank=True, default='')
    attachment_url = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)

    def validate(self, attrs):
        if not ChatRooms.objects.filter(pk=attrs['room_id']).exists():
            raise serializers.ValidationError({"room_id": "Chat room does not exist."})
        if attrs['message_type'] != 'TEXT' and not attrs.get('attachment_url'):
            raise serializers.ValidationError(
                {"attachment_url": "attachment_url is required for non-text messages."}
            )
        if attrs['message_type'] == 'TEXT' and not attrs.get('content'):
            raise serializers.ValidationError({"content": "content is required for text messages."})
        return attrs


# ---------- Notifications ----------

class NotificationSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender_user_id', read_only=True)

    class Meta:
        model = Notifications
        fields = ['id', 'sender_id', 'title', 'content', 'type', 'is_read', 'created_at']
        read_only_fields = fields