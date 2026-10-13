"""
Awards (shown to applicants as "events") and their application forms.
"""
from django.db import models


class Award(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    summary = models.TextField()
    deadline = models.DateField()
    is_open = models.BooleanField(default=True)

    class Meta:
        ordering = ["deadline"]

    def __str__(self):
        return self.name

    @property
    def current_form(self):
        """The newest published form; new applications use this one."""
        return self.form_versions.filter(is_published=True).order_by("-number").first()


class FormVersion(models.Model):
    """
    The questions for one award, frozen once published.             [Rule 4]

    Changing the questions means publishing a new version. Each application
    keeps the version it was started on, so old applications always open
    with the questions they were answered against.

    questions: list of {"key", "label", "type": text|textarea|number, "required"}
    """
    award = models.ForeignKey(Award, on_delete=models.CASCADE, related_name="form_versions")
    number = models.PositiveIntegerField()
    questions = models.JSONField()
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("award", "number")]
        ordering = ["award", "number"]

    def __str__(self):
        return f"{self.award.name} v{self.number}"
