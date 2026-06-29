from rest_framework import serializers
from .models import Payments, Commissions, Wallets, WalletTransactions
from apps.accounts.models import Users, TutorProfiles, StudentProfiles
from apps.tutoring.models import Classes

# Helper nested serializers for read-only fields
class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['id', 'full_name', 'avatar_url', 'role']

class TutorProfileBasicSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = TutorProfiles
        fields = ['id', 'user']

class StudentProfileBasicSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = StudentProfiles
        fields = ['id', 'user']

class ClassBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classes
        fields = ['id', 'subject', 'tuition_fee', 'status']

class PaymentSerializer(serializers.ModelSerializer):
    tutor_detail = TutorProfileBasicSerializer(source='tutor', read_only=True)
    student_detail = StudentProfileBasicSerializer(source='student', read_only=True)
    class_detail = ClassBasicSerializer(source='class_field', read_only=True)

    class Meta:
        model = Payments
        fields = '__all__'
        read_only_fields = ['tutor', 'student', 'created_at', 'updated_at']

class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payments
        fields = ['class_field', 'amount', 'due_date', 'payment_method']

class CommissionSerializer(serializers.ModelSerializer):
    tutor_detail = TutorProfileBasicSerializer(source='tutor', read_only=True)
    class_detail = ClassBasicSerializer(source='class_field', read_only=True)

    class Meta:
        model = Commissions
        fields = '__all__'

class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransactions
        fields = '__all__'

class WalletSerializer(serializers.ModelSerializer):
    user_detail = UserBasicSerializer(source='user', read_only=True)
    
    class Meta:
        model = Wallets
        fields = '__all__'
