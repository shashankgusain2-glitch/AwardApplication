"""
Applications (the applicant's "report") and their file attachments.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import SoftDeleteModel, TimeStampedModel, TwoStepApproval

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024   # 10 MB


class Application(TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        ACCEPTED = "accepted", "Accepted for judging"   # staff checked it; only these go to judges
        ASSIGNED = "assigned", "Assigned to judges"
        IN_REVIEW = "in_review", "In review"
        SCORED = "scored", "Scored"
        REJECTED = "rejected", "Rejected"
        APPROVED = "approved", "Approved"

    class Reevaluation(models.TextChoices):
        REQUESTED = "requested", "Re-evaluation requested"
        ALLOWED = "allowed", "Re-evaluation allowed"
        REFUSED = "refused", "Re-evaluation refused"

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
    # Re-evaluation summary (the request itself, with both confirmations, is an ApplicantRequest).
    # Once the result is out the applicant may ask once; confirmed → fresh judges score it again.
    reevaluation_status = models.CharField(max_length=20, choices=Reevaluation.choices, blank=True, default="")
    reevaluation_previous_result = models.CharField(max_length=20, blank=True, default="")

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


class ApplicantRequest(TwoStepApproval):
    """
    An applicant asks to change something after submitting: edit the report (only before
    judging starts) or re-evaluate the result (once, after the result). Staff check it, then
    a leader confirms it; only the leader's confirmation takes effect.
    """

    class Kind(models.TextChoices):
        EDIT = "edit", "Edit the submitted report"
        REEVALUATION = "reevaluation", "Re-evaluate the result"

    class Status(models.TextChoices):
        REQUESTED = TwoStepApproval.WAITING_STAFF, "Waiting for staff"
        STAFF_APPROVED = TwoStepApproval.WAITING_LEADER, "Waiting for leadership"
        APPROVED = TwoStepApproval.APPROVED, "Approved"
        DECLINED = TwoStepApproval.REFUSED, "Refused"

    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="requests")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [   # one open request of each kind per application
            models.UniqueConstraint(fields=["application", "kind"], name="applicant_request_one_open",
                                    condition=Q(status__in=["requested", "staff_approved"])),
        ]

    def __str__(self):
        return f"{self.application.reference}: {self.get_kind_display()} ({self.get_status_display()})"
