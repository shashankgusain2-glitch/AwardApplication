"""
Shared building blocks used by every other app.
"""
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Adds created/updated times to any model that inherits from it."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
