from rest_framework import serializers

from apps.applications.models import Application, Attachment
from apps.awards.models import Award


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["id", "question_key", "file", "original_name", "size_bytes", "content_type", "created_at"]
        read_only_fields = fields


class ApplicationSerializer(serializers.ModelSerializer):
    applicant_email = serializers.EmailField(source="applicant.email", read_only=True)
    applicant_name = serializers.CharField(source="applicant.display_name", read_only=True)
    award_name = serializers.CharField(source="award.name", read_only=True)
    award_slug = serializers.SlugField(source="award.slug", read_only=True)
    form_version_number = serializers.IntegerField(source="form_version.version", read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = ["id", "reference", "applicant_email", "applicant_name", "award_slug", "award_name",
                  "form_version_number", "title", "content",
                  "status", "submitted_at", "edit_requested", "edit_allowed", "edit_reason", "attachments",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "reference", "status", "submitted_at", "edit_requested", "edit_allowed",
                            "edit_reason", "created_at", "updated_at"]


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


class StatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[Application.Status.REJECTED, Application.Status.APPROVED])
    note = serializers.CharField(required=False, allow_blank=True, default="")
