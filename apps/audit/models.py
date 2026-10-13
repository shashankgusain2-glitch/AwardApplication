"""Append-only record of who did what, to which record, and when."""
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        STATUS_CHANGE = "status_change", "Status change"
        ASSIGN = "assign", "Assign"
        REASSIGN = "reassign", "Reassign"
        SCORE = "score", "Score"
        SCORE_CHANGE = "score_change", "Score change"
        VERIFY = "verify", "Verify"
        LOGIN = "login", "Login"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="audit_entries")
    action = models.CharField(max_length=50, choices=Action.choices, db_index=True)
    entity = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=40)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity", "entity_id"], name="audit_entity_idx"),
            models.Index(fields=["user", "-timestamp"], name="audit_user_time_idx"),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.user} {self.action} {self.entity}#{self.entity_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Audit entries are permanent and can't be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit entries are permanent and can't be deleted.")
