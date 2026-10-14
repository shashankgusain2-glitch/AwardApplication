from django.conf import settings

from . import demo_data

_ASSETS = ["css/main.css", "js/main.js"]


def _asset_version():
    """
    Changes whenever the CSS or JS file changes, so browsers fetch the new
    file instead of an old cached copy (used as ?v=... on the links).
    """
    mtimes = []
    for path in _ASSETS:
        try:
            mtimes.append((settings.BASE_DIR / "static" / path).stat().st_mtime)
        except OSError:
            pass
    return str(int(max(mtimes))) if mtimes else "1"


def site(request):
    """Organisation details, portal navigation, unread notifications and asset version, on every page."""
    unread = 0
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        from apps.notifications.models import Notification
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
    return {
        "unread_notifications": unread,
        "org": demo_data.ORGANISATION,
        "portal_nav": demo_data.PORTAL_NAV,
        "role_labels": demo_data.ROLE_LABELS,
        "asset_version": _asset_version(),
    }
