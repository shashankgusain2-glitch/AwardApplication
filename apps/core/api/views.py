from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


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
