from rest_framework import serializers

from apps.awards.models import Award, AwardRound, Criterion, FormVersion


class AwardRoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = AwardRound
        fields = ["number", "kind"]


class CriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criterion
        fields = ["round_number", "key", "label", "weight", "order"]


class FormVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormVersion
        fields = ["version", "questions", "published_at"]


class AwardSerializer(serializers.ModelSerializer):
    rounds = AwardRoundSerializer(many=True, read_only=True)
    criteria = CriterionSerializer(many=True, read_only=True)
    current_form = FormVersionSerializer(read_only=True)

    class Meta:
        model = Award
        fields = ["id", "slug", "name", "sector", "summary", "status", "opens_on", "closes_on", "applicant_type",
                  "judges_per_report", "blind_judging", "entry_fee", "rounds", "criteria", "current_form"]
