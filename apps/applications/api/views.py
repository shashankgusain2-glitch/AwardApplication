"""
/applications/  applicants: their own only; staff and leaders: all.
Judges don't use this endpoint: they see reports through their assignments,
where blind judging is applied (/judge/my-assignments/).
"""
import django_filters
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.accounts.api.serializers import UserSerializer
from apps.applications import files, services
from apps.applications.models import Application
from apps.assignments.services import eligible_judges
from apps.core.api.permissions import HasRole, IsApplicant, IsStaffOrLeader

from .serializers import (
    ApplicationCreateSerializer,
    ApplicationSerializer,
    ApplicationUpdateSerializer,
    AttachmentSerializer,
    AttachmentUploadSerializer,
    DecideSerializer,
    ReasonSerializer,
    ReevaluationDecisionSerializer,
    StatusChangeSerializer,
)


class ApplicantStaffOrLeader(HasRole):
    roles = ("applicant", "staff", "manager", "leader")


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
        if self.action in (("create", "update", "partial_update", "destroy", "submit", "request_edit", "attachments",
                           "request_reevaluation")):
            return [IsApplicant()]
        if self.action in ("decide_edit", "decide_reevaluation", "change_status", "eligible_judges"):
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

    @extend_schema(request=ReasonSerializer, responses=ApplicationSerializer)
    @action(detail=True, methods=["post"], url_path="request-reevaluation")
    def request_reevaluation(self, request, pk=None):
        """Applicant: once the result is out, ask once for fresh judges to score it again."""
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = services.request_reevaluation(self.get_object(), by=request.user, **serializer.validated_data)
        return Response(ApplicationSerializer(app).data)

    @extend_schema(request=ReevaluationDecisionSerializer, responses=ApplicationSerializer)
    @action(detail=True, methods=["post"], url_path="decide-reevaluation")
    def decide_reevaluation(self, request, pk=None):
        """Staff: confirm (fresh judges score it again) or refuse a re-evaluation request."""
        serializer = ReevaluationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = services.decide_reevaluation(self.get_object(), by=request.user, **serializer.validated_data)
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

    @extend_schema(request={"multipart/form-data": AttachmentUploadSerializer}, responses=AttachmentSerializer)
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
    def attachments(self, request, pk=None):
        """Upload the file for one file question (multipart: question_key, file). Replaces an earlier one."""
        serializer = AttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = files.attach(self.get_object(), by=request.user,
                                  question_key=serializer.validated_data["question_key"],
                                  upload=serializer.validated_data["file"])
        return Response(AttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)


class AttachmentDownloadView(generics.GenericAPIView):
    """
    GET /attachments/{id}/download/: the file, for the applicant who owns it, staff, leaders,
    and judges assigned to that report (blind rounds get a neutral file name). Anyone else: 404.
    """
    queryset_model = files.Attachment

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        return files.visible_to(self.request.user)

    @extend_schema(responses={(200, "application/octet-stream"): bytes})
    def get(self, request, pk):
        attachment = get_object_or_404(self.get_queryset(), pk=pk)
        return FileResponse(attachment.file.open("rb"), as_attachment=True,
                            filename=files.download_name(attachment, request.user),
                            content_type=attachment.content_type)
