import json
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from django.http import Http404, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from apps.accounts.models import TutorProfiles
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


DEFAULT_LIMIT = 50
MAX_LIMIT = 100

DEFAULT_VALUES = {
    SubjectCategories: {"status": "ACTIVE"},
    Subjects: {"status": "ACTIVE"},
    StudentPosts: {"status": "OPEN", "moderation_status": "PENDING"},
    TutorApplications: {"status": "PENDING"},
    Classes: {"status": "ACTIVE"},
    Schedules: {"status": "UPCOMING"},
    Reviews: {"status": "VISIBLE"},
    ReviewReports: {"status": "PENDING"},
}

RESOURCE_CONFIGS = {
    "subject-categories": {
        "model": SubjectCategories,
        "search": ("name", "description"),
        "ordering": "name",
    },
    "subjects": {
        "model": Subjects,
        "search": ("name", "description"),
        "select_related": ("category",),
        "ordering": "name",
    },
    "student-posts": {
        "model": StudentPosts,
        "search": ("title", "description", "address", "schedule_note"),
        "select_related": ("student", "subject"),
        "ordering": "-created_at",
    },
    "tutor-applications": {
        "model": TutorApplications,
        "select_related": ("post", "tutor"),
        "ordering": "-applied_at",
    },
    "classes": {
        "model": Classes,
        "select_related": ("tutor", "student", "subject"),
        "ordering": "-created_at",
    },
    "schedules": {
        "model": Schedules,
        "select_related": ("class_field", "tutor", "student"),
        "ordering": "start_time",
    },
    "reviews": {
        "model": Reviews,
        "search": ("content",),
        "select_related": ("tutor", "student", "class_field"),
        "ordering": "-created_at",
    },
    "review-reports": {
        "model": ReviewReports,
        "search": ("reason",),
        "select_related": ("review", "reporter"),
        "ordering": "-created_at",
    },
    "ai-matching-logs": {
        "model": AiMatchingLogs,
        "select_related": ("tutor", "student", "post"),
        "ordering": "-created_at",
    },
}


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


def error_response(message, status=400, details=None):
    payload = {"error": message}
    if details is not None:
        payload["details"] = details
    return json_response(payload, status=status)


def parse_json_body(request):
    if not request.body:
        return {}
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON body: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object.")
    return payload


def to_json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [to_json_value(item) for item in value]
    if isinstance(value, list):
        return [to_json_value(item) for item in value]
    return value


def serialize_instance(instance):
    data = {}
    for field in instance._meta.fields:
        if field.is_relation and (field.many_to_one or field.one_to_one):
            value = getattr(instance, field.attname)
            data[field.name] = to_json_value(value)
            if field.attname != field.name:
                data[field.attname] = to_json_value(value)
            if field.db_column and field.db_column not in data:
                data[field.db_column] = to_json_value(value)
        else:
            data[field.name] = to_json_value(getattr(instance, field.name))

    if "id" not in data:
        data["pk"] = to_json_value(instance.pk)
    return data


def get_resource_config(resource):
    config = RESOURCE_CONFIGS.get(resource)
    if config is None:
        raise KeyError(resource)
    return config


def payload_field_map(model):
    fields = {}
    for field in model._meta.fields:
        if field.primary_key and not (field.is_relation and field.many_to_one):
            continue

        if field.is_relation and (field.many_to_one or field.one_to_one):
            fields[field.name] = field.attname
            fields[field.attname] = field.attname
            if field.db_column:
                fields[field.db_column] = field.attname
        else:
            fields[field.name] = field.name
            if field.db_column and field.db_column != field.name:
                fields[field.db_column] = field.name
    return fields


def normalize_payload(model, payload):
    field_map = payload_field_map(model)
    attrs = {}
    unknown = []

    for key, value in payload.items():
        target = field_map.get(key)
        if target is None:
            unknown.append(key)
            continue
        attrs[target] = value

    if unknown:
        raise ValueError(f"Unknown field(s): {', '.join(sorted(unknown))}")
    return attrs


