"""
Which judge grades which report, and the conflicts staff record.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TimeStampedModel


class JudgeAssignment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_REVIEW = "in_review", "In review"
        COMPLETED = "completed", "Completed"
        DECLINED = "declined", "Declined"

    # The judge must have role=judge, be on the award's panel, have no conflict
    # and be under their workload limit: checked in assignments.services.
    judge = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="judge_assignments")
    report = models.ForeignKey("applications.Application", on_delete=models.PROTECT, related_name="assignments")
    round = models.PositiveSmallIntegerField(default=1)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="assignments_made")
    assigned_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["judge", "status"], name="assignment_judge_status_idx"),
            models.Index(fields=["report", "status"], name="assignment_report_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["judge", "report", "round"], name="assignment_unique_judge_report_round"),
            models.CheckConstraint(condition=Q(round__gte=1), name="assignment_round_positive"),
        ]

    def __str__(self):
        return f"{self.judge} → {self.report} (round {self.round})"


class ConflictOfInterest(TimeStampedModel):
    """
    A judge's conflict with an organisation, recorded by STAFF.        [Rule 2]
    Judges don't declare conflicts themselves (12 Oct meeting).
    """

    judge = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conflicts")
    applicant_profile = models.ForeignKey("accounts.ApplicantProfile", on_delete=models.CASCADE,
                                          related_name="conflicts")
    reason = models.CharField(max_length=300, blank=True, default="")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["judge", "applicant_profile"], name="conflict_unique_pair"),
        ]

    def __str__(self):
        return f"{self.judge} × {self.applicant_profile}"
