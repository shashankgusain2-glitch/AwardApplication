from django.urls import reverse
from rest_framework import serializers

from apps.applications.models import ApplicantRequest, Application, Attachment
from apps.awards.models import Award


class AttachmentSerializer(serializers.ModelSerializer):
    """The file itself is never linked directly: download_url checks who is asking."""
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "question_key", "original_name", "size_bytes", "content_type", "download_url", "created_at"]
        read_only_fields = fields

    def get_download_url(self, obj) -> str:
        return reverse("api:attachment-download", args=[obj.pk])


class AttachmentUploadSerializer(serializers.Serializer):
    question_key = serializers.CharField(max_length=50, help_text="Key of a question of type 'file'")
    file = serializers.FileField(help_text="PDF, JPG or PNG, up to 10 MB")


REEVALUATION_FIELDS = ["reevaluation_status", "reevaluation_previous_result", "requests"]


class ApplicantRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicantRequest
        fields = ["id", "kind", "reason", "status", "staff_at", "staff_note", "decided_at", "decision_note",
                  "created_at"]
        read_only_fields = fields


class ApplicationSerializer(serializers.ModelSerializer):
    applicant_email = serializers.EmailField(source="applicant.email", read_only=True)
    applicant_name = serializers.CharField(source="applicant.display_name", read_only=True)
    award_name = serializers.CharField(source="award.name", read_only=True)
    award_slug = serializers.SlugField(source="award.slug", read_only=True)
    form_version_number = serializers.IntegerField(source="form_version.version", read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    requests = ApplicantRequestSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = ["id", "reference", "applicant_email", "applicant_name", "award_slug", "award_name",
                  "form_version_number", "title", "content",
                  "status", "submitted_at", "edit_requested", "edit_allowed", "edit_reason", "attachments",
                  *REEVALUATION_FIELDS, "created_at", "updated_at"]
        read_only_fields = ["id", "reference", "status", "submitted_at", "edit_requested", "edit_allowed",
                            "edit_reason", *REEVALUATION_FIELDS, "created_at", "updated_at"]

    def to_representation(self, instance):
        """The applicant sees a provisional result as "scored" until leadership approves the award's result."""
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None and getattr(request.user, "role", "") == "applicant":
            from apps.applications.services import provisional
            if provisional(instance):
                data["status"] = Application.Status.SCORED
        return data


class ApplicationCreateSerializer(serializers.Serializer):
    award = serializers.SlugRelatedField(slug_field="slug", queryset=Award.objects.all())
    title = serializers.CharField(max_length=200)


class ApplicationUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    content = serializers.DictField(required=False, help_text="Answers keyed by question key (can be partial)")


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField()


class DecideSerializer(serializers.Serializer):
    allow = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ReevaluationDecisionSerializer(DecideSerializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class StatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[Application.Status.ACCEPTED, Application.Status.REJECTED,
                                              Application.Status.APPROVED])
    note = serializers.CharField(required=False, allow_blank=True, default="")
