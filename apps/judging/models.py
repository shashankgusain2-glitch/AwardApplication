"""
Judges, assignments, grading, score changes and Round 2 meetings
(from the 12 Oct meeting).
"""
from django.conf import settings
from django.db import models

from apps.awards.models import Award
from apps.entries.models import Application, Organisation


class JudgeProfile(models.Model):
    """A user who can judge. Staff pick judges by priority (1 = first choice)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="judge")
    name = models.CharField(max_length=200)
    expertise = models.CharField(max_length=200, blank=True)
    priority = models.PositiveSmallIntegerField(default=5, help_text="1 = first choice")
    max_load = models.PositiveSmallIntegerField(default=10, help_text="Most reports at once")
    panels = models.ManyToManyField(Award, blank=True, related_name="judges",
                                    help_text="Events this judge is selected for")

    class Meta:
        ordering = ["priority", "name"]

    def __str__(self):
        return self.name

    @property
    def open_load(self):
        """Reports offered or being graded right now (used to balance workload)."""
        return self.assignments.filter(status__in=[Assignment.Status.OFFERED, Assignment.Status.ACCEPTED]).count()


class Conflict(models.Model):
    """
    A conflict between a judge and an organisation, recorded by STAFF.  [Rule 2]
    Judges don't declare conflicts themselves (12 Oct meeting).
    """
    judge = models.ForeignKey(JudgeProfile, on_delete=models.CASCADE, related_name="conflicts")
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="conflicts")
    note = models.CharField(max_length=300, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("judge", "organisation")]


class Assignment(models.Model):
    """One judge, one report, one round."""

    class Status(models.TextChoices):
        OFFERED = "offered", "Waiting for judge"
        ACCEPTED = "accepted", "Accepted, grading"
        DECLINED = "declined", "Declined"
        COMPLETED = "completed", "Graded"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="assignments")
    judge = models.ForeignKey(JudgeProfile, on_delete=models.CASCADE, related_name="assignments")
    round = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OFFERED)
    # Can the judge change scores of a graded report right now? Only after staff approve.
    change_allowed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("application", "judge", "round")]
        ordering = ["round", "created_at"]

    def __str__(self):
        return f"{self.judge} → {self.application} (Round {self.round})"

    @property
    def criteria(self):
        return self.application.award.criteria_for(self.round)

    @property
    def scores_by_key(self):
        return {s.criterion: s for s in self.scores.all()}

    @property
    def progress(self):
        total = len(self.criteria)
        return round(self.scores.count() * 100 / total) if total else 0

    @property
    def total(self):
        """Weighted total out of 10."""
        scores = self.scores_by_key
        total = sum(c["weight"] * scores[c["key"]].value for c in self.criteria if c["key"] in scores)
        return round(total / 100, 2)


class Score(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="scores")
    criterion = models.CharField(max_length=50)
    value = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = [("assignment", "criterion")]


class ScoreChangeRequest(models.Model):
    """A judge asks staff for permission to change a graded report's scores."""

    class Status(models.TextChoices):
        REQUESTED = "requested", "Waiting for staff"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"
        USED = "used", "Change made"

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="change_requests")
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ScoreChange(models.Model):
    """
    Permanent record of every score change after grading.            [Rule 3]
    Never edited or deleted.
    """
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT, related_name="score_changes")
    criterion = models.CharField(max_length=50)
    old_value = models.PositiveSmallIntegerField()
    new_value = models.PositiveSmallIntegerField()
    reason = models.TextField()
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    request = models.ForeignKey(ScoreChangeRequest, on_delete=models.PROTECT, related_name="changes")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Score changes are permanent and can't be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Score changes are permanent and can't be deleted.")


class Round2Meeting(models.Model):
    """Round 2: a group of judges meets the organisation online and grades it."""
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="round2_meeting")
    scheduled_at = models.DateTimeField()
    meeting_link = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
