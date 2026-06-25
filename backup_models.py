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


class AiMatchingLogs(models.Model):
    id = models.BigAutoField(primary_key=True)
    tutor = models.ForeignKey('TutorProfiles', models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey('StudentProfiles', models.DO_NOTHING, blank=True, null=True)
    post = models.ForeignKey('StudentPosts', models.DO_NOTHING, blank=True, null=True)
    matching_score = models.DecimalField(max_digits=5, decimal_places=2)
    distance_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    fee_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    rating_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    response_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ai_matching_logs'


class ChatMembers(models.Model):
    pk = models.CompositePrimaryKey('room_id', 'user_id')
    room = models.ForeignKey('ChatRooms', models.DO_NOTHING)
    user = models.ForeignKey('Users', models.DO_NOTHING)
    joined_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'chat_members'


class ChatMessages(models.Model):
    id = models.BigAutoField(primary_key=True)
    room = models.ForeignKey('ChatRooms', models.DO_NOTHING)
    sender_user = models.ForeignKey('Users', models.DO_NOTHING)
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


class Classes(models.Model):
    id = models.BigAutoField(primary_key=True)
    tutor = models.ForeignKey('TutorProfiles', models.DO_NOTHING)
    student = models.ForeignKey('StudentProfiles', models.DO_NOTHING)
    subject = models.ForeignKey('Subjects', models.DO_NOTHING)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    tuition_fee = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'classes'


class Commissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    class_field = models.ForeignKey(Classes, models.DO_NOTHING, db_column='class_id') 
    tutor = models.ForeignKey('TutorProfiles', models.DO_NOTHING)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=20, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'commissions'


class KycDocuments(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING)
    document_type = models.CharField(max_length=30)
    file_url = models.TextField()
    status = models.CharField(max_length=20, blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'kyc_documents'


class Notifications(models.Model):
    id = models.BigAutoField(primary_key=True)
    sender_user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    receiver_user = models.ForeignKey('Users', models.DO_NOTHING, related_name='notifications_receiver_user_set')
    title = models.CharField(max_length=255)
    content = models.TextField()
    type = models.CharField(max_length=20)
    is_read = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notifications'


class Payments(models.Model):
    id = models.BigAutoField(primary_key=True)
    class_field = models.ForeignKey(Classes, models.DO_NOTHING, db_column='class_id') 
    tutor = models.ForeignKey('TutorProfiles', models.DO_NOTHING)
    student = models.ForeignKey('StudentProfiles', models.DO_NOTHING)
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


class ReviewReports(models.Model):
    id = models.BigAutoField(primary_key=True)
    review = models.ForeignKey('Reviews', models.DO_NOTHING)
    reporter = models.ForeignKey('Users', models.DO_NOTHING)
    reason = models.TextField()
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'review_reports'


class Reviews(models.Model):
    id = models.BigAutoField(primary_key=True)
    tutor = models.ForeignKey('TutorProfiles', models.DO_NOTHING)
    student = models.ForeignKey('StudentProfiles', models.DO_NOTHING)
    class_field = models.ForeignKey(Classes, models.DO_NOTHING, db_column='class_id') 
    rating = models.IntegerField()
    content = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'reviews'
        unique_together = (('class_field', 'student'),)


class Schedules(models.Model):
    id = models.BigAutoField(primary_key=True)
    class_field = models.ForeignKey(Classes, models.DO_NOTHING, db_column='class_id')  
    tutor = models.ForeignKey('TutorProfiles', models.DO_NOTHING)
    student = models.ForeignKey('StudentProfiles', models.DO_NOTHING)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'schedules'


class StudentPosts(models.Model):
    id = models.BigAutoField(primary_key=True)
    student = models.ForeignKey('StudentProfiles', models.DO_NOTHING)
    subject = models.ForeignKey('Subjects', models.DO_NOTHING)
    title = models.CharField(max_length=255)
    description = models.TextField()
    preferred_fee = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    schedule_note = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    moderation_status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'student_posts'


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


class SubjectCategories(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'subject_categories'


class Subjects(models.Model):
    id = models.BigAutoField(primary_key=True)
    category = models.ForeignKey(SubjectCategories, models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(unique=True, max_length=100)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'subjects'


class SupportTickets(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING)
    title = models.CharField(max_length=255)
    description = models.TextField()
    attachment_url = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'support_tickets'


class SystemLogs(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    action = models.CharField(max_length=255)
    module = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'system_logs'


class TicketMessages(models.Model):
    id = models.BigAutoField(primary_key=True)
    ticket = models.ForeignKey(SupportTickets, models.DO_NOTHING)
    sender = models.ForeignKey('Users', models.DO_NOTHING)
    message = models.TextField()
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ticket_messages'


class TutorApplications(models.Model):
    id = models.BigAutoField(primary_key=True)
    post = models.ForeignKey(StudentPosts, models.DO_NOTHING)
    tutor = models.ForeignKey('TutorProfiles', models.DO_NOTHING)
    status = models.CharField(max_length=20, blank=True, null=True)
    applied_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tutor_applications'
        unique_together = (('post', 'tutor'),)


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


class TutorSubjects(models.Model):
    pk = models.CompositePrimaryKey('tutor_id', 'subject_id')
    tutor = models.ForeignKey(TutorProfiles, models.DO_NOTHING)
    subject = models.ForeignKey(Subjects, models.DO_NOTHING)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tutor_subjects'


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
    user = models.OneToOneField(Users, models.DO_NOTHING)
    balance = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'wallets'
