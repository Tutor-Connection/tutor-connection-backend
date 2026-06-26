from django.db import models


class Accounts(models.Model):
    id = models.BigAutoField(primary_key=True)
    email = models.CharField(unique=True, max_length=255)
    phone = models.CharField(unique=True, max_length=20)
    password_hash = models.CharField(max_length=255)
    login_provider = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    email_verified = models.BooleanField(blank=True, null=True)
    phone_verified = models.BooleanField(blank=True, null=True)
    last_login_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)


    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
    
    class Meta:
        managed = False
        db_table = 'accounts'


class AdminProfiles(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField('Users', models.DO_NOTHING)
    department = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'admin_profiles'

class Users(models.Model):
    id = models.BigAutoField(primary_key=True)
    account = models.OneToOneField(Accounts, models.DO_NOTHING)
    full_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=20)
    is_online = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'

class StudentProfiles(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField('Users', models.DO_NOTHING)
    grade = models.CharField(max_length=20)
    parent_name = models.CharField(max_length=255, blank=True, null=True)
    parent_phone = models.CharField(max_length=20, blank=True, null=True)
    learning_goal = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'student_profiles'

class TutorProfiles(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField('Users', models.DO_NOTHING)
    experience_years = models.IntegerField(blank=True, null=True)
    teaching_fee = models.DecimalField(max_digits=12, decimal_places=2)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    total_reviews = models.IntegerField(blank=True, null=True)
    response_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    trusted_badge = models.BooleanField(blank=True, null=True)
    education_level = models.CharField(max_length=255, blank=True, null=True)
    university = models.CharField(max_length=255, blank=True, null=True)
    major = models.CharField(max_length=255, blank=True, null=True)
    is_kyc_verified = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tutor_profiles'

class KycDocuments(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('accounts.Users', models.DO_NOTHING)
    document_type = models.CharField(max_length=30)
    file_url = models.TextField()
    status = models.CharField(max_length=20, blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'kyc_documents'

class SystemLogs(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('accounts.Users', models.DO_NOTHING, blank=True, null=True)
    action = models.CharField(max_length=255)
    module = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'system_logs'


