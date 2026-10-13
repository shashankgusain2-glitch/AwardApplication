"""
/assignments/          staff and leaders create, bulk-assign and reassign; judges read their own only
/judge/my-assignments/ the logged-in judge's reports (judge taken from request.user)
/conflicts/            staff and leaders record conflicts (Rule 2)
"""
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.assignments import services
from apps.assignments.models import ConflictOfInterest, JudgeAssignment
from apps.core.api.permissions import HasRole, IsJudge, IsStaffOrLeader

from .serializers import (
    AssignmentCreateSerializer,
    AssignmentSerializer,
    BulkAssignSerializer,
    ConflictSerializer,
    JudgeAssignmentSerializer,
    ReassignSerializer,
)


class JudgeStaffOrLeader(HasRole):
    roles = ("judge", "staff", "leader")


class AssignmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    queryset_model = JudgeAssignment
    filterset_fields = ["status", "round", "judge", "report"]
    ordering_fields = ["assigned_at", "status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        # A judge only ever sees their own; another judge's id gives 404.
        return services.visible_to(self.request.user)

    def get_permissions(self):
        if self.action in ("create", "reassign", "bulk"):
            return [IsStaffOrLeader()]
        if self.action in ("accept", "decline"):
            return [IsJudge()]
        return [JudgeStaffOrLeader()]

    def get_serializer_class(self):
        if self.action == "create":
            return AssignmentCreateSerializer
        if self.action == "bulk":
            return BulkAssignSerializer
        if self.request.user.is_authenticated and self.request.user.role == "judge":
            return JudgeAssignmentSerializer
        return AssignmentSerializer

    def create(self, request, *args, **kwargs):
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = services.assign(serializer.validated_data["report"], serializer.validated_data["judge"],
                                     by=request.user, round=serializer.validated_data["round"])
        return Response(AssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=BulkAssignSerializer, responses=AssignmentSerializer(many=True))
    @action(detail=False, methods=["post"])
    def bulk(self, request):
        """
        {"items": [{"report": 1, "judge": 5}, ...]}  assigns exactly these pairs, or
        {"reports": [1, 2]}  fills each report with the best eligible judges.
        All or nothing: one broken rule and nothing is saved (400 names the item).
        """
        serializer = BulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("items"):
            made = services.bulk_assign([(i["report"], i["judge"]) for i in data["items"]],
                                        by=request.user, round=data["round"])
        else:
            made = services.auto_assign_many(data["reports"], by=request.user, round=data["round"])
        return Response(AssignmentSerializer(made, many=True).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=ReassignSerializer, responses=AssignmentSerializer)
    @action(detail=True, methods=["post"])
    def reassign(self, request, pk=None):
        serializer = ReassignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new = services.reassign(self.get_object(), serializer.validated_data["judge"], by=request.user)
        return Response(AssignmentSerializer(new).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=JudgeAssignmentSerializer)
    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        assignment = services.start_review(self.get_object(), judge=request.user)
        return Response(JudgeAssignmentSerializer(assignment).data)

    @extend_schema(request=None, responses=JudgeAssignmentSerializer)
    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        assignment = services.decline(self.get_object(), judge=request.user)
        return Response(JudgeAssignmentSerializer(assignment).data)


class MyAssignmentsView(generics.ListAPIView):
    """GET: reports assigned to the logged-in judge (never another judge's)."""
    serializer_class = JudgeAssignmentSerializer
    queryset_model = JudgeAssignment
    permission_classes = [IsJudge]
    filterset_fields = ["status", "round"]
    ordering_fields = ["assigned_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        return services.visible_to(self.request.user).select_related("evaluation")


class ConflictViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ConflictSerializer
    queryset_model = ConflictOfInterest
    permission_classes = [IsStaffOrLeader]
    filterset_fields = ["judge", "applicant_profile"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):   # building the API docs: no user
            return self.queryset_model.objects.none()
        return ConflictOfInterest.objects.select_related("judge", "applicant_profile")

    def create(self, request, *args, **kwargs):
        serializer = ConflictSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conflict = services.record_conflict(judge=serializer.validated_data["judge"],
                                            profile=serializer.validated_data["applicant_profile"],
                                            by=request.user, reason=serializer.validated_data.get("reason", ""))
        return Response(ConflictSerializer(conflict).data, status=status.HTTP_201_CREATED)
