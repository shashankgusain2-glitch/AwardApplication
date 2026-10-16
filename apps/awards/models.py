"""
Awards and everything staff configure without code: rounds, the
application form (versioned) and the scoring criteria.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.core.models import SoftDeleteModel, TimeStampedModel


class Award(TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        JUDGING = "judging", "Judging"
        RESULTS = "results", "Results"

    class ApplicantType(models.TextChoices):
        ORGANISATION = "organisation", "Organisation"
        TEAM = "team", "Team"
        UNIT = "unit", "Plant / unit"

    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=200)
    sector = models.CharField(max_length=100, blank=True, default="")
    summary = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING, db_index=True)
    opens_on = models.DateField(null=True, blank=True)
    closes_on = models.DateField(null=True, blank=True)
    applicant_type = models.CharField(max_length=20, choices=ApplicantType.choices, default=ApplicantType.ORGANISATION)
    judges_per_report = models.PositiveSmallIntegerField(default=2)
    blind_judging = models.BooleanField(default=False, help_text="Applies to desk-review rounds only")
    entry_fee = models.PositiveIntegerField(default=0, help_text="Rupees; 0 = no fee")
    # Who runs it: a leader picks one award manager and the programme staff allocated to it.
    # Staff and managers only ever see the awards they are on (apps/awards/access.py).
    manager = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="managed_awards", limit_choices_to={"role": "manager"})
    staff = models.ManyToManyField("accounts.User", blank=True, related_name="staff_awards",
                                   limit_choices_to={"role": "staff"})

    # The award's result, approved by leadership as a whole (apps/awards/results.py): the award
    # manager decides each entry and sends the result; a leader approves it (published) or sends it back.
    class Results(models.TextChoices):
        NOT_SENT = "", "Not sent yet"
        SUBMITTED = "submitted", "Waiting for leadership"
        APPROVED = "approved", "Approved"
        RETURNED = "returned", "Sent back to the award manager"

    results_status = models.CharField(max_length=20, choices=Results.choices, blank=True, default="",
                                      db_index=True)
    results_note = models.TextField(blank=True, default="", help_text="The manager's note, or why it was sent back")
    results_submitted_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name="+")
    results_submitted_at = models.DateTimeField(null=True, blank=True)
    results_decided_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name="+")
    results_decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=Q(judges_per_report__gte=1, judges_per_report__lte=7),
                                   name="award_judges_per_report_range"),
            models.CheckConstraint(
                condition=Q(opens_on__isnull=True) | Q(closes_on__isnull=True) | Q(closes_on__gte=F("opens_on")),
                name="award_closes_after_opens"),
        ]

    def __str__(self):
        return self.name

    @property
    def current_form(self):
        """The newest published form version; new applications use it."""
        return self.form_versions.filter(published_at__isnull=False).order_by("-version").first()


class AwardRound(models.Model):
    class Kind(models.TextChoices):
        DESK = "desk", "Desk review"
        SITE = "site", "Site visit"
        LIVE = "live", "Live presentation"

    award = models.ForeignKey(Award, on_delete=models.CASCADE, related_name="rounds")
    number = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.DESK)

    class Meta:
        ordering = ["award", "number"]
        constraints = [
            models.UniqueConstraint(fields=["award", "number"], name="round_unique_per_award"),
            models.CheckConstraint(condition=Q(number__gte=1, number__lte=5), name="round_number_range"),
        ]

    def __str__(self):
        return f"{self.award} · Round {self.number} ({self.get_kind_display()})"


class FormVersion(TimeStampedModel):
    """
    The application questions for an award.                          [Rule 4]
    Once published it is read-only: changing questions means publishing a
    new version. Each application keeps the version it was answered on.

    questions: [{"key", "label", "type", "required", "identifying", "section", "subsection"}]
    ("subsection" is optional: an older version without it still reads correctly)
    """

    award = models.ForeignKey(Award, on_delete=models.PROTECT, related_name="form_versions")
    version = models.PositiveIntegerField()
    questions = models.JSONField(default=list)
    published_at = models.DateTimeField(null=True, blank=True)
    # Staff draft a version and send it; the award manager publishes it or sends it back
    # (apps/awards/team_work.py). Unpublished = a draft: staff can still change it.
    submitted_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")
    submitted_at = models.DateTimeField(null=True, blank=True, help_text="Sent to the award manager (empty: "
                                                                         "being edited, or sent back)")
    reviewed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")
    review_note = models.TextField(blank=True, default="", help_text="Why the manager sent it back")

    class Meta:
        ordering = ["award", "version"]
        constraints = [models.UniqueConstraint(fields=["award", "version"], name="form_version_unique_per_award")]

    def __str__(self):
        return f"{self.award} form v{self.version}"

    @property
    def is_published(self):
        return self.published_at is not None

    @property
    def waiting_for_manager(self):
        return self.published_at is None and self.submitted_at is not None

    def save(self, *args, **kwargs):
        if self.pk:
            before = FormVersion.objects.filter(pk=self.pk).values("published_at", "questions").first()
            if before and before["published_at"] and before["questions"] != self.questions:
                raise ValidationError("A published form version can't be changed. Publish a new version instead.")
        super().save(*args, **kwargs)


class Criterion(models.Model):
    """One thing judges score (1-10), with a weight. Weights per round add up to 100."""

    award = models.ForeignKey(Award, on_delete=models.CASCADE, related_name="criteria")
    round_number = models.PositiveSmallIntegerField(default=1)
    key = models.SlugField(max_length=50)
    label = models.CharField(max_length=200)
    weight = models.PositiveSmallIntegerField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["award", "round_number", "order"]
        constraints = [
            models.UniqueConstraint(fields=["award", "round_number", "key"], name="criterion_unique_key"),
            models.CheckConstraint(condition=Q(weight__gte=1, weight__lte=100), name="criterion_weight_range"),
        ]

    def __str__(self):
        return f"{self.award} R{self.round_number}: {self.label} ({self.weight}%)"


class Escalation(TimeStampedModel):
    """
    A case programme staff pass up to the award manager instead of deciding it themselves
    (a doubtful GSTIN, an applicant disputing a decline, an unclear duplicate...). The manager
    answers with a decision; staff then act on it. Nothing changes on its own.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Waiting for the award manager"
        ANSWERED = "answered", "Answered"

    award = models.ForeignKey(Award, on_delete=models.CASCADE, related_name="escalations")
    application = models.ForeignKey("applications.Application", null=True, blank=True, on_delete=models.CASCADE,
                                    related_name="escalations")
    raised_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    question = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    answer = models.TextField(blank=True, default="")
    answered_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(status="open") | ~Q(answer=""), name="escalation_answered_has_answer"),
        ]

    def __str__(self):
        return f"{self.award}: {self.question[:40]}"
