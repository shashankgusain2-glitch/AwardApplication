from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import ApplicantProfile, User
from apps.applications.models import Application
from apps.assignments.models import ConflictOfInterest, JudgeAssignment
from apps.assignments.services import report_for_judge


class AssignmentSerializer(serializers.ModelSerializer):
    """Staff/leader view: who judges what."""
    judge_email = serializers.EmailField(source="judge.email", read_only=True)
    report_reference = serializers.CharField(source="report.reference", read_only=True)
    assigned_by_email = serializers.EmailField(source="assigned_by.email", read_only=True, default=None)

    class Meta:
        model = JudgeAssignment
        fields = ["id", "judge", "judge_email", "report", "report_reference", "round", "status",
                  "assigned_by_email", "assigned_at", "updated_at"]
        read_only_fields = ["id", "status", "assigned_at", "updated_at"]


class AssignmentCreateSerializer(serializers.Serializer):
    report = serializers.PrimaryKeyRelatedField(queryset=Application.objects.all())
    judge = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=User.Role.JUDGE))
    round = serializers.IntegerField(min_value=1, default=1)


class ReassignSerializer(serializers.Serializer):
    judge = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=User.Role.JUDGE))


class AssignmentPairSerializer(serializers.Serializer):
    report = serializers.PrimaryKeyRelatedField(queryset=Application.objects.all())
    judge = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=User.Role.JUDGE))


class BulkAssignSerializer(serializers.Serializer):
    """
    Either `items` (exact report → judge pairs) or `reports` (each report is
    filled with the best eligible judges, up to the award's judges per report).
    """
    round = serializers.IntegerField(min_value=1, default=1)
    items = AssignmentPairSerializer(many=True, required=False)
    reports = serializers.PrimaryKeyRelatedField(queryset=Application.objects.all(), many=True, required=False)

    def validate(self, attrs):
        if bool(attrs.get("items")) == bool(attrs.get("reports")):
            raise serializers.ValidationError("Send either a non-empty `items` list or a non-empty `reports` list.")
        return attrs


class JudgeAssignmentSerializer(serializers.ModelSerializer):
    """
    Judge view: the report as the judge may see it. In blind desk-review
    rounds the applicant and identifying answers are removed.     [Rule 1]
    """
    report = serializers.SerializerMethodField()
    evaluation_id = serializers.IntegerField(source="evaluation.id", read_only=True, default=None)
    criteria = serializers.SerializerMethodField()

    class Meta:
        model = JudgeAssignment
        fields = ["id", "round", "status", "assigned_at", "evaluation_id", "report", "criteria"]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_report(self, obj):
        return report_for_judge(obj)

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_criteria(self, obj):
        """What the judge scores in this round: key, label and weight (%)."""
        return [{"key": c.key, "label": c.label, "weight": c.weight}
                for c in obj.report.award.criteria.filter(round_number=obj.round).order_by("order")]


class ConflictSerializer(serializers.ModelSerializer):
    judge = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=User.Role.JUDGE))
    applicant_profile = serializers.PrimaryKeyRelatedField(queryset=ApplicantProfile.objects.all())

    class Meta:
        model = ConflictOfInterest
        fields = ["id", "judge", "applicant_profile", "reason", "created_at"]
        read_only_fields = ["id", "created_at"]
