from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Count
from .models import SupportTickets, TicketMessages
from apps.tutoring.models import ReviewReports, Reviews
from apps.accounts.models import Users
from apps.communication.models import Notifications
from .serializers import (
    SupportTicketSerializer, 
    SupportTicketCreateSerializer, 
    SupportTicketUpdateSerializer,
    ReviewReportSerializer,
    ReviewReportCreateSerializer
)

def get_user_profile(user):
    # --- MOCK FOR TESTING ---
    mock_user = Users.objects.first()
    if mock_user: return mock_user
    # ------------------------
    # Depending on auth backend, user might be Accounts or Users or auth.User.
    if isinstance(user, Users):
        return user
    if hasattr(user, 'users'):
        return user.users
    # Fallback to fetching by some ID if standard Django User
    return Users.objects.filter(id=getattr(user, 'id', None)).first()

def is_admin(user_profile):
    if not user_profile:
        return False
    return hasattr(user_profile, 'role') and user_profile.role == 'ADMIN'

class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    API ViewSet quản lý các vé hỗ trợ (Support Tickets).
    - GET /api/support/tickets/ : Lấy danh sách ticket.
    - POST /api/support/tickets/ : Tạo ticket mới.
    - GET /api/support/tickets/{id}/ : Xem chi tiết ticket.
    - PUT /api/support/tickets/{id}/ : Cập nhật thông tin ticket.
    """
    queryset = SupportTickets.objects.all()
    serializer_class = SupportTicketSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_profile = get_user_profile(self.request.user)
        queryset = super().get_queryset()
        
        if not is_admin(user_profile):
            queryset = queryset.filter(user=user_profile)
            
        ticket_status = self.request.query_params.get('status', None)
        ticket_type = self.request.query_params.get('type', None)
        search = self.request.query_params.get('search', None)
        
        if ticket_status:
            queryset = queryset.filter(status=ticket_status)
        if ticket_type:
            queryset = queryset.filter(ticket_type=ticket_type)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
            
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return SupportTicketCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SupportTicketUpdateSerializer
        return SupportTicketSerializer

    def perform_create(self, serializer):
        user_profile = get_user_profile(self.request.user)
        ticket = serializer.save(user=user_profile, status='OPEN')
        
        # Send notification to all admins
        admins = Users.objects.filter(role='ADMIN')
        for admin in admins:
            Notifications.objects.create(
                sender_user=user_profile,
                receiver_user=admin,
                title="New Support Ticket",
                content=f"A new ticket '{ticket.title}' has been created.",
                type="SUPPORT",
                is_read=False,
                created_at=timezone.now()
            )

    def update(self, request, *args, **kwargs):
        user_profile = get_user_profile(request.user)
        if not is_admin(user_profile):
            return Response({"detail": "Only admin can update tickets."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        user_profile = get_user_profile(request.user)
        
        is_owner = ticket.user == user_profile
        
        if not (is_owner or is_admin(user_profile)):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
        message_text = request.data.get('message')
        attachment_url = request.data.get('attachment_url')
        
        if not message_text:
            return Response({"detail": "Message is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        TicketMessages.objects.create(
            ticket=ticket,
            sender=user_profile,
            message=message_text,
            attachment_url=attachment_url
        )
        
        receiver = ticket.user if is_admin(user_profile) else ticket.assigned_to
        
        if is_admin(user_profile):
            ticket.status = 'IN_PROGRESS'
            ticket.save()
            
        if receiver:
            Notifications.objects.create(
                sender_user=user_profile,
                receiver_user=receiver,
                title="New reply on ticket",
                content=f"New reply on ticket '{ticket.title}'",
                type="SUPPORT",
                is_read=False,
                created_at=timezone.now()
            )
            
        return Response({"detail": "Reply added."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        ticket = self.get_object()
        user_profile = get_user_profile(request.user)
        
        if not is_admin(user_profile):
            return Response({"detail": "Only admin can update status."}, status=status.HTTP_403_FORBIDDEN)
            
        new_status = request.data.get('status')
        note = request.data.get('note')
        
        if not new_status:
            return Response({"detail": "Status is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        ticket.status = new_status
        if new_status == 'RESOLVED':
            ticket.resolved_at = timezone.now()
            
        if note:
            # log note or send as message?
            TicketMessages.objects.create(
                ticket=ticket,
                sender=user_profile,
                message=f"Status changed to {new_status}. Note: {note}"
            )
            
        ticket.save()
        
        Notifications.objects.create(
            sender_user=user_profile,
            receiver_user=ticket.user,
            title="Ticket status updated",
            content=f"Your ticket '{ticket.title}' is now {new_status}.",
            type="SUPPORT",
            is_read=False,
            created_at=timezone.now()
        )
        
        return Response({"detail": "Status updated."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        user_profile = get_user_profile(request.user)
        
        if not is_admin(user_profile):
            return Response({"detail": "Only admin can assign tickets."}, status=status.HTTP_403_FORBIDDEN)
            
        assigned_to_id = request.data.get('assigned_to')
        if not assigned_to_id:
            return Response({"detail": "assigned_to is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        admin_user = Users.objects.filter(id=assigned_to_id, role='ADMIN').first()
        if not admin_user:
            return Response({"detail": "Invalid admin user ID."}, status=status.HTTP_400_BAD_REQUEST)
            
        ticket.assigned_to = admin_user
        ticket.status = 'IN_PROGRESS'
        ticket.save()
        
        Notifications.objects.create(
            sender_user=user_profile,
            receiver_user=admin_user,
            title="Ticket assigned",
            content=f"Ticket '{ticket.title}' has been assigned to you.",
            type="SUPPORT",
            is_read=False,
            created_at=timezone.now()
        )
        
        return Response({"detail": "Ticket assigned."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        ticket = self.get_object()
        user_profile = get_user_profile(request.user)
        
        if ticket.user != user_profile:
            return Response({"detail": "Only ticket owner can rate."}, status=status.HTTP_403_FORBIDDEN)
            
        if ticket.status != 'RESOLVED':
            return Response({"detail": "Can only rate when status is RESOLVED."}, status=status.HTTP_400_BAD_REQUEST)
            
        rating = request.data.get('rating')
        feedback = request.data.get('feedback')
        
        if not rating or not (1 <= int(rating) <= 5):
            return Response({"detail": "Valid rating (1-5) is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        ticket.rating = rating
        if feedback:
            ticket.feedback = feedback
        ticket.save()
        
        return Response({"detail": "Rating submitted."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def my_tickets(self, request):
        user_profile = get_user_profile(request.user)
        tickets = SupportTickets.objects.filter(user=user_profile).order_by('-created_at')
        serializer = SupportTicketSerializer(tickets, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        user_profile = get_user_profile(request.user)
        if not is_admin(user_profile):
            return Response({"detail": "Only admin can view stats."}, status=status.HTTP_403_FORBIDDEN)
            
        stats = SupportTickets.objects.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status='OPEN')),
            in_progress=Count('id', filter=Q(status='IN_PROGRESS')),
            resolved=Count('id', filter=Q(status='RESOLVED')),
            closed=Count('id', filter=Q(status='CLOSED'))
        )
        return Response(stats)


class ReviewReportViewSet(viewsets.ModelViewSet):
    """
    API ViewSet quản lý việc báo cáo đánh giá (Review Reports).
    - GET /api/support/reports/ : Lấy danh sách báo cáo (chỉ dành cho ADMIN).
    - POST /api/support/reports/ : Tạo một báo cáo mới.
    - GET /api/support/reports/{id}/ : Xem chi tiết báo cáo.
    """
    queryset = ReviewReports.objects.all()
    serializer_class = ReviewReportSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_profile = get_user_profile(self.request.user)
        queryset = super().get_queryset()
        
        if not is_admin(user_profile):
            queryset = queryset.filter(reporter=user_profile)
            
        report_status = self.request.query_params.get('status', None)
        if report_status:
            queryset = queryset.filter(status=report_status)
            
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewReportCreateSerializer
        return ReviewReportSerializer

    def create(self, request, *args, **kwargs):
        user_profile = get_user_profile(request.user)
        review_id = request.data.get('review_id') or request.data.get('review')
        reason = request.data.get('reason')
        
        if not review_id or not reason:
            return Response({"detail": "review_id and reason are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        if not Reviews.objects.filter(id=review_id).exists():
            return Response({"detail": "Review does not exist."}, status=status.HTTP_404_NOT_FOUND)
            
        if ReviewReports.objects.filter(review_id=review_id, reporter=user_profile).exists():
            return Response({"detail": "You have already reported this review."}, status=status.HTTP_400_BAD_REQUEST)
            
        report = ReviewReports.objects.create(
            review_id=review_id,
            reporter=user_profile,
            reason=reason,
            status='PENDING'
        )
        
        # Send notification to admins
        admins = Users.objects.filter(role='ADMIN')
        for admin in admins:
            Notifications.objects.create(
                sender_user=user_profile,
                receiver_user=admin,
                title="New Review Report",
                content=f"A new report for review #{review_id} has been submitted.",
                type="REPORT",
                is_read=False,
                created_at=timezone.now()
            )
            
        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        report = self.get_object()
        user_profile = get_user_profile(request.user)
        
        if not is_admin(user_profile):
            return Response({"detail": "Only admin can process reports."}, status=status.HTTP_403_FORBIDDEN)
            
        new_status = request.data.get('status')
        admin_note = request.data.get('admin_note')
        action_type = request.data.get('action')
        
        if not new_status or not action_type:
            return Response({"detail": "status and action are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        report.status = new_status
        report.admin_note = admin_note
        report.action_taken = action_type
        
        review = report.review
        
        if new_status == 'RESOLVED' and action_type == 'HIDE_REVIEW':
            review.status = 'HIDDEN'
            review.save()
        elif action_type == 'DELETE_REVIEW':
            review.delete()
            
        if new_status in ['RESOLVED', 'REJECTED']:
            report.resolved_at = timezone.now()
            
        report.save()
        
        Notifications.objects.create(
            sender_user=user_profile,
            receiver_user=report.reporter,
            title="Report Processed",
            content=f"Your report for review #{review.id} has been {new_status}.",
            type="REPORT",
            is_read=False,
            created_at=timezone.now()
        )
        
        return Response({"detail": "Report processed successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        user_profile = get_user_profile(request.user)
        if not is_admin(user_profile):
            return Response({"detail": "Only admin can view pending reports."}, status=status.HTTP_403_FORBIDDEN)
            
        reports = ReviewReports.objects.filter(status='PENDING')
        serializer = ReviewReportSerializer(reports, many=True)
        return Response(serializer.data)
