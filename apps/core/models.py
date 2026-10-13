"""
Shared building blocks used by every other app.
"""
from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Adds created/updated times to any model that inherits from it."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActivityLog(models.Model):
    """
    Append-only record of what happened, by whom and when.
    Staff use it to document each event; leadership sees it on the dashboard.
    """
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=200)
    application = models.ForeignKey("entries.Application", null=True, blank=True, on_delete=models.CASCADE,
                                    related_name="activity")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.created_at:%d %b %H:%M} {self.actor}: {self.action}"


def log(actor, action, application=None):
    return ActivityLog.objects.create(actor=actor, action=action, application=application)
