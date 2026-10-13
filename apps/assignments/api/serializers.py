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


class JudgeAssignmentSerializer(serializers.ModelSerializer):
    """
    Judge view: the report as the judge may see it. In blind desk-review
    rounds the applicant and identifying answers are removed.     [Rule 1]
    """
    report = serializers.SerializerMethodField()
    evaluation_id = serializers.IntegerField(source="evaluation.id", read_only=True, default=None)

    class Meta:
        model = JudgeAssignment
        fields = ["id", "round", "status", "assigned_at", "evaluation_id", "report"]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_report(self, obj):
        return report_for_judge(obj)


class ConflictSerializer(serializers.ModelSerializer):
    judge = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=User.Role.JUDGE))
    applicant_profile = serializers.PrimaryKeyRelatedField(queryset=ApplicantProfile.objects.all())

    class Meta:
        model = ConflictOfInterest
        fields = ["id", "judge", "applicant_profile", "reason", "created_at"]
        read_only_fields = ["id", "created_at"]
