from django.conf import settings

ORGANISATION = {
    "name": "Awards Platform",
    "short_name": "AP",
    "email": "awards@awards.example",
}

_ASSETS = ["css/main.css", "js/main.js"]


def _asset_version():
    """Changes when the CSS or JS changes, so browsers don't use an old cached copy."""
    mtimes = []
    for path in _ASSETS:
        try:
            mtimes.append((settings.BASE_DIR / "static" / path).stat().st_mtime)
        except OSError:
            pass
    return str(int(max(mtimes))) if mtimes else "1"


def site(request):
    return {"org": ORGANISATION, "asset_version": _asset_version()}