def apply_defaults(instance, creating):
    defaults = DEFAULT_VALUES.get(type(instance), {})
    for field_name, value in defaults.items():
        if getattr(instance, field_name, None) in (None, ""):
            setattr(instance, field_name, value)

    now = timezone.now()
    if creating and hasattr(instance, "created_at") and getattr(instance, "created_at") is None:
        instance.created_at = now
    if creating and hasattr(instance, "applied_at") and getattr(instance, "applied_at") is None:
        instance.applied_at = now
    if hasattr(instance, "updated_at"):
        instance.updated_at = now


def validation_details(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return exc.messages


def save_new_instance(model, payload):
    attrs = normalize_payload(model, payload)
    instance = model(**attrs)
    apply_defaults(instance, creating=True)
    instance.full_clean()
    instance.save()
    return instance


def update_instance(instance, payload):
    attrs = normalize_payload(type(instance), payload)
    for field_name, value in attrs.items():
        setattr(instance, field_name, value)
    apply_defaults(instance, creating=False)
    instance.full_clean()
    instance.save()
    return instance


def base_queryset(config):
    queryset = config["model"].objects.all()
    select_related = config.get("select_related", ())
    if select_related:
        queryset = queryset.select_related(*select_related)
    return queryset


def resolve_filter_field(model, param):
    field_map = payload_field_map(model)
    if param in field_map:
        return field_map[param]
    try:
        model._meta.get_field(param)
    except FieldDoesNotExist:
        return None
    return param


def apply_filters(queryset, model, query_params):
    ignored = {"limit", "offset", "ordering", "search"}
    for key, value in query_params.items():
        if key in ignored or value == "":
            continue

        filter_field = resolve_filter_field(model, key)
        if filter_field is None:
            continue
        queryset = queryset.filter(**{filter_field: value})
    return queryset


def apply_search(queryset, config, term):
    search_fields = config.get("search", ())
    if not term or not search_fields:
        return queryset

    query = Q()
    for field_name in search_fields:
        query |= Q(**{f"{field_name}__icontains": term})
    return queryset.filter(query)


def ordering_fields(model):
    fields = set()
    for field in model._meta.fields:
        fields.add(field.name)
        if field.is_relation and (field.many_to_one or field.one_to_one):
            fields.add(field.attname)
            if field.db_column:
                fields.add(field.db_column)
    return fields


def apply_ordering(queryset, config, request):
    model = config["model"]
    requested = request.GET.get("ordering") or config.get("ordering")
    if not requested:
        return queryset

    allowed = ordering_fields(model)
    ordering = []
    for field in requested.split(","):
        field = field.strip()
        bare_field = field[1:] if field.startswith("-") else field
        mapped_field = payload_field_map(model).get(bare_field, bare_field)
        if mapped_field in allowed:
            prefix = "-" if field.startswith("-") else ""
            ordering.append(f"{prefix}{mapped_field}")
    if ordering:
        return queryset.order_by(*ordering)
    return queryset


def int_query_param(request, name, default, minimum=0, maximum=None):
    raw_value = request.GET.get(name)
    if raw_value in (None, ""):
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


def refresh_tutor_rating(tutor_id):
    queryset = Reviews.objects.filter(tutor_id=tutor_id).exclude(status__in=["deleted", "hidden", "rejected"])
    summary = queryset.aggregate(avg_rating=Avg("rating"), total_reviews=Count("id"))
    avg_rating = summary["avg_rating"]

    TutorProfiles.objects.filter(id=tutor_id).update(
        rating_avg=round_decimal(avg_rating) if avg_rating is not None else None,
        total_reviews=summary["total_reviews"],
    )


def after_save(instance):
    if isinstance(instance, Reviews):
        refresh_tutor_rating(instance.tutor_id)


def after_delete(instance):
    if isinstance(instance, Reviews):
        refresh_tutor_rating(instance.tutor_id)


@csrf_exempt
def api_index(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    return json_response(
        {
            "resources": sorted(RESOURCE_CONFIGS.keys()) + ["tutor-subjects"],
            "workflows": [
                "student-posts/<post_id>/apply/",
                "student-posts/<post_id>/matches/",
                "tutor-applications/<application_id>/create-class/",
                "tutors/<tutor_id>/review-summary/",
            ],
        }
    )


@csrf_exempt
def resource_collection(request, resource):
    try:
        config = get_resource_config(resource)
    except KeyError:
        return error_response("Unknown tutoring resource.", status=404)

    model = config["model"]
    if request.method == "GET":
        queryset = base_queryset(config)
        queryset = apply_filters(queryset, model, request.GET)
        queryset = apply_search(queryset, config, request.GET.get("search"))
        queryset = apply_ordering(queryset, config, request)

        limit = int_query_param(request, "limit", DEFAULT_LIMIT, minimum=1, maximum=MAX_LIMIT)
        offset = int_query_param(request, "offset", 0, minimum=0)
        count = queryset.count()
        results = [serialize_instance(item) for item in queryset[offset : offset + limit]]
        return json_response({"count": count, "limit": limit, "offset": offset, "results": results})

    if request.method == "POST":
        try:
            payload = parse_json_body(request)
            with transaction.atomic():
                instance = save_new_instance(model, payload)
                after_save(instance)
        except ValueError as exc:
            return error_response(str(exc))
        except ValidationError as exc:
            return error_response("Validation failed.", details=validation_details(exc))
        except IntegrityError as exc:
            return error_response("Database constraint failed.", status=409, details=str(exc))
        return json_response(serialize_instance(instance), status=201)

    return HttpResponseNotAllowed(["GET", "POST"])


@csrf_exempt
def resource_detail(request, resource, pk):
    try:
        config = get_resource_config(resource)
    except KeyError:
        return error_response("Unknown tutoring resource.", status=404)

    try:
        instance = get_object_or_404(base_queryset(config), pk=pk)
    except Http404:
        return error_response("Resource not found.", status=404)

    if request.method == "GET":
        return json_response(serialize_instance(instance))

    if request.method in {"PUT", "PATCH"}:
        try:
            payload = parse_json_body(request)
            with transaction.atomic():
                instance = update_instance(instance, payload)
                after_save(instance)
        except ValueError as exc:
            return error_response(str(exc))
        except ValidationError as exc:
            return error_response("Validation failed.", details=validation_details(exc))
        except IntegrityError as exc:
            return error_response("Database constraint failed.", status=409, details=str(exc))
        return json_response(serialize_instance(instance))

    if request.method == "DELETE":
        with transaction.atomic():
            deleted_instance = instance
            instance.delete()
            after_delete(deleted_instance)
        return json_response({"deleted": True})

    return HttpResponseNotAllowed(["GET", "PUT", "PATCH", "DELETE"])


@csrf_exempt
def tutor_subjects_collection(request):
    config = {
        "model": TutorSubjects,
        "select_related": ("tutor", "subject"),
        "ordering": "-created_at",
    }

    if request.method == "GET":
        queryset = base_queryset(config)
        queryset = apply_filters(queryset, TutorSubjects, request.GET)
        queryset = apply_ordering(queryset, config, request)
        limit = int_query_param(request, "limit", DEFAULT_LIMIT, minimum=1, maximum=MAX_LIMIT)
        offset = int_query_param(request, "offset", 0, minimum=0)
        count = queryset.count()
        results = [serialize_instance(item) for item in queryset[offset : offset + limit]]
        return json_response({"count": count, "limit": limit, "offset": offset, "results": results})

    if request.method == "POST":
        try:
            payload = parse_json_body(request)
            with transaction.atomic():
                instance = save_new_instance(TutorSubjects, payload)
        except ValueError as exc:
            return error_response(str(exc))
        except ValidationError as exc:
            return error_response("Validation failed.", details=validation_details(exc))
        except IntegrityError as exc:
            return error_response("Database constraint failed.", status=409, details=str(exc))
        return json_response(serialize_instance(instance), status=201)

    return HttpResponseNotAllowed(["GET", "POST"])


@csrf_exempt
def tutor_subject_detail(request, tutor_id, subject_id):
    try:
        instance = get_object_or_404(TutorSubjects, tutor_id=tutor_id, subject_id=subject_id)
    except Http404:
        return error_response("Tutor subject not found.", status=404)

    if request.method == "GET":
        return json_response(serialize_instance(instance))

    if request.method == "DELETE":
        instance.delete()
        return json_response({"deleted": True})

    return HttpResponseNotAllowed(["GET", "DELETE"])


@csrf_exempt
def apply_to_post(request, post_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        payload = parse_json_body(request)
        tutor_id = payload.get("tutor") or payload.get("tutor_id")
        if not tutor_id:
            return error_response("Field 'tutor' or 'tutor_id' is required.")

        get_object_or_404(StudentPosts, pk=post_id)
        with transaction.atomic():
            application = save_new_instance(
                TutorApplications,
                {
                    "post_id": post_id,
                    "tutor_id": tutor_id,
                    "status": payload.get("status", "PENDING"),
                },
            )
    except ValueError as exc:
        return error_response(str(exc))
    except Http404:
        return error_response("Student post not found.", status=404)
    except ValidationError as exc:
        return error_response("Validation failed.", details=validation_details(exc))
    except IntegrityError as exc:
        return error_response("Tutor already applied to this post.", status=409, details=str(exc))

    return json_response(serialize_instance(application), status=201)


@csrf_exempt
def create_class_from_application(request, application_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        payload = parse_json_body(request)
        application = get_object_or_404(TutorApplications.objects.select_related("post"), pk=application_id)

        class_payload = {
            "tutor_id": application.tutor_id,
            "student_id": application.post.student_id,
            "subject_id": payload.get("subject") or payload.get("subject_id") or application.post.subject_id,
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "tuition_fee": payload.get("tuition_fee") or application.post.preferred_fee,
            "status": payload.get("status", "ACTIVE"),
        }

        if not class_payload["start_date"]:
            return error_response("Field 'start_date' is required.")
        if class_payload["tuition_fee"] is None:
            return error_response("Field 'tuition_fee' is required when the post has no preferred_fee.")

        with transaction.atomic():
            new_class = save_new_instance(Classes, class_payload)
            application.status = "ACCEPTED"
            apply_defaults(application, creating=False)
            application.save()
            StudentPosts.objects.filter(id=application.post_id).update(status="MATCHED", updated_at=timezone.now())
    except ValueError as exc:
        return error_response(str(exc))
    except Http404:
        return error_response("Tutor application not found.", status=404)
    except ValidationError as exc:
        return error_response("Validation failed.", details=validation_details(exc))
    except IntegrityError as exc:
        return error_response("Database constraint failed.", status=409, details=str(exc))

    return json_response(
        {
            "class": serialize_instance(new_class),
            "application": serialize_instance(application),
        },
        status=201,
    )


@csrf_exempt
def match_tutors_for_post(request, post_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    try:
        post = get_object_or_404(StudentPosts.objects.select_related("student", "subject"), pk=post_id)
    except Http404:
        return error_response("Student post not found.", status=404)
    limit = int_query_param(request, "limit", 10, minimum=1, maximum=MAX_LIMIT)
    persist = request.GET.get("persist", "").lower() in {"1", "true", "yes"}

    tutor_ids = TutorSubjects.objects.filter(subject_id=post.subject_id).values_list("tutor_id", flat=True)
    tutors = TutorProfiles.objects.select_related("user").filter(id__in=tutor_ids)

    matches = []
    for tutor in tutors:
        scores = calculate_match_scores(post, tutor)
        matches.append(
            {
                "tutor": serialize_tutor_profile(tutor),
                "scores": scores,
            }
        )

    matches.sort(key=lambda item: Decimal(item["scores"]["matching_score"]), reverse=True)
    matches = matches[:limit]

    if persist:
        with transaction.atomic():
            for item in matches:
                tutor_id = item["tutor"]["id"]
                scores = item["scores"]
                AiMatchingLogs.objects.create(
                    tutor_id=tutor_id,
                    student_id=post.student_id,
                    post_id=post.id,
                    matching_score=scores["matching_score"],
                    distance_score=scores["distance_score"],
                    fee_score=scores["fee_score"],
                    rating_score=scores["rating_score"],
                    response_score=scores["response_score"],
                    created_at=timezone.now(),
                )

    return json_response({"post": serialize_instance(post), "count": len(matches), "results": matches})


@csrf_exempt
def tutor_review_summary(request, tutor_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    try:
        get_object_or_404(TutorProfiles, pk=tutor_id)
    except Http404:
        return error_response("Tutor not found.", status=404)
    queryset = Reviews.objects.filter(tutor_id=tutor_id).exclude(status__in=["deleted", "hidden", "rejected"])
    summary = queryset.aggregate(avg_rating=Avg("rating"), total_reviews=Count("id"))
    return json_response(
        {
            "tutor": tutor_id,
            "rating_avg": to_json_value(round_decimal(summary["avg_rating"]) if summary["avg_rating"] is not None else None),
            "total_reviews": summary["total_reviews"],
        }
    )


def serialize_tutor_profile(tutor):
    user = getattr(tutor, "user", None)
    return {
        "id": tutor.id,
        "user_id": tutor.user_id,
        "full_name": getattr(user, "full_name", None),
        "avatar_url": getattr(user, "avatar_url", None),
        "address": getattr(user, "address", None),
        "latitude": to_json_value(getattr(user, "latitude", None)),
        "longitude": to_json_value(getattr(user, "longitude", None)),
        "experience_years": tutor.experience_years,
        "teaching_fee": to_json_value(tutor.teaching_fee),
        "rating_avg": to_json_value(tutor.rating_avg),
        "total_reviews": tutor.total_reviews,
        "response_rate": to_json_value(tutor.response_rate),
        "trusted_badge": tutor.trusted_badge,
        "education_level": tutor.education_level,
        "university": tutor.university,
        "major": tutor.major,
        "is_kyc_verified": tutor.is_kyc_verified,
    }


def calculate_match_scores(post, tutor):
    fee_score = calculate_fee_score(post.preferred_fee, tutor.teaching_fee)
    rating_score = calculate_rating_score(tutor.rating_avg)
    response_score = clamp_decimal(tutor.response_rate if tutor.response_rate is not None else Decimal("50.00"))
    distance_score = calculate_distance_score(post, tutor)

    matching_score = (
        Decimal("100.00") * Decimal("0.35")
        + distance_score * Decimal("0.20")
        + fee_score * Decimal("0.20")
        + rating_score * Decimal("0.15")
        + response_score * Decimal("0.10")
    )

    return {
        "matching_score": str(round_decimal(matching_score)),
        "distance_score": str(round_decimal(distance_score)),
        "fee_score": str(round_decimal(fee_score)),
        "rating_score": str(round_decimal(rating_score)),
        "response_score": str(round_decimal(response_score)),
    }


def calculate_fee_score(preferred_fee, teaching_fee):
    if preferred_fee is None or teaching_fee is None:
        return Decimal("50.00")

    preferred_fee = Decimal(str(preferred_fee))
    teaching_fee = Decimal(str(teaching_fee))
    if preferred_fee == 0:
        return Decimal("50.00")
    if teaching_fee <= preferred_fee:
        return Decimal("100.00")

    over_budget_ratio = (teaching_fee - preferred_fee) / preferred_fee
    return clamp_decimal(Decimal("100.00") - over_budget_ratio * Decimal("100.00"))


def calculate_rating_score(rating_avg):
    if rating_avg is None:
        return Decimal("50.00")
    return clamp_decimal(Decimal(str(rating_avg)) / Decimal("5.00") * Decimal("100.00"))


def calculate_distance_score(post, tutor):
    user = getattr(tutor, "user", None)
    coordinates = (
        post.latitude,
        post.longitude,
        getattr(user, "latitude", None),
        getattr(user, "longitude", None),
    )
    if any(value is None for value in coordinates):
        return Decimal("50.00")

    distance_km = haversine_km(
        Decimal(str(post.latitude)),
        Decimal(str(post.longitude)),
        Decimal(str(user.latitude)),
        Decimal(str(user.longitude)),
    )
    return clamp_decimal(Decimal("100.00") - Decimal(str(distance_km)) * Decimal("5.00"))


def haversine_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371
    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(value))


def clamp_decimal(value, minimum=Decimal("0.00"), maximum=Decimal("100.00")):
    value = Decimal(str(value))
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def round_decimal(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
