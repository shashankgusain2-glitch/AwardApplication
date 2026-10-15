"""
Notifications: an in-app message, and the same message by email.

Every service that changes something a person needs to know about calls
notify(). The email is sent only after the database change is saved
(transaction.on_commit), and a failed email never undoes the change: it is
logged instead. Seeding demo data turns email off with emails_off().
"""
import logging
from contextlib import contextmanager

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Notification

logger = logging.getLogger("apps.notifications")

SUBJECTS = {
    Notification.Kind.ASSIGNMENT: "New report to judge",
    Notification.Kind.STATUS_CHANGE: "Update on your application",
    Notification.Kind.REQUEST: "A request needs your decision",
    Notification.Kind.INFO: "Awards Platform update",
}

_email_enabled = True


@contextmanager
def emails_off():
    """Create notifications without sending email (used by seed_data)."""
    global _email_enabled
    before, _email_enabled = _email_enabled, False
    try:
        yield
    finally:
        _email_enabled = before


def _absolute(link):
    return f"{settings.SITE_URL.rstrip('/')}{link}" if link.startswith("/") else link


def _send_email(to, subject, message, link):
    body = f"{message}\n\n" + (f"Open it here: {_absolute(link)}\n\n" if link else "") + \
           "You are getting this email because you have an account on the Awards Platform."
    try:
        send_mail(f"[Awards Platform] {subject}", body, None, [to])
    except Exception:   # noqa: BLE001 - email trouble must never break the action that caused it
        logger.exception("Could not send notification email to %s", to)


def notify(user, message, *, kind=Notification.Kind.INFO, link="", email=True):
    note = Notification.objects.create(user=user, message=message[:500], kind=kind, link=link)
    if email and _email_enabled and user.is_active and user.email:
        subject = SUBJECTS.get(kind, SUBJECTS[Notification.Kind.INFO])
        transaction.on_commit(lambda: _send_email(user.email, subject, message, link))
    return note


def notify_role(role, message, **kwargs):
    """Notify every active user with this role (e.g. all staff)."""
    from apps.accounts.models import User
    return [notify(u, message, **kwargs) for u in User.objects.filter(role=role, is_active=True)]


def mark_read(notification):
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return notification


def mark_all_read(user):
    return Notification.objects.filter(user=user, is_read=False).update(is_read=True, read_at=timezone.now())


def notify_team(award, message, **kwargs):
    """Notify the people who run this award: its manager and allocated staff (not every staff member)."""
    from apps.awards.access import team
    return [notify(u, message, **kwargs) for u in team(award)]
