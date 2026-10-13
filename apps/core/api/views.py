from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import ApplicantProfile, User
from apps.applications.models import Application
from apps.assignments.models import JudgeAssignment
from apps.awards.models import Award, AwardRound
from apps.core import overview
from apps.evaluations.models import Evaluation


class HealthView(APIView):
    """GET /api/v1/health/: is the app up and can it reach the database?"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(responses={200: dict, 503: dict})
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return Response({"status": "ok", "database": "ok"})
        except Exception:   # noqa: BLE001 - report any database failure as unhealthy
            return Response({"success": False, "data": {"status": "error", "database": "unreachable"},
                             "message": "Database unreachable.", "errors": None},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)


class DashboardSummaryView(APIView):
    """GET /api/v1/dashboard/summary/: counts by status for the logged-in user's role (only what they may see)."""

    @extend_schema(responses=dict)
    def get(self, request):
        return Response(overview.summary_for(request.user))


class LookupsView(APIView):
    """GET /api/v1/lookups/: the codes and labels the screens need for drop-downs and badges."""

    @extend_schema(responses=dict)
    def get(self, request):
        def pairs(choices):
            return [{"value": value, "label": label} for value, label in choices]
        return Response({
            "roles": pairs(User.Role.choices),
            "application_statuses": pairs(Application.Status.choices),
            "assignment_statuses": pairs(JudgeAssignment.Status.choices),
            "evaluation_statuses": pairs(Evaluation.Status.choices),
            "verification_statuses": pairs(ApplicantProfile.Verification.choices),
            "round_kinds": pairs(AwardRound.Kind.choices),
            "applicant_types": pairs(Award.ApplicantType.choices),
            "award_statuses": pairs(Award.Status.choices),
            "score_range": {"min": 1, "max": 10},
        })
