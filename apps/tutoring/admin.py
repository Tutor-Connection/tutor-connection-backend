from django.contrib import admin

from .models import (
    AiMatchingLogs,
    Classes,
    ReviewReports,
    Reviews,
    Schedules,
    StudentPosts,
    SubjectCategories,
    Subjects,
    TutorApplications,
    TutorSubjects,
)


@admin.register(SubjectCategories)
class SubjectCategoriesAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "created_at", "updated_at")
    search_fields = ("name", "description")
    list_filter = ("status",)


@admin.register(Subjects)
class SubjectsAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "status", "created_at", "updated_at")
    search_fields = ("name", "description")
    list_filter = ("status", "category")


@admin.register(TutorSubjects)
class TutorSubjectsAdmin(admin.ModelAdmin):
    list_display = ("tutor", "subject", "created_at")
    list_filter = ("subject",)


@admin.register(StudentPosts)
class StudentPostsAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "subject", "title", "status", "moderation_status", "created_at")
    search_fields = ("title", "description", "address")
    list_filter = ("status", "moderation_status", "subject")


@admin.register(TutorApplications)
class TutorApplicationsAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "tutor", "status", "applied_at")
    list_filter = ("status",)


@admin.register(Classes)
class ClassesAdmin(admin.ModelAdmin):
    list_display = ("id", "tutor", "student", "subject", "start_date", "end_date", "tuition_fee", "status")
    list_filter = ("status", "subject")


@admin.register(Schedules)
class SchedulesAdmin(admin.ModelAdmin):
    list_display = ("id", "class_field", "tutor", "student", "start_time", "end_time", "status")
    list_filter = ("status",)


@admin.register(Reviews)
class ReviewsAdmin(admin.ModelAdmin):
    list_display = ("id", "tutor", "student", "class_field", "rating", "status", "created_at")
    search_fields = ("content",)
    list_filter = ("status", "rating")


@admin.register(ReviewReports)
class ReviewReportsAdmin(admin.ModelAdmin):
    list_display = ("id", "review", "reporter", "status", "created_at")
    search_fields = ("reason",)
    list_filter = ("status",)


@admin.register(AiMatchingLogs)
class AiMatchingLogsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tutor",
        "student",
        "post",
        "matching_score",
        "distance_score",
        "fee_score",
        "rating_score",
        "response_score",
        "created_at",
    )
