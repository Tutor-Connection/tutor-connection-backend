from django.db import models

# Create your models here.
class ChatMembers(models.Model):

    ROLE = (
        ("MEMBER", "Member"),
        ("ADMIN", "Admin"),
    )

    id = models.BigAutoField(primary_key=True)

    room = models.ForeignKey(
        'ChatRooms',
        on_delete=models.CASCADE,
        related_name="members"
    )

    user = models.ForeignKey(
        "accounts.Users",
        on_delete=models.CASCADE,
        related_name="chat_rooms"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE,
        default="MEMBER"
    )

    last_seen_message = models.ForeignKey(
        "ChatMessages",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+"
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_members"

        constraints = [
            models.UniqueConstraint(
                fields=["room", "user"],
                name="unique_room_member"
            )
        ]

class ChatMessages(models.Model):

    MESSAGE_TYPE = (
        ("TEXT", "Text"),
        ("IMAGE", "Image"),
        ("FILE", "File"),
        ("VOICE", "Voice"),
        ("VIDEO", "Video"),
    )

    id = models.BigAutoField(primary_key=True)

    room = models.ForeignKey(
        'ChatRooms',
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender_user = models.ForeignKey(
        "accounts.Users",
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )

    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE,
        default="TEXT"
    )

    content = models.TextField(
        blank=True
    )

    attachment_url = models.TextField(
        blank=True,
        null=True
    )

    is_seen = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    edited_at = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_messages"

        ordering = ["created_at"]


class ChatRooms(models.Model):
    ROOM_TYPE = (
        ("PRIVATE", "Private"),
        ("GROUP", "Group"),
    )

    id = models.BigAutoField(primary_key=True)

    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPE,
        default="PRIVATE"
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    avatar_url = models.TextField(
        blank=True,
        null=True
    )

    created_by = models.ForeignKey(
        "accounts.Users",
        on_delete=models.CASCADE,
        related_name="created_rooms"
    )

    last_message = models.ForeignKey(
        "ChatMessages",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_rooms"

    def __str__(self):
        return f"Room {self.id}"


class Notifications(models.Model):

    TYPE = (
        ("CHAT", "Chat"),
        ("BOOKING", "Booking"),
        ("PAYMENT", "Payment"),
        ("SYSTEM", "System"),
    )

    id = models.BigAutoField(primary_key=True)

    sender_user = models.ForeignKey(
        "accounts.Users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications"
    )

    receiver_user = models.ForeignKey(
        "accounts.Users",
        on_delete=models.CASCADE,
        related_name="received_notifications"
    )

    title = models.CharField(max_length=255)

    content = models.TextField()

    type = models.CharField(
        max_length=20,
        choices=TYPE
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"

        ordering = ["-created_at"]
