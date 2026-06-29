from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import Users, Accounts, TutorProfiles, StudentProfiles
from apps.support.models import SupportTickets, TicketMessages
from apps.tutoring.models import Reviews, ReviewReports, Classes, Subjects
from django.utils import timezone
from unittest.mock import patch

class SupportAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create an account
        self.account = Accounts.objects.create(email="test@example.com", phone="123", password_hash="hash", status="ACTIVE")
        self.admin_acc = Accounts.objects.create(email="admin@example.com", phone="456", password_hash="hash", status="ACTIVE")
        self.tutor_acc = Accounts.objects.create(email="tutor@example.com", phone="789", password_hash="hash", status="ACTIVE")
        
        # Create User
        self.user = Users.objects.create(
            account=self.account, full_name="Test User", role="USER"
        )
        self.admin_user = Users.objects.create(
            account=self.admin_acc, full_name="Admin User", role="ADMIN"
        )
        self.tutor_user = Users.objects.create(
            account=self.tutor_acc, full_name="Tutor User", role="TUTOR"
        )
        
        # Mock get_user_profile decorator to bypass token authentication
        self.patcher = patch('apps.support.views.get_user_profile')
        self.mock_get_user = self.patcher.start()
        self.mock_get_user.return_value = self.user
        
        # Disable permission_classes dynamically for the test since we bypass JWT
        self.permission_patcher_ticket = patch('apps.support.views.SupportTicketViewSet.permission_classes', [])
        self.permission_patcher_ticket.start()
        
        self.permission_patcher_report = patch('apps.support.views.ReviewReportViewSet.permission_classes', [])
        self.permission_patcher_report.start()
        
    def tearDown(self):
        self.patcher.stop()
        self.permission_patcher_ticket.stop()
        self.permission_patcher_report.stop()

    def test_ticket_create(self):
        data = {
            "title": "Help me",
            "description": "My account is locked",
            "ticket_type": "TECHNICAL"
        }
        response = self.client.post('/api/support/tickets/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SupportTickets.objects.count(), 1)
        ticket = SupportTickets.objects.first()
        self.assertEqual(ticket.title, "Help me")
        self.assertEqual(ticket.status, "OPEN")
        self.assertEqual(ticket.user, self.user)
        
    def test_ticket_list_and_my_tickets(self):
        SupportTickets.objects.create(user=self.user, title="T1", status="OPEN", ticket_type="OTHER")
        SupportTickets.objects.create(user=self.admin_user, title="T2", status="OPEN", ticket_type="OTHER")
        
        # Test my_tickets (as normal user)
        response = self.client.get('/api/support/tickets/my_tickets/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "T1")
        
        # Test generic list as admin
        self.mock_get_user.return_value = self.admin_user
        response = self.client.get('/api/support/tickets/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_ticket_retrieve_and_update(self):
        ticket = SupportTickets.objects.create(user=self.user, title="T1", status="OPEN", ticket_type="OTHER")
        
        response = self.client.get(f'/api/support/tickets/{ticket.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], "T1")
        
        # We need admin to update
        self.mock_get_user.return_value = self.admin_user
        update_data = {"ticket_type": "BILLING"}
        response = self.client.patch(f'/api/support/tickets/{ticket.id}/', update_data, format='json')
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.ticket_type, "BILLING")

    def test_ticket_reply(self):
        ticket = SupportTickets.objects.create(user=self.user, title="T1", status="OPEN", ticket_type="OTHER")
        data = {"message": "Here is a reply", "attachment_url": "http://img.com"}
        response = self.client.post(f'/api/support/tickets/{ticket.id}/reply/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TicketMessages.objects.count(), 1)
        self.assertEqual(TicketMessages.objects.first().message, "Here is a reply")
        
    def test_ticket_update_status(self):
        ticket = SupportTickets.objects.create(user=self.user, title="T1", status="OPEN", ticket_type="OTHER")
        self.mock_get_user.return_value = self.admin_user
        
        response = self.client.post(f'/api/support/tickets/{ticket.id}/update_status/', {"status": "RESOLVED"}, format='json')
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "RESOLVED")
        self.assertIsNotNone(ticket.resolved_at)

    def test_ticket_assign(self):
        ticket = SupportTickets.objects.create(user=self.user, title="T1", status="OPEN", ticket_type="OTHER")
        self.mock_get_user.return_value = self.admin_user
        
        response = self.client.post(f'/api/support/tickets/{ticket.id}/assign/', {"assigned_to": self.admin_user.id}, format='json')
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to, self.admin_user)
        self.assertEqual(ticket.status, "IN_PROGRESS")

    def test_ticket_rate(self):
        ticket = SupportTickets.objects.create(user=self.user, title="T1", status="RESOLVED", ticket_type="OTHER")
        response = self.client.post(f'/api/support/tickets/{ticket.id}/rate/', {"rating": 5, "feedback": "Great!"}, format='json')
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.rating, 5)
        self.assertEqual(ticket.feedback, "Great!")

    def test_ticket_stats(self):
        SupportTickets.objects.create(user=self.user, title="T1", status="OPEN", ticket_type="OTHER")
        SupportTickets.objects.create(user=self.user, title="T2", status="RESOLVED", ticket_type="OTHER")
        
        self.mock_get_user.return_value = self.admin_user
        response = self.client.get('/api/support/tickets/stats/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 2)

    def create_review_setup(self):
        subject = Subjects.objects.create(name="Math")
        student_profile = StudentProfiles.objects.create(user=self.user, grade="10")
        tutor_profile = TutorProfiles.objects.create(user=self.tutor_user, teaching_fee=100.0)
        class_obj = Classes.objects.create(tutor=tutor_profile, student=student_profile, subject=subject, start_date=timezone.now(), tuition_fee=100.0)
        review = Reviews.objects.create(tutor=tutor_profile, student=student_profile, class_field=class_obj, rating=1, content="Bad review")
        return review

    def test_report_create(self):
        review = self.create_review_setup()
        data = {"review": review.id, "reason": "INAPPROPRIATE", "description": "Spam"}
        response = self.client.post('/api/support/reports/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ReviewReports.objects.count(), 1)
        self.assertEqual(ReviewReports.objects.first().status, "PENDING")

    def test_report_process(self):
        review = self.create_review_setup()
        report = ReviewReports.objects.create(
            review=review, reporter=self.user, reason="INAPPROPRIATE", status="PENDING"
        )
        self.mock_get_user.return_value = self.admin_user
        
        data = {"status": "RESOLVED", "action": "Deleted review", "admin_note": "Done"}
        response = self.client.post(f'/api/support/reports/{report.id}/process/', data, format='json')
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertEqual(report.status, "RESOLVED")
        self.assertEqual(report.action_taken, "Deleted review")

    def test_report_pending(self):
        review = self.create_review_setup()
        ReviewReports.objects.create(review=review, reporter=self.user, reason="INAPPROPRIATE", status="PENDING")
        ReviewReports.objects.create(review=review, reporter=self.user, reason="SPAM", status="RESOLVED")
        
        self.mock_get_user.return_value = self.admin_user
        response = self.client.get('/api/support/reports/pending/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], "PENDING")
