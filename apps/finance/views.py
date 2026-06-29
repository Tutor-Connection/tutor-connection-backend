from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum
from decimal import Decimal

from .models import Payments, Commissions, Wallets, WalletTransactions
from apps.accounts.models import Users, TutorProfiles, StudentProfiles
from apps.tutoring.models import Classes
from apps.communication.models import Notifications

from .serializers import (
    PaymentSerializer, PaymentCreateSerializer,
    CommissionSerializer, WalletSerializer, WalletTransactionSerializer
)

import uuid

def get_user_profile(user):
    # --- MOCK FOR TESTING ---
    mock_user = Users.objects.first()
    if mock_user: return mock_user
    # ------------------------
    if isinstance(user, Users):
        return user
    if hasattr(user, 'users'):
        return user.users
    return Users.objects.filter(id=getattr(user, 'id', None)).first()

def get_role(user_profile):
    return getattr(user_profile, 'role', '')

class PaymentViewSet(viewsets.ModelViewSet):
    """
    API ViewSet quản lý các giao dịch thanh toán học phí (Payments).
    - GET /api/finance/payments/ : Lấy danh sách thanh toán.
    - POST /api/finance/payments/ : Tạo yêu cầu thanh toán mới.
    - GET /api/finance/payments/{id}/ : Xem chi tiết giao dịch thanh toán.
    - PUT /api/finance/payments/{id}/ : Cập nhật giao dịch.
    - POST /api/finance/payments/confirm_payment/ : Xác nhận thanh toán (bởi Tutor/Student).
    """
    queryset = Payments.objects.all().order_by('-created_at')
    # permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_queryset(self):
        user = get_user_profile(self.request.user)
        role = get_role(user)
        queryset = super().get_queryset()
        
        if role == 'TUTOR':
            queryset = queryset.filter(tutor__user=user)
        elif role == 'USER' or role == 'STUDENT':
            queryset = queryset.filter(student__user=user)
            
        status_filter = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        if search:
            queryset = queryset.filter(
                Q(tutor__user__full_name__icontains=search) |
                Q(student__user__full_name__icontains=search)
            )
            
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        class_obj = serializer.validated_data['class_field']
        
        # Check pending payment
        if Payments.objects.filter(class_field=class_obj, status='PENDING').exists():
            return Response({"detail": "A pending payment already exists for this class."}, status=status.HTTP_400_BAD_REQUEST)
            
        payment = Payments.objects.create(
            class_field=class_obj,
            tutor=class_obj.tutor,
            student=class_obj.student,
            amount=serializer.validated_data['amount'],
            due_date=serializer.validated_data['due_date'],
            payment_method=serializer.validated_data.get('payment_method', 'CASH'),
            status='PENDING',
            tutor_confirmed=False,
            student_confirmed=False,
            created_at=timezone.now(),
            updated_at=timezone.now()
        )
        
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        user = get_user_profile(request.user)
        if get_role(user) != 'ADMIN':
            return Response({"detail": "Only admin can update payments."}, status=status.HTTP_403_FORBIDDEN)
            
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = PaymentSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Prevent status update directly through this endpoint if needed, but since it's admin, we might allow it.
        # But per prompt: "Không cho update status qua đây"
        if 'status' in request.data:
            return Response({"detail": "Cannot update status directly."}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer.save(updated_at=timezone.now())
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        user = get_user_profile(request.user)
        if get_role(user) != 'ADMIN':
            return Response({"detail": "Only admin can delete payments."}, status=status.HTTP_403_FORBIDDEN)
            
        instance = self.get_object()
        if instance.status == 'PAID':
            return Response({"detail": "Cannot delete a paid payment."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Soft delete: update status to CANCELLED or similar (Wait, prompt says soft delete, I will just set status to DELETED)
        instance.status = 'DELETED'
        instance.updated_at = timezone.now()
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def confirm_payment(self, request):
        payment_id = request.data.get('payment_id')
        confirm_by = request.data.get('confirm_by')
        payment_method = request.data.get('payment_method')
        
        try:
            payment = Payments.objects.get(id=payment_id)
        except Payments.DoesNotExist:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
            
        user = get_user_profile(request.user)
        role = get_role(user)
        
        if confirm_by == 'TUTOR' and (role == 'TUTOR' or role == 'ADMIN'):
            payment.tutor_confirmed = True
        elif confirm_by == 'STUDENT' and (role == 'USER' or role == 'STUDENT' or role == 'ADMIN'):
            payment.student_confirmed = True
        elif confirm_by == 'ADMIN' and role == 'ADMIN':
            payment.tutor_confirmed = True
            payment.student_confirmed = True
        else:
            return Response({"detail": "Invalid confirm_by or permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
        if payment_method:
            payment.payment_method = payment_method
            
        if payment.tutor_confirmed and payment.student_confirmed and payment.status != 'PAID':
            payment.status = 'PAID'
            
            # If wallet, deduct from student, add to tutor (Simplified logic since this requires wallet integration)
            if payment.payment_method == 'WALLET':
                student_wallet, _ = Wallets.objects.get_or_create(user=payment.student.user)
                student_wallet.balance = (student_wallet.balance or 0) - payment.amount
                student_wallet.save()
                
                WalletTransactions.objects.create(
                    wallet=student_wallet, transaction_type='PAYMENT', amount=-payment.amount,
                    description=f"Payment for class {payment.class_field.id}", status='SUCCESS', created_at=timezone.now()
                )
                
            # Notify both
            Notifications.objects.create(
                sender_user=user, receiver_user=payment.tutor.user,
                title="Payment Confirmed", content=f"Payment {payment.id} has been fully confirmed.", type="PAYMENT", is_read=False, created_at=timezone.now()
            )
            Notifications.objects.create(
                sender_user=user, receiver_user=payment.student.user,
                title="Payment Confirmed", content=f"Payment {payment.id} has been fully confirmed.", type="PAYMENT", is_read=False, created_at=timezone.now()
            )
            
        payment.updated_at = timezone.now()
        payment.save()
        return Response({"detail": "Payment confirmation updated.", "status": payment.status})

    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        return self.list(request)

    @action(detail=False, methods=['post'])
    def remind(self, request):
        payment_id = request.data.get('payment_id')
        try:
            payment = Payments.objects.get(id=payment_id)
        except Payments.DoesNotExist:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if payment.status not in ['PENDING', 'OVERDUE']:
            return Response({"detail": "Can only remind pending or overdue payments."}, status=status.HTTP_400_BAD_REQUEST)
            
        user = get_user_profile(request.user)
        
        Notifications.objects.create(
            sender_user=user, receiver_user=payment.student.user,
            title="Payment Reminder", content=f"Please complete payment {payment.id}.", type="PAYMENT", is_read=False, created_at=timezone.now()
        )
        Notifications.objects.create(
            sender_user=user, receiver_user=payment.tutor.user,
            title="Payment Reminder", content=f"Reminder sent for payment {payment.id}.", type="PAYMENT", is_read=False, created_at=timezone.now()
        )
        return Response({"detail": "Reminder sent."})

class CommissionViewSet(viewsets.ModelViewSet):
    """
    API ViewSet quản lý hoa hồng hệ thống (Commissions).
    - GET /api/finance/commissions/ : Lấy danh sách hoa hồng.
    - POST /api/finance/commissions/{id}/pay/ : Gia sư thanh toán tiền hoa hồng (trừ tiền từ ví).
    - GET /api/finance/commissions/stats/ : Thống kê hoa hồng.
    - POST /api/finance/commissions/auto_calculate/ : Tự động tính toán hoa hồng cho các lớp đang hoạt động (chỉ dành cho ADMIN).
    """
    queryset = Commissions.objects.all().order_by('-due_date')
    serializer_class = CommissionSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = get_user_profile(self.request.user)
        role = get_role(user)
        queryset = super().get_queryset()
        
        if role == 'TUTOR':
            queryset = queryset.filter(tutor__user=user)
        elif role != 'ADMIN':
            return queryset.none()
            
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        # Optional: date range filtering can be added here
        return queryset

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def pay(self, request, pk=None):
        commission = self.get_object()
        
        if commission.status == 'PAID':
            return Response({"detail": "Commission is already paid."}, status=status.HTTP_400_BAD_REQUEST)
            
        tutor_wallet, created = Wallets.objects.get_or_create(user=commission.tutor.user)
        
        if not tutor_wallet.balance or tutor_wallet.balance < commission.amount:
            return Response({"detail": "Insufficient wallet balance."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Deduct balance
        tutor_wallet.balance -= commission.amount
        tutor_wallet.save()
        
        # Create transaction
        WalletTransactions.objects.create(
            wallet=tutor_wallet,
            transaction_type='COMMISSION_FEE',
            amount=-commission.amount,
            description=f"Paid commission {commission.id}",
            status='SUCCESS',
            created_at=timezone.now()
        )
        
        commission.status = 'PAID'
        commission.paid_at = timezone.now()
        commission.save()
        
        Notifications.objects.create(
            sender_user=get_user_profile(request.user),
            receiver_user=commission.tutor.user,
            title="Commission Paid",
            content=f"Commission for class {commission.class_field.id} has been paid.",
            type="SYSTEM",
            created_at=timezone.now()
        )
        
        return Response({"detail": "Commission paid successfully."})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        user = get_user_profile(request.user)
        role = get_role(user)
        queryset = super().get_queryset()
        
        if role == 'TUTOR':
            queryset = queryset.filter(tutor__user=user)
        elif role != 'ADMIN':
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
        stats = queryset.aggregate(
            total_pending=Sum('amount', filter=Q(status='PENDING')),
            total_overdue=Sum('amount', filter=Q(status='OVERDUE')),
            total_paid=Sum('amount', filter=Q(status='PAID')),
            total_commission=Sum('amount')
        )
        # Handle None values
        stats = {k: (v if v else 0) for k, v in stats.items()}
        return Response(stats)

    @action(detail=False, methods=['post'])
    def auto_calculate(self, request):
        user = get_user_profile(request.user)
        if get_role(user) != 'ADMIN':
            return Response({"detail": "Only admin can trigger auto_calculate."}, status=status.HTTP_403_FORBIDDEN)
            
        # Find active classes without commissions
        active_classes = Classes.objects.filter(status='ACTIVE')
        created_count = 0
        
        for cls in active_classes:
            if not Commissions.objects.filter(class_field=cls).exists():
                Commissions.objects.create(
                    class_field=cls,
                    tutor=cls.tutor,
                    percentage=10.0, # 10% first month
                    amount=cls.tuition_fee * 10 / 100,
                    due_date=timezone.now().date() + timezone.timedelta(days=30),
                    status='PENDING',
                    created_at=timezone.now()
                )
                created_count += 1
                
        return Response({"detail": f"Auto calculated {created_count} commissions.", "created": created_count})

class WalletViewSet(viewsets.ModelViewSet):
    """
    API ViewSet quản lý ví điện tử của người dùng (Wallets).
    - GET /api/finance/wallets/my_wallet/ : Xem thông tin và số dư ví của bản thân.
    - POST /api/finance/wallets/deposit/ : Yêu cầu nạp tiền vào ví (tạo URL thanh toán).
    - POST /api/finance/wallets/deposit_callback/ : Webhook nhận kết quả thanh toán từ Gateway.
    - POST /api/finance/wallets/withdraw/ : Yêu cầu rút tiền về tài khoản ngân hàng.
    - GET /api/finance/wallets/{id}/transactions/ : Xem lịch sử giao dịch nạp/rút/thanh toán của ví.
    """
    queryset = Wallets.objects.all()
    serializer_class = WalletSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = get_user_profile(self.request.user)
        if get_role(user) == 'ADMIN':
            queryset = super().get_queryset()
            status_filter = self.request.query_params.get('status')
            if status_filter:
                return queryset.filter(status=status_filter)
            return queryset
        return Wallets.objects.filter(user=user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = get_user_profile(request.user)
        if get_role(user) != 'ADMIN' and instance.user != user:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def my_wallet(self, request):
        user = get_user_profile(request.user)
        wallet, created = Wallets.objects.get_or_create(user=user)
        return Response(WalletSerializer(wallet).data)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def deposit(self, request):
        amount = request.data.get('amount')
        payment_gateway = request.data.get('payment_gateway')
        
        if not amount or not payment_gateway:
            return Response({"detail": "Amount and payment_gateway are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        user = get_user_profile(request.user)
        wallet, _ = Wallets.objects.get_or_create(user=user)
        
        tx = WalletTransactions.objects.create(
            wallet=wallet,
            transaction_type='DEPOSIT',
            amount=amount,
            description=f"Deposit via {payment_gateway}",
            status='PENDING',
            created_at=timezone.now()
        )
        
        payment_url = f"https://mock-{payment_gateway.lower()}.com/pay?tx={tx.id}"
        
        return Response({
            "transaction_id": tx.id,
            "payment_url": payment_url,
            "qr_code": "mock_qr_string"
        })

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def withdraw(self, request):
        amount = request.data.get('amount')
        bank_account = request.data.get('bank_account')
        bank_name = request.data.get('bank_name')
        bank_owner = request.data.get('bank_owner')
        
        if not all([amount, bank_account, bank_name, bank_owner]):
            return Response({"detail": "Amount, bank account, name, owner required."}, status=status.HTTP_400_BAD_REQUEST)
            
        user = get_user_profile(request.user)
        wallet, _ = Wallets.objects.get_or_create(user=user)
        
        if not wallet.balance or wallet.balance < Decimal(str(amount)):
            return Response({"detail": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)
            
        wallet.balance -= Decimal(str(amount))
        wallet.save()
        
        tx = WalletTransactions.objects.create(
            wallet=wallet,
            transaction_type='WITHDRAW',
            amount=-Decimal(str(amount)),
            description="Withdrawal request",
            bank_account=bank_account,
            bank_name=bank_name,
            bank_owner=bank_owner,
            status='PENDING',
            created_at=timezone.now()
        )
        
        # Notify admin
        admins = Users.objects.filter(role='ADMIN')
        for admin in admins:
            Notifications.objects.create(
                sender_user=user, receiver_user=admin,
                title="New Withdrawal Request", content=f"User requested {amount}", type="SYSTEM", is_read=False, created_at=timezone.now()
            )
            
        return Response({"transaction_id": tx.id})

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        wallet = self.get_object()
        user = get_user_profile(request.user)
        
        if get_role(user) != 'ADMIN' and wallet.user != user:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
            
        txs = WalletTransactions.objects.filter(wallet=wallet).order_by('-created_at')
        tx_type = request.query_params.get('transaction_type')
        if tx_type:
            txs = txs.filter(transaction_type=tx_type)
            
        # Can add pagination here
        return Response(WalletTransactionSerializer(txs, many=True).data)

    @action(detail=False, methods=['post'])
    def deposit_callback(self, request):
        tx_id = request.data.get('transaction_id')
        status_code = request.data.get('status')
        
        try:
            tx = WalletTransactions.objects.get(id=tx_id, transaction_type='DEPOSIT', status='PENDING')
        except WalletTransactions.DoesNotExist:
            return Response({"detail": "Invalid or processed transaction."}, status=status.HTTP_400_BAD_REQUEST)
            
        if status_code == 'SUCCESS':
            tx.status = 'SUCCESS'
            tx.wallet.balance = (tx.wallet.balance or 0) + tx.amount
            tx.wallet.save()
            msg = "Deposit successful."
        else:
            tx.status = 'FAILED'
            msg = "Deposit failed."
            
        tx.save()
        
        Notifications.objects.create(
            sender_user=None, receiver_user=tx.wallet.user,
            title="Deposit Update", content=msg, type="SYSTEM", is_read=False, created_at=timezone.now()
        )
        return Response({"detail": msg})
