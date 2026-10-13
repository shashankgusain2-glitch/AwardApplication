"""
Applications (the applicant's "report") and their file attachments.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import SoftDeleteModel, TimeStampedModel

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024   # 10 MB


class Application(TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        ASSIGNED = "assigned", "Assigned to judges"
        IN_REVIEW = "in_review", "In review"
        SCORED = "scored", "Scored"
        REJECTED = "rejected", "Rejected"
        APPROVED = "approved", "Approved"

    reference = models.CharField(max_length=20, unique=True)
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="applications")
    award = models.ForeignKey("awards.Award", on_delete=models.PROTECT, related_name="applications")
    # The questions these answers belong to.                         [Rule 4]
    form_version = models.ForeignKey("awards.FormVersion", on_delete=models.PROTECT, related_name="applications")
    title = models.CharField(max_length=200)
    content = models.JSONField(default=dict, blank=True, help_text="Answers keyed by question key")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    # Changing a submitted report needs staff to allow it (12 Oct meeting).
    edit_requested = models.BooleanField(default=False)
    edit_allowed = models.BooleanField(default=False)
    edit_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["award", "status"], name="application_award_status_idx"),
            models.Index(fields=["applicant", "status"], name="application_owner_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["applicant", "award"], condition=Q(is_deleted=False),
                                    name="application_one_per_award"),
            models.CheckConstraint(condition=Q(status="draft") | Q(submitted_at__isnull=False),
                                   name="application_submitted_has_date"),
        ]

    def __str__(self):
        return f"{self.reference}: {self.title}"


class Attachment(TimeStampedModel):
    ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="attachments")
    question_key = models.CharField(max_length=50, blank=True, default="")
    file = models.FileField(upload_to="attachments/%Y/%m/")
    original_name = models.CharField(max_length=255)
    size_bytes = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(size_bytes__lte=MAX_ATTACHMENT_BYTES), name="attachment_max_10mb"),
        ]

    def __str__(self):
        return self.original_name
