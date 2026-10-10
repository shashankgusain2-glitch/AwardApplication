from . import demo_data


def site(request):
    """Organisation details and portal navigation available on every page."""
    return {
        "org": demo_data.ORGANISATION,
        "portal_nav": demo_data.PORTAL_NAV,
        "role_labels": demo_data.ROLE_LABELS,
    }
