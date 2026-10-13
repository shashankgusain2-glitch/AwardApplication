"""
/applications/  applicants: their own only; staff and leaders: all.
Judges don't use this endpoint: they see reports through their assignments,
where blind judging is applied (/judge/my-assignments/).
"""
import django_filters
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.api.serializers import UserSerializer
from apps.applications import services
from apps.applications.models import Application
from apps.assignments.services import eligible_judges
from apps.core.api.permissions import HasRole, IsApplicant, IsStaffOrLeader

from .serializers import (
    ApplicationCreateSerializer,
    ApplicationSerializer,
    ApplicationUpdateSerializer,
    DecideSerializer,
    ReasonSerializer,
    StatusChangeSerializer,
)


class ApplicantStaffOrLeader(HasRole):
    roles = ("applicant", "staff", "leader")


class ApplicationFilter(django_filters.FilterSet):
    award = django_filters.CharFilter(field_name="award__slug")
    submitted_after = django_filters.DateTimeFilter(field_name="submitted_at", lookup_expr="gte")

    class Meta:
        model = Application
        fields = ["status", "award", "edit_requested"]


class ApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                         mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset_model = Application
    serializer_class = ApplicationSerializer
    filterset_class = ApplicationFilter
    search_fields = ["reference", "title", "applicant__email"]
    ordering_fields = ["created_at", "submitted_at", "status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        # Object-level security: an applicant only ever gets their own rows.
        return services.visible_to(self.request.user).prefetch_related("attachments")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "submit", "request_edit"):
            return [IsApplicant()]
        if self.action in ("decide_edit", "change_status", "eligible_judges"):
            return [IsStaffOrLeader()]
        return [ApplicantStaffOrLeader()]

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationCreateSerializer
        if self.action in ("update", "partial_update"):
            return ApplicationUpdateSerializer
        return ApplicationSerializer

    def create(self, request, *args, **kwargs):
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = services.create_draft(applicant=request.user, **serializer.validated_data)
        return Response(ApplicationSerializer(app).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        app = self.get_object()
        serializer = ApplicationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = services.update(app, by=request.user, **serializer.validated_data)
        return Response(ApplicationSerializer(app).data)

    def perform_destroy(self, instance):
        if instance.status != Application.Status.DRAFT:
            from apps.core.services import BusinessRuleError
            raise BusinessRuleError("Only drafts can be deleted.")
        instance.delete()   # soft delete

    @extend_schema(request=None, responses=ApplicationSerializer)
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return Response(ApplicationSerializer(services.submit(self.get_object(), by=request.user)).data)

    @extend_schema(request=ReasonSerializer, responses=ApplicationSerializer)
    @action(detail=True, methods=["post"], url_path="request-edit")
    def request_edit(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = services.request_edit(self.get_object(), by=request.user, **serializer.validated_data)
        return Response(ApplicationSerializer(app).data)

    @extend_schema(request=DecideSerializer, responses=ApplicationSerializer)
    @action(detail=True, methods=["post"], url_path="decide-edit")
    def decide_edit(self, request, pk=None):
        serializer = DecideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = services.decide_edit(self.get_object(), by=request.user, **serializer.validated_data)
        return Response(ApplicationSerializer(app).data)

    @extend_schema(request=StatusChangeSerializer, responses=ApplicationSerializer)
    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        serializer = StatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = services.change_status(self.get_object(), by=request.user,
                                     new_status=serializer.validated_data["status"],
                                     note=serializer.validated_data["note"])
        return Response(ApplicationSerializer(app).data)

    @extend_schema(responses=UserSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="eligible-judges")
    def eligible_judges(self, request, pk=None):
        """Judges staff may assign: on the panel, no conflict, under their limit; best first."""
        try:
            round_number = int(request.query_params.get("round", 1))
        except ValueError:
            raise ValidationError({"round": ["Round must be a whole number."]}) from None
        return Response(UserSerializer(eligible_judges(self.get_object(), round_number), many=True).data)
