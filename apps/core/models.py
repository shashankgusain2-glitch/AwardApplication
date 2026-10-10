"""
Shared building blocks used by every other app.

Planned:
- ActivityLog: who did what, when (append-only). Built in Phase 1.
"""
from django.db import models


class TimeStampedModel(models.Model):
    """Adds created/updated times to any model that inherits from it."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
