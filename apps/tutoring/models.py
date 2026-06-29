from django.db import models

# Create your models here.
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

class TutorSubjects(models.Model):
    pk = models.CompositePrimaryKey('tutor_id', 'subject_id')
    tutor = models.ForeignKey("accounts.TutorProfiles", models.DO_NOTHING)
    subject = models.ForeignKey(Subjects, models.DO_NOTHING)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tutor_subjects'

class StudentPosts(models.Model):
    id = models.BigAutoField(primary_key=True)
    student = models.ForeignKey('accounts.StudentProfiles', models.DO_NOTHING)
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

class TutorApplications(models.Model):
    id = models.BigAutoField(primary_key=True)
    post = models.ForeignKey(StudentPosts, models.DO_NOTHING)
    tutor = models.ForeignKey('accounts.TutorProfiles', models.DO_NOTHING)
    status = models.CharField(max_length=20, blank=True, null=True)
    applied_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tutor_applications'
        unique_together = (('post', 'tutor'),)

class Classes(models.Model):
    id = models.BigAutoField(primary_key=True)
    tutor = models.ForeignKey('accounts.TutorProfiles', models.DO_NOTHING)
    student = models.ForeignKey('accounts.StudentProfiles', models.DO_NOTHING)
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

class Schedules(models.Model):
    id = models.BigAutoField(primary_key=True)
    class_field = models.ForeignKey(Classes, models.DO_NOTHING, db_column='class_id')  
    tutor = models.ForeignKey('accounts.TutorProfiles', models.DO_NOTHING)
    student = models.ForeignKey('accounts.StudentProfiles', models.DO_NOTHING)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'schedules'

class ReviewReports(models.Model):
    id = models.BigAutoField(primary_key=True)
    review = models.ForeignKey('Reviews', models.DO_NOTHING)
    reporter = models.ForeignKey('accounts.Users', models.DO_NOTHING)
    reason = models.TextField()
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'review_reports'


class Reviews(models.Model):
    id = models.BigAutoField(primary_key=True)
    tutor = models.ForeignKey('accounts.TutorProfiles', models.DO_NOTHING)
    student = models.ForeignKey('accounts.StudentProfiles', models.DO_NOTHING)
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

class AiMatchingLogs(models.Model):
    id = models.BigAutoField(primary_key=True)
    tutor = models.ForeignKey('accounts.TutorProfiles', models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey('accounts.StudentProfiles', models.DO_NOTHING, blank=True, null=True)
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

