from django.db import models

# Create your models here.
class WalletTransactions(models.Model):
    id = models.BigAutoField(primary_key=True)
    wallet = models.ForeignKey('Wallets', models.DO_NOTHING)
    transaction_type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    external_ref_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wallet_transactions'


class Wallets(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField('accounts.Users', models.DO_NOTHING)
    balance = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wallets'

class Commissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    class_field = models.ForeignKey("tutoring.Classes", models.DO_NOTHING, db_column='class_id') 
    tutor = models.ForeignKey('accounts.TutorProfiles', models.DO_NOTHING)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=20, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'commissions'


class Payments(models.Model):
    id = models.BigAutoField(primary_key=True)
    class_field = models.ForeignKey("tutoring.Classes", models.DO_NOTHING, db_column='class_id') 
    tutor = models.ForeignKey('accounts.TutorProfiles', models.DO_NOTHING)
    student = models.ForeignKey('accounts.StudentProfiles', models.DO_NOTHING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    tutor_confirmed = models.BooleanField(blank=True, null=True)
    student_confirmed = models.BooleanField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'payments'

