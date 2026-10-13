"""In-app notifications for a user."""
from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        INFO = "info", "Information"
        ASSIGNMENT = "assignment", "Assignment"
        STATUS_CHANGE = "status_change", "Status change"
        REQUEST = "request", "Request"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=30, choices=Kind.choices, default=Kind.INFO)
    message = models.CharField(max_length=500)
    link = models.CharField(max_length=300, blank=True, default="")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read", "-created_at"], name="notification_inbox_idx")]

    def __str__(self):
        return f"To {self.user}: {self.message[:40]}"
