from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import Users, Accounts, TutorProfiles, StudentProfiles
from apps.finance.models import Payments, Commissions, Wallets, WalletTransactions
from apps.tutoring.models import Classes, Subjects
from django.utils import timezone
from unittest.mock import patch
from decimal import Decimal

class FinanceAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Accounts
        self.admin_acc = Accounts.objects.create(email="admin@example.com", phone="123", password_hash="hash", status="ACTIVE")
        self.tutor_acc = Accounts.objects.create(email="tutor@example.com", phone="456", password_hash="hash", status="ACTIVE")
        self.student_acc = Accounts.objects.create(email="student@example.com", phone="789", password_hash="hash", status="ACTIVE")
        
        # Users
        self.admin_user = Users.objects.create(account=self.admin_acc, full_name="Admin", role="ADMIN")
        self.tutor_user = Users.objects.create(account=self.tutor_acc, full_name="Tutor", role="TUTOR")
        self.student_user = Users.objects.create(account=self.student_acc, full_name="Student", role="USER")
        
        # Profiles
        self.tutor_profile = TutorProfiles.objects.create(user=self.tutor_user, teaching_fee=100.0)
        self.student_profile = StudentProfiles.objects.create(user=self.student_user, grade="10")
        
        # Class setup
        self.subject = Subjects.objects.create(name="Math")
        self.class_obj = Classes.objects.create(
            tutor=self.tutor_profile, student=self.student_profile, subject=self.subject, 
            start_date=timezone.now(), tuition_fee=100.0, status='ACTIVE'
        )

        # Mocks
        self.patcher = patch('apps.finance.views.get_user_profile')
        self.mock_get_user = self.patcher.start()
        self.mock_get_user.return_value = self.student_user
        
        self.perm_patcher1 = patch('apps.finance.views.PaymentViewSet.permission_classes', [])
        self.perm_patcher1.start()
        self.perm_patcher2 = patch('apps.finance.views.CommissionViewSet.permission_classes', [])
        self.perm_patcher2.start()
        self.perm_patcher3 = patch('apps.finance.views.WalletViewSet.permission_classes', [])
        self.perm_patcher3.start()

    def tearDown(self):
        self.patcher.stop()
        self.perm_patcher1.stop()
        self.perm_patcher2.stop()
        self.perm_patcher3.stop()

    # --- Payment Tests ---
    def test_create_payment(self):
        data = {
            "class_field": self.class_obj.id,
            "amount": "100.00",
            "due_date": "2026-07-01",
            "payment_method": "VNPAY"
        }
        response = self.client.post('/api/finance/payments/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Payments.objects.count(), 1)

    def test_confirm_payment(self):
        payment = Payments.objects.create(
            class_field=self.class_obj, tutor=self.tutor_profile, student=self.student_profile,
            amount=100, due_date="2026-07-01", status="PENDING"
        )
        # Student confirms
        self.mock_get_user.return_value = self.student_user
        response = self.client.post('/api/finance/payments/confirm_payment/', {"payment_id": payment.id, "confirm_by": "STUDENT"}, format='json')
        self.assertEqual(response.status_code, 200)
        
        # Tutor confirms
        self.mock_get_user.return_value = self.tutor_user
        response = self.client.post('/api/finance/payments/confirm_payment/', {"payment_id": payment.id, "confirm_by": "TUTOR"}, format='json')
        self.assertEqual(response.status_code, 200)
        
        payment.refresh_from_db()
        self.assertEqual(payment.status, "PAID")

    # --- Commission Tests ---
    def test_auto_calculate_commission(self):
        self.mock_get_user.return_value = self.admin_user
        response = self.client.post('/api/finance/commissions/auto_calculate/', format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Commissions.objects.count(), 1)
        
    def test_pay_commission(self):
        commission = Commissions.objects.create(
            class_field=self.class_obj, tutor=self.tutor_profile, percentage=10, amount=10, due_date="2026-07-01", status="PENDING"
        )
        
        # Setup wallet with enough balance
        tutor_wallet = Wallets.objects.create(user=self.tutor_user, balance=50)
        
        self.mock_get_user.return_value = self.tutor_user
        response = self.client.post(f'/api/finance/commissions/{commission.id}/pay/', format='json')
        self.assertEqual(response.status_code, 200)
        
        commission.refresh_from_db()
        self.assertEqual(commission.status, "PAID")
        
        tutor_wallet.refresh_from_db()
        self.assertEqual(tutor_wallet.balance, Decimal("40.00"))

    # --- Wallet Tests ---
    def test_deposit(self):
        self.mock_get_user.return_value = self.student_user
        data = {"amount": "200.00", "payment_gateway": "VNPAY"}
        response = self.client.post('/api/finance/wallets/deposit/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn("payment_url", response.data)
        
        tx = WalletTransactions.objects.first()
        self.assertEqual(tx.status, "PENDING")
        self.assertEqual(tx.amount, Decimal("200.00"))

    def test_deposit_callback(self):
        wallet = Wallets.objects.create(user=self.student_user, balance=0)
        tx = WalletTransactions.objects.create(wallet=wallet, transaction_type="DEPOSIT", amount=200, status="PENDING")
        
        data = {"transaction_id": tx.id, "status": "SUCCESS"}
        response = self.client.post('/api/finance/wallets/deposit_callback/', data, format='json')
        self.assertEqual(response.status_code, 200)
        
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("200.00"))
        
        tx.refresh_from_db()
        self.assertEqual(tx.status, "SUCCESS")

    def test_withdraw(self):
        wallet = Wallets.objects.create(user=self.tutor_user, balance=500)
        self.mock_get_user.return_value = self.tutor_user
        
        data = {
            "amount": "100.00", 
            "bank_account": "123456789", 
            "bank_name": "VCB", 
            "bank_owner": "Nguyen Van A"
        }
        response = self.client.post('/api/finance/wallets/withdraw/', data, format='json')
        self.assertEqual(response.status_code, 200)
        
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("400.00"))
        
        tx = WalletTransactions.objects.get(transaction_type="WITHDRAW")
        self.assertEqual(tx.status, "PENDING")
        self.assertEqual(tx.bank_account, "123456789")
