"""/awards/: read-only list of awards with rounds, criteria and the current form (public)."""
from rest_framework import permissions, viewsets

from apps.awards.models import Award

from .serializers import AwardSerializer


class AwardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AwardSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    filterset_fields = ["status", "sector"]
    search_fields = ["name", "summary"]
    ordering_fields = ["name", "closes_on"]

    def get_queryset(self):
        return Award.objects.prefetch_related("rounds", "criteria", "form_versions")
