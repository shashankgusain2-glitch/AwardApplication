"""
Write audit entries. Every service that assigns, scores, changes a score,
changes a status or verifies something calls record().
"""
import logging

from .models import AuditLog

logger = logging.getLogger("apps.audit")


def record(user, action, obj=None, *, entity=None, entity_id=None, changes=None, request=None):
    """Add one permanent audit entry. `obj` gives entity and id; or pass them directly."""
    entry = AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        entity=entity or (obj._meta.model_name if obj is not None else ""),
        entity_id=str(entity_id if entity_id is not None else getattr(obj, "pk", "")),
        changes=changes or {},
        ip_address=_client_ip(request),
    )
    logger.info("audit %s %s#%s by %s", entry.action, entry.entity, entry.entity_id, entry.user)
    return entry


def _client_ip(request):
    if request is None:
        return None
    return request.META.get("REMOTE_ADDR") or None
