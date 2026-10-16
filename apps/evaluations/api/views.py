"""
/evaluations/            judges create and update evaluations for their OWN assignments only;
                         staff and leaders read all
/score-change-requests/  staff and leaders allow or refuse score changes
"""
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.assignments.models import JudgeAssignment
from apps.core.api.permissions import HasRole, IsJudge, IsStaffOrLeader, IsStaffOrManager
from apps.evaluations import services
from apps.evaluations.models import Evaluation, ScoreChangeRequest

from .serializers import (
    ChangeDecisionSerializer,
    ChangeReasonSerializer,
    ChangeRequestSerializer,
    ChangeScoresSerializer,
    EvaluationSerializer,
    EvaluationUpdateSerializer,
    EvaluationWriteSerializer,
)


class JudgeStaffOrLeader(HasRole):
    roles = ("judge", "staff", "manager", "leader")


class EvaluationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                        mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset_model = Evaluation
    filterset_fields = ["status", "assignment"]
    ordering_fields = ["submitted_at", "total_score", "created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        return services.visible_to(self.request.user)

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "request_change", "change_scores"):
            return [IsJudge()]
        return [JudgeStaffOrLeader()]

    def get_serializer_class(self):
        return {"create": EvaluationWriteSerializer, "update": EvaluationUpdateSerializer,
                "partial_update": EvaluationUpdateSerializer}.get(self.action, EvaluationSerializer)

    def create(self, request, *args, **kwargs):
        serializer = EvaluationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Never trust the id alone: look it up among THIS judge's assignments.
        assignment = get_object_or_404(JudgeAssignment, pk=data["assignment"], judge=request.user)
        evaluation = services.save(assignment, judge=request.user, scores=data["scores"],
                                   feedback=data.get("feedback"), submit=data["submit"])
        return Response(EvaluationSerializer(evaluation).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        evaluation = self.get_object()
        serializer = EvaluationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluation = services.save(evaluation.assignment, judge=request.user, **serializer.validated_data)
        return Response(EvaluationSerializer(evaluation).data)

    @extend_schema(request=ChangeReasonSerializer, responses=ChangeRequestSerializer)
    @action(detail=True, methods=["post"], url_path="request-change")
    def request_change(self, request, pk=None):
        serializer = ChangeReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = services.request_change(self.get_object(), judge=request.user, **serializer.validated_data)
        return Response(ChangeRequestSerializer(req).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=ChangeScoresSerializer, responses=EvaluationSerializer)
    @action(detail=True, methods=["post"], url_path="change-scores")
    def change_scores(self, request, pk=None):
        serializer = ChangeScoresSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluation = services.change_scores(self.get_object(), judge=request.user, **serializer.validated_data)
        return Response(EvaluationSerializer(evaluation).data)


class ScoreChangeRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ChangeRequestSerializer
    queryset_model = ScoreChangeRequest
    permission_classes = [IsStaffOrLeader]
    filterset_fields = ["status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        # Staff and award managers: only requests on their awards (leaders: all).
        return (ScoreChangeRequest.objects.filter(evaluation__in=services.visible_to(self.request.user))
                .select_related("evaluation__assignment__judge", "evaluation__assignment__report"))

    def get_permissions(self):
        if self.action == "decide":       # staff check, the award manager confirms; leaders aren't involved
            return [IsStaffOrManager()]
        return super().get_permissions()

    @extend_schema(request=ChangeDecisionSerializer, responses=ChangeRequestSerializer)
    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        serializer = ChangeDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = services.decide_change(self.get_object(), by=request.user, **serializer.validated_data)
        return Response(ChangeRequestSerializer(req).data)
