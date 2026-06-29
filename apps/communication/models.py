from django.db import models

# Create your models here.
class ChatMembers(models.Model):
    pk = models.CompositePrimaryKey('room_id', 'user_id')
    room = models.ForeignKey('ChatRooms', models.DO_NOTHING)
    user = models.ForeignKey('accounts.Users', models.DO_NOTHING)
    joined_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'chat_members'


class ChatMessages(models.Model):
    id = models.BigAutoField(primary_key=True)
    room = models.ForeignKey('ChatRooms', models.DO_NOTHING)
    sender_user = models.ForeignKey('accounts.Users', models.DO_NOTHING)
    message_type = models.CharField(max_length=20, blank=True, null=True)
    content = models.TextField()
    is_seen = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'chat_messages'


class ChatRooms(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'chat_rooms'


class Notifications(models.Model):
    id = models.BigAutoField(primary_key=True)
    sender_user = models.ForeignKey('accounts.Users', models.DO_NOTHING, blank=True, null=True)
    receiver_user = models.ForeignKey('accounts.Users', models.DO_NOTHING, related_name='notifications_receiver_user_set')
    title = models.CharField(max_length=255)
    content = models.TextField()
    type = models.CharField(max_length=20)
    is_read = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notifications'
