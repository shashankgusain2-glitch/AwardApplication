"""Send in-app notifications (email/SMS can be added here later)."""
from django.utils import timezone

from .models import Notification


def notify(user, message, *, kind=Notification.Kind.INFO, link=""):
    return Notification.objects.create(user=user, message=message[:500], kind=kind, link=link)


def mark_read(notification):
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return notification
