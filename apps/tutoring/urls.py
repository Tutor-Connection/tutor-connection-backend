from django.urls import path

from . import views


RESOURCE_ROUTES = [
    ("subject-categories", "subject_categories"),
    ("subjects", "subjects"),
    ("student-posts", "student_posts"),
    ("tutor-applications", "tutor_applications"),
    ("classes", "classes"),
    ("schedules", "schedules"),
    ("reviews", "reviews"),
    ("review-reports", "review_reports"),
    ("ai-matching-logs", "ai_matching_logs"),
]

urlpatterns = [
    path("", views.api_index, name="tutoring_index"),
    path("tutor-subjects/", views.tutor_subjects_collection, name="tutor_subjects_collection"),
    path(
        "tutor-subjects/<int:tutor_id>/<int:subject_id>/",
        views.tutor_subject_detail,
        name="tutor_subject_detail",
    ),
    path("student-posts/<int:post_id>/apply/", views.apply_to_post, name="student_post_apply"),
    path("student-posts/<int:post_id>/matches/", views.match_tutors_for_post, name="student_post_matches"),
    path(
        "tutor-applications/<int:application_id>/create-class/",
        views.create_class_from_application,
        name="application_create_class",
    ),
    path("tutors/<int:tutor_id>/review-summary/", views.tutor_review_summary, name="tutor_review_summary"),
]

for resource, route_name in RESOURCE_ROUTES:
    urlpatterns.extend(
        [
            path(f"{resource}/", views.resource_collection, {"resource": resource}, name=f"{route_name}_collection"),
            path(f"{resource}/<int:pk>/", views.resource_detail, {"resource": resource}, name=f"{route_name}_detail"),
        ]
    )
