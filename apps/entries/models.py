"""
Organisations and their applications (the applicant's "report").
"""
from django.conf import settings
from django.db import models

from apps.awards.models import Award, FormVersion


class Organisation(models.Model):
    """
    One organisation, verified by GSTIN and the PAN of the person registering it.
    A GSTIN can be registered only once, which stops impersonation and
    keeps one report per organisation.
    """
    name = models.CharField(max_length=200)
    gstin = models.CharField("GSTIN", max_length=15, unique=True)
    holder_pan = models.CharField("PAN of organisation holder", max_length=10)
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organisation")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Application(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted, staff checking"
        POOL = "pool", "In report pool"
        REJECTED = "rejected", "Rejected (failed proof check)"
        ASSIGNED = "assigned", "Assigned to judges"
        JUDGING = "judging", "Being judged"
        JUDGED = "judged", "Judged"
        SHORTLISTED = "shortlisted", "Shortlisted for Round 2"
        ROUND2_DONE = "round2_done", "Round 2 graded"

    class EditRequest(models.TextChoices):
        NONE = "", "None"
        REQUESTED = "requested", "Waiting for staff"
        APPROVED = "approved", "Approved by staff"
        DECLINED = "declined", "Declined by staff"

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="applications")
    award = models.ForeignKey(Award, on_delete=models.PROTECT, related_name="applications")
    form_version = models.ForeignKey(FormVersion, on_delete=models.PROTECT, related_name="applications")
    answers = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    edit_request = models.CharField(max_length=20, choices=EditRequest.choices, default=EditRequest.NONE, blank=True)
    edit_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # One report per organisation per award.
        unique_together = [("organisation", "award")]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.organisation} · {self.award}"

    @property
    def can_edit(self):
        """Drafts can always be edited; submitted ones only after staff approve."""
        return self.status == self.Status.DRAFT or self.edit_request == self.EditRequest.APPROVED

    @property
    def can_request_edit(self):
        return self.status != self.Status.DRAFT and self.edit_request in (
            self.EditRequest.NONE, self.EditRequest.DECLINED)

    @property
    def progress_steps(self):
        """The status tracker shown to the applicant (Round 2 steps only if shortlisted)."""
        S = self.Status
        order = [S.SUBMITTED, S.POOL, S.ASSIGNED, S.JUDGING, S.JUDGED]
        if self.status in (S.SHORTLISTED, S.ROUND2_DONE):
            order += [S.SHORTLISTED, S.ROUND2_DONE]
        current = order.index(self.status) if self.status in order else -1
        return [
            {"label": s.label, "state": "done" if i < current else "current" if i == current else "todo"}
            for i, s in enumerate(order)
        ]

    def average(self, round_no=1):
        """Average of the judges' weighted totals for a round (completed gradings only)."""
        totals = [a.total for a in self.assignments.filter(round=round_no, status="completed")]
        return round(sum(totals) / len(totals), 2) if totals else None

    @property
    def round1_average(self):
        return self.average(1)

    @property
    def round2_average(self):
        return self.average(2)
