"""
A judge's evaluation of one assignment, its per-criterion scores, and the
permanent record of every score change.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import AppendOnlyQuerySet, TimeStampedModel, TwoStepApproval

SCORE_RANGE = Q(score__gte=1, score__lte=10)


class Evaluation(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft (saved midway)"
        SUBMITTED = "submitted", "Submitted"

    assignment = models.OneToOneField("assignments.JudgeAssignment", on_delete=models.PROTECT,
                                      related_name="evaluation")
    total_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                      help_text="Weighted total out of 10, recalculated by the service")
    feedback = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(total_score__isnull=True) | Q(total_score__gte=0, total_score__lte=10),
                                   name="evaluation_total_range"),
            models.CheckConstraint(condition=Q(status="draft") | Q(submitted_at__isnull=False),
                                   name="evaluation_submitted_has_date"),
        ]

    def __str__(self):
        return f"Evaluation of {self.assignment}"


class CriterionScore(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="scores")
    criterion = models.ForeignKey("awards.Criterion", on_delete=models.PROTECT, related_name="scores")
    score = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["evaluation", "criterion"], name="score_unique_per_criterion"),
            models.CheckConstraint(condition=SCORE_RANGE, name="score_range_1_10"),
        ]

    def __str__(self):
        return f"{self.criterion.key}: {self.score}"


class ScoreChangeRequest(TwoStepApproval):
    """A judge asks to change a submitted evaluation: staff check it, then a leader confirms it."""

    class Status(models.TextChoices):
        REQUESTED = TwoStepApproval.WAITING_STAFF, "Waiting for staff"
        STAFF_APPROVED = TwoStepApproval.WAITING_LEADER, "Waiting for leadership"
        APPROVED = TwoStepApproval.APPROVED, "Approved"
        DECLINED = TwoStepApproval.REFUSED, "Refused"
        USED = "used", "Change made"

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="change_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class ScoreChange(models.Model):
    """
    Permanent record of a score change after submission: who, when,
    old and new value, and why.                                     [Rule 3]
    Never edited or deleted.
    """

    evaluation = models.ForeignKey(Evaluation, on_delete=models.PROTECT, related_name="score_changes")
    criterion = models.ForeignKey("awards.Criterion", on_delete=models.PROTECT, related_name="+")
    old_score = models.PositiveSmallIntegerField()
    new_score = models.PositiveSmallIntegerField()
    reason = models.TextField()
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    request = models.ForeignKey(ScoreChangeRequest, on_delete=models.PROTECT, related_name="changes")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()   # no bulk update/delete either

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(old_score__gte=1, old_score__lte=10), name="change_old_score_range"),
            models.CheckConstraint(condition=Q(new_score__gte=1, new_score__lte=10), name="change_new_score_range"),
            models.CheckConstraint(condition=~Q(reason=""), name="change_reason_required"),
        ]

    def __str__(self):
        return f"{self.criterion_id}: {self.old_score} → {self.new_score} by {self.changed_by_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Score changes are permanent and can't be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Score changes are permanent and can't be deleted.")
