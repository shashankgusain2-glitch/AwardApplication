from rest_framework import serializers

from apps.evaluations.models import CriterionScore, Evaluation, ScoreChange, ScoreChangeRequest


class CriterionScoreSerializer(serializers.ModelSerializer):
    criterion = serializers.SlugRelatedField(slug_field="key", read_only=True)
    label = serializers.CharField(source="criterion.label", read_only=True)
    weight = serializers.IntegerField(source="criterion.weight", read_only=True)

    class Meta:
        model = CriterionScore
        fields = ["criterion", "label", "weight", "score", "comment"]


class ScoreChangeSerializer(serializers.ModelSerializer):
    criterion = serializers.SlugRelatedField(slug_field="key", read_only=True)
    changed_by = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = ScoreChange
        fields = ["criterion", "old_score", "new_score", "reason", "changed_by", "created_at"]


class EvaluationSerializer(serializers.ModelSerializer):
    scores = CriterionScoreSerializer(many=True, read_only=True)
    score_changes = ScoreChangeSerializer(many=True, read_only=True)
    report_reference = serializers.CharField(source="assignment.report.reference", read_only=True)

    class Meta:
        model = Evaluation
        fields = ["id", "assignment", "report_reference", "status", "total_score", "feedback", "scores",
                  "score_changes", "submitted_at", "created_at", "updated_at"]
        read_only_fields = fields


class ScoresField(serializers.DictField):
    """{"criterion-key": 8} or {"criterion-key": {"score": 8, "comment": "..."}}"""
    child = serializers.JSONField()


class EvaluationWriteSerializer(serializers.Serializer):
    assignment = serializers.IntegerField(help_text="Must be one of your own assignments")
    scores = ScoresField()
    feedback = serializers.CharField(required=False, allow_blank=True)
    submit = serializers.BooleanField(default=False, help_text="false = save midway; true = submit and lock")


class EvaluationUpdateSerializer(serializers.Serializer):
    scores = ScoresField()
    feedback = serializers.CharField(required=False, allow_blank=True)
    submit = serializers.BooleanField(default=False)


class ChangeRequestSerializer(serializers.ModelSerializer):
    evaluation_report = serializers.CharField(source="evaluation.assignment.report.reference", read_only=True)
    judge_email = serializers.EmailField(source="evaluation.assignment.judge.email", read_only=True)

    class Meta:
        model = ScoreChangeRequest
        fields = ["id", "evaluation", "evaluation_report", "judge_email", "reason", "status", "staff_at", "staff_note",
                  "decided_at", "decision_note", "created_at"]
        read_only_fields = ["id", "status", "staff_at", "staff_note", "decided_at", "decision_note", "created_at",
                            "evaluation"]


class ChangeScoresSerializer(serializers.Serializer):
    scores = ScoresField()
    reason = serializers.CharField()


class ChangeReasonSerializer(serializers.Serializer):
    reason = serializers.CharField()


class ChangeDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, default="")
