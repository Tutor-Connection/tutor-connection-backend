import json
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import Accounts, StudentProfiles, TutorProfiles, Users
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


class UnmanagedModelTablesMixin:
    unmanaged_models = (
        Accounts,
        Users,
        StudentProfiles,
        TutorProfiles,
        SubjectCategories,
        Subjects,
        TutorSubjects,
        StudentPosts,
        TutorApplications,
        Classes,
        Schedules,
        Reviews,
        ReviewReports,
        AiMatchingLogs,
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._created_test_models = []
        existing_tables = set(connection.introspection.table_names())

        with connection.schema_editor() as schema_editor:
            for model in cls.unmanaged_models:
                if model._meta.db_table in existing_tables:
                    continue
                schema_editor.create_model(model)
                cls._created_test_models.append(model)
                existing_tables.add(model._meta.db_table)

    @classmethod
    def tearDownClass(cls):
        existing_tables = set(connection.introspection.table_names())
        with connection.schema_editor() as schema_editor:
            for model in reversed(getattr(cls, "_created_test_models", [])):
                if model._meta.db_table in existing_tables:
                    schema_editor.delete_model(model)
        super().tearDownClass()

    def clear_unmanaged_tables(self):
        for model in reversed(self.unmanaged_models):
            if model._meta.db_table in connection.introspection.table_names():
                model.objects.all().delete()


class TutoringApiTestCase(UnmanagedModelTablesMixin, TransactionTestCase):
    base_url = "/api/tutoring/"

    def setUp(self):
        self.clear_unmanaged_tables()
        self.slug = uuid4().hex[:10]
        self.now = timezone.now()
        self.today = date.today()

        self.student_account, self.student_user = self.create_account_user("student", "Student User")
        self.tutor_account, self.tutor_user = self.create_account_user(
            "tutor",
            "Tutor User",
            latitude=Decimal("10.7800000"),
            longitude=Decimal("106.7050000"),
        )
        self.other_tutor_account, self.other_tutor_user = self.create_account_user(
            "other-tutor",
            "Other Tutor",
            latitude=Decimal("10.7900000"),
            longitude=Decimal("106.7150000"),
        )

        self.student = StudentProfiles.objects.create(
            user=self.student_user,
            grade="10",
            parent_name="Parent",
            parent_phone=f"parent-{self.slug}",
            learning_goal="Improve math",
            created_at=self.now,
            updated_at=self.now,
        )
        self.tutor = TutorProfiles.objects.create(
            user=self.tutor_user,
            experience_years=5,
            teaching_fee=Decimal("220000.00"),
            rating_avg=Decimal("4.50"),
            total_reviews=1,
            response_rate=Decimal("90.00"),
            trusted_badge=True,
            education_level="Bachelor",
            university="Test University",
            major="Mathematics",
            is_kyc_verified=True,
            created_at=self.now,
            updated_at=self.now,
        )
        self.other_tutor = TutorProfiles.objects.create(
            user=self.other_tutor_user,
            experience_years=2,
            teaching_fee=Decimal("260000.00"),
            rating_avg=Decimal("4.00"),
            total_reviews=0,
            response_rate=Decimal("70.00"),
            trusted_badge=False,
            education_level="Bachelor",
            university="Other University",
            major="Physics",
            is_kyc_verified=False,
            created_at=self.now,
            updated_at=self.now,
        )

        self.category = self.create_category("Core")
        self.subject = self.create_subject("Mathematics", self.category)
        self.post = self.create_student_post("Need math tutor")
        self.tutor_subject = TutorSubjects.objects.create(
            tutor=self.tutor,
            subject=self.subject,
            created_at=self.now,
        )
        self.class_obj = self.create_class()
        self.review = Reviews.objects.create(
            tutor=self.tutor,
            student=self.student,
            class_field=self.class_obj,
            rating=5,
            content="Great tutor",
            status="visible",
            created_at=self.now,
            updated_at=self.now,
        )

    def create_account_user(self, prefix, full_name, latitude=None, longitude=None):
        account = Accounts.objects.create(
            email=f"{prefix}-{self.slug}@example.com",
            phone=f"{prefix}-{self.slug}",
            password_hash="not-used-in-tests",
            login_provider="email",
            status="active",
            email_verified=True,
            phone_verified=True,
            created_at=self.now,
            updated_at=self.now,
        )
        user = Users.objects.create(
            account=account,
            full_name=full_name,
            gender="other",
            avatar_url="https://example.com/avatar.png",
            address="Ho Chi Minh City",
            latitude=latitude if latitude is not None else Decimal("10.7769000"),
            longitude=longitude if longitude is not None else Decimal("106.7009000"),
            bio="Test user",
            role="tutor" if "tutor" in prefix else "student",
            is_online=True,
            created_at=self.now,
            updated_at=self.now,
        )
        return account, user

    def create_category(self, name):
        return SubjectCategories.objects.create(
            name=f"{name} {self.slug}",
            description=f"{name} category",
            status="active",
            created_at=self.now,
            updated_at=self.now,
        )

    def create_subject(self, name, category=None):
        return Subjects.objects.create(
            category=category or self.category,
            name=f"{name} {uuid4().hex[:8]}",
            description=f"{name} subject",
            status="active",
            created_at=self.now,
            updated_at=self.now,
        )

    def create_student_post(self, title, subject=None):
        return StudentPosts.objects.create(
            student=self.student,
            subject=subject or self.subject,
            title=f"{title} {uuid4().hex[:8]}",
            description="Need a tutor for exam preparation",
            preferred_fee=Decimal("250000.00"),
            schedule_note="Evenings",
            address="District 1",
            latitude=Decimal("10.7769000"),
            longitude=Decimal("106.7009000"),
            status="open",
            moderation_status="approved",
            created_at=self.now,
            updated_at=self.now,
        )

    def create_class(self, subject=None):
        return Classes.objects.create(
            tutor=self.tutor,
            student=self.student,
            subject=subject or self.subject,
            start_date=self.today,
            end_date=self.today + timedelta(days=30),
            tuition_fee=Decimal("250000.00"),
            status="active",
            created_at=self.now,
            updated_at=self.now,
        )

    def json_request(self, method, path, payload=None):
        return getattr(self.client, method)(
            path,
            data=json.dumps(payload or {}),
            content_type="application/json",
        )

    def response_json(self, response):
        return json.loads(response.content.decode("utf-8"))

    def assert_status(self, response, status_code):
        self.assertEqual(response.status_code, status_code, self.response_json(response))

    def test_index_lists_resources_and_workflows(self):
        response = self.client.get(self.base_url)

        self.assert_status(response, 200)
        data = self.response_json(response)
        self.assertIn("subjects", data["resources"])
        self.assertIn("tutor-subjects", data["resources"])
        self.assertIn("student-posts/<post_id>/matches/", data["workflows"])

    def test_standard_resource_apis_support_crud(self):
        cases = [
            {
                "resource": "subject-categories",
                "payload": {
                    "name": f"Languages {self.slug}",
                    "description": "Language subjects",
                },
                "patch": {"description": "Updated category"},
                "field": "description",
                "value": "Updated category",
            },
            {
                "resource": "subjects",
                "payload": {
                    "category_id": self.category.id,
                    "name": f"Physics {self.slug}",
                    "description": "Physics subject",
                },
                "patch": {"description": "Updated subject"},
                "field": "description",
                "value": "Updated subject",
            },
            {
                "resource": "student-posts",
                "payload": {
                    "student_id": self.student.id,
                    "subject_id": self.subject.id,
                    "title": f"Need chemistry tutor {self.slug}",
                    "description": "Need support twice a week",
                    "preferred_fee": "240000.00",
                },
                "patch": {"title": "Updated student post"},
                "field": "title",
                "value": "Updated student post",
            },
            {
                "resource": "tutor-applications",
                "payload": {
                    "post_id": self.create_student_post("Application target").id,
                    "tutor_id": self.other_tutor.id,
                },
                "patch": {"status": "shortlisted"},
                "field": "status",
                "value": "shortlisted",
            },
            {
                "resource": "classes",
                "payload": {
                    "tutor_id": self.tutor.id,
                    "student_id": self.student.id,
                    "subject_id": self.subject.id,
                    "start_date": str(self.today + timedelta(days=1)),
                    "tuition_fee": "230000.00",
                },
                "patch": {"status": "paused"},
                "field": "status",
                "value": "paused",
            },
            {
                "resource": "schedules",
                "payload": {
                    "class_id": self.create_class().id,
                    "tutor_id": self.tutor.id,
                    "student_id": self.student.id,
                    "start_time": (self.now + timedelta(days=1)).isoformat(),
                    "end_time": (self.now + timedelta(days=1, hours=2)).isoformat(),
                    "note": "Initial lesson",
                },
                "patch": {"note": "Updated schedule"},
                "field": "note",
                "value": "Updated schedule",
            },
            {
                "resource": "reviews",
                "payload": {
                    "tutor_id": self.tutor.id,
                    "student_id": self.student.id,
                    "class_id": self.create_class().id,
                    "rating": 4,
                    "content": "Good lesson",
                },
                "patch": {"content": "Updated review"},
                "field": "content",
                "value": "Updated review",
            },
            {
                "resource": "review-reports",
                "payload": {
                    "review_id": self.review.id,
                    "reporter_id": self.student_user.id,
                    "reason": "Inappropriate wording",
                },
                "patch": {"status": "resolved"},
                "field": "status",
                "value": "resolved",
            },
            {
                "resource": "ai-matching-logs",
                "payload": {
                    "tutor_id": self.tutor.id,
                    "student_id": self.student.id,
                    "post_id": self.post.id,
                    "matching_score": "91.25",
                    "distance_score": "88.00",
                    "fee_score": "95.00",
                    "rating_score": "90.00",
                    "response_score": "92.00",
                },
                "patch": {"response_score": "88.00"},
                "field": "response_score",
                "value": "88.00",
            },
        ]

        for case in cases:
            with self.subTest(resource=case["resource"]):
                collection_path = f"{self.base_url}{case['resource']}/"

                create_response = self.json_request("post", collection_path, case["payload"])
                self.assert_status(create_response, 201)
                created = self.response_json(create_response)
                detail_path = f"{collection_path}{created['id']}/"

                list_response = self.client.get(collection_path)
                self.assert_status(list_response, 200)
                self.assertGreaterEqual(self.response_json(list_response)["count"], 1)

                detail_response = self.client.get(detail_path)
                self.assert_status(detail_response, 200)
                self.assertEqual(self.response_json(detail_response)["id"], created["id"])

                patch_response = self.json_request("patch", detail_path, case["patch"])
                self.assert_status(patch_response, 200)
                self.assertEqual(self.response_json(patch_response)[case["field"]], case["value"])

                delete_response = self.client.delete(detail_path)
                self.assert_status(delete_response, 200)
                self.assertTrue(self.response_json(delete_response)["deleted"])

                missing_response = self.client.get(detail_path)
                self.assert_status(missing_response, 404)

    def test_collection_filters_search_ordering_and_pagination(self):
        subject = self.create_subject("Biology", self.category)

        response = self.client.get(
            f"{self.base_url}subjects/",
            {
                "category_id": self.category.id,
                "search": subject.name.split()[0],
                "ordering": "-name",
                "limit": 1,
                "offset": 0,
            },
        )

        self.assert_status(response, 200)
        data = self.response_json(response)
        self.assertGreaterEqual(data["count"], 1)
        self.assertLessEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["category_id"], self.category.id)

    def test_tutor_subject_apis_support_composite_key_crud(self):
        subject = self.create_subject("English", self.category)
        collection_path = f"{self.base_url}tutor-subjects/"
        detail_path = f"{collection_path}{self.other_tutor.id}/{subject.id}/"

        create_response = self.json_request(
            "post",
            collection_path,
            {"tutor_id": self.other_tutor.id, "subject_id": subject.id},
        )
        self.assert_status(create_response, 201)
        self.assertEqual(self.response_json(create_response)["tutor_id"], self.other_tutor.id)

        list_response = self.client.get(collection_path, {"tutor_id": self.other_tutor.id})
        self.assert_status(list_response, 200)
        self.assertEqual(self.response_json(list_response)["count"], 1)

        detail_response = self.client.get(detail_path)
        self.assert_status(detail_response, 200)
        self.assertEqual(self.response_json(detail_response)["subject_id"], subject.id)

        delete_response = self.client.delete(detail_path)
        self.assert_status(delete_response, 200)
        self.assertTrue(self.response_json(delete_response)["deleted"])

        missing_response = self.client.get(detail_path)
        self.assert_status(missing_response, 404)

    def test_apply_to_post_api_creates_application_and_handles_duplicates(self):
        post = self.create_student_post("Apply workflow")
        path = f"{self.base_url}student-posts/{post.id}/apply/"

        response = self.json_request("post", path, {"tutor_id": self.tutor.id})
        self.assert_status(response, 201)
        self.assertEqual(self.response_json(response)["status"], "pending")

        duplicate_response = self.json_request("post", path, {"tutor_id": self.tutor.id})
        self.assert_status(duplicate_response, 409)

        missing_tutor_response = self.json_request("post", path, {})
        self.assert_status(missing_tutor_response, 400)

    def test_create_class_from_application_api_accepts_application_and_matches_post(self):
        post = self.create_student_post("Create class workflow")
        application = TutorApplications.objects.create(
            post=post,
            tutor=self.tutor,
            status="pending",
            applied_at=self.now,
        )

        response = self.json_request(
            "post",
            f"{self.base_url}tutor-applications/{application.id}/create-class/",
            {
                "start_date": str(self.today + timedelta(days=3)),
                "tuition_fee": "260000.00",
            },
        )

        self.assert_status(response, 201)
        data = self.response_json(response)
        self.assertEqual(data["application"]["status"], "accepted")
        self.assertEqual(data["class"]["student_id"], self.student.id)

        post.refresh_from_db()
        application.refresh_from_db()
        self.assertEqual(post.status, "matched")
        self.assertEqual(application.status, "accepted")

    def test_match_tutors_for_post_api_returns_scores_and_can_persist_logs(self):
        response = self.client.get(f"{self.base_url}student-posts/{self.post.id}/matches/", {"persist": "true"})

        self.assert_status(response, 200)
        data = self.response_json(response)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["tutor"]["id"], self.tutor.id)
        self.assertIn("matching_score", data["results"][0]["scores"])
        self.assertEqual(AiMatchingLogs.objects.filter(post=self.post, tutor=self.tutor).count(), 1)

    def test_tutor_review_summary_api_returns_rating_aggregate(self):
        response = self.client.get(f"{self.base_url}tutors/{self.tutor.id}/review-summary/")

        self.assert_status(response, 200)
        data = self.response_json(response)
        self.assertEqual(data["tutor"], self.tutor.id)
        self.assertEqual(data["rating_avg"], "5.00")
        self.assertEqual(data["total_reviews"], 1)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            f"{self.base_url}subjects/",
            data="{invalid",
            content_type="application/json",
        )

        self.assert_status(response, 400)
        self.assertIn("Invalid JSON body", self.response_json(response)["error"])
