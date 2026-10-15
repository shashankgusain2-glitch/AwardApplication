"""
Shared building blocks used by every other app.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Adds created/updated times to any model that inherits from it."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TwoStepApproval(TimeStampedModel):
    """
    A request that needs two confirmations: staff check it first, then a leader confirms it.
    Only the leader's confirmation takes effect (see apps.core.approvals). Each step keeps
    who decided, when, and an optional note to the person who asked.
    """
    WAITING_STAFF = "requested"
    WAITING_LEADER = "staff_approved"
    APPROVED = "approved"
    REFUSED = "declined"
    STAGES = [(WAITING_STAFF, "Waiting for staff"), (WAITING_LEADER, "Waiting for leadership"),
              (APPROVED, "Approved"), (REFUSED, "Refused")]

    reason = models.TextField()
    staff_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="+")
    staff_at = models.DateTimeField(null=True, blank=True)
    staff_note = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True, default="")

    class Meta:
        abstract = True

    @property
    def waiting(self):
        return self.status in (self.WAITING_STAFF, self.WAITING_LEADER)

    @property
    def confirmer_label(self):
        """Who gives the final confirmation: "the award manager (name)" or "leadership"."""
        from apps.core.approvals import confirmer_label
        return confirmer_label(self)

    @property
    def stage_label(self):
        """The status in words, naming who it waits for."""
        if self.status == self.WAITING_LEADER:
            return f"Waiting for {self.confirmer_label}"
        return self.get_status_display()

    @property
    def note(self):
        """The note to show the person who asked: the leader's, else staff's."""
        return self.decision_note or self.staff_note


class AppendOnlyQuerySet(models.QuerySet):
    """
    For permanent records (audit log, score changes): rows can be added, never
    changed or removed, not even in bulk (`.update()` / `.delete()` on a
    queryset skip the model's own save/delete checks, so they are blocked here).
    """

    def update(self, **kwargs):
        raise ValueError(f"{self.model.__name__} records are permanent and can't be changed.")

    def delete(self):
        raise ValueError(f"{self.model.__name__} records are permanent and can't be deleted.")


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """Soft-delete every row in the queryset."""
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager: hides soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """
    "Deleting" hides the row instead of removing it, so history (judging,
    audit trail) is kept. `objects` hides deleted rows; `all_objects` shows all.
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])
