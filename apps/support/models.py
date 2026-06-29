from django.db import models

# Create your models here.

class SupportTickets(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('accounts.Users', models.DO_NOTHING)
    title = models.CharField(max_length=255)
    description = models.TextField()
    ticket_type = models.CharField(max_length=50, blank=True, null=True, db_column='type')
    attachment_url = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    assigned_to = models.ForeignKey('accounts.Users', models.DO_NOTHING, blank=True, null=True, related_name='assigned_tickets')
    rating = models.IntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'support_tickets'


class TicketMessages(models.Model):
    id = models.BigAutoField(primary_key=True)
    ticket = models.ForeignKey(SupportTickets, models.DO_NOTHING, related_name='messages')
    sender = models.ForeignKey('accounts.Users', models.DO_NOTHING)
    message = models.TextField()
    attachment_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ticket_messages'