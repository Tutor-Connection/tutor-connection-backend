from rest_framework import serializers
from .models import SupportTickets, TicketMessages
from apps.tutoring.models import ReviewReports

class TicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketMessages
        fields = '__all__'
        read_only_fields = ['id', 'ticket', 'sender', 'created_at']

class SupportTicketSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTickets
        fields = '__all__'
        read_only_fields = ['id', 'user', 'status', 'resolved_at', 'assigned_to', 'created_at', 'updated_at', 'messages']

class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTickets
        fields = ['title', 'description', 'ticket_type', 'attachment_url']

class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTickets
        fields = ['title', 'description', 'ticket_type']

class ReviewReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewReports
        fields = '__all__'
        read_only_fields = ['id', 'reporter', 'status', 'admin_note', 'action_taken', 'resolved_at', 'created_at']

class ReviewReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewReports
        fields = ['review', 'reason']
