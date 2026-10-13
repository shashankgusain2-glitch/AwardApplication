"""
Role-based access control (RBAC) for every portal page.

  @role_required("judge")   → only judges may open the view

- Not logged in          → sent to the login page, on the right tab
- Logged in, wrong role  → 403 Access Denied
- Session role doesn't match the account (e.g. role changed by an admin)
                         → logged out and sent to log in again
"""
from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

SESSION_ROLE = "role"

# Where each role lands after logging in.
ROLE_HOME = {
    "applicant": "entries:dashboard",
    "staff": "awards:staff_home",
    "judge": "judging:assignments",
    "leader": "dashboard:overview",
}


def login_url(role=None, next_path=None):
    params = {}
    if role:
        params["role"] = role
    if next_path:
        params["next"] = next_path
    url = reverse("accounts:login")
    return f"{url}?{urlencode(params)}" if params else url


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(login_url(roles[0], request.get_full_path()))
            if request.session.get(SESSION_ROLE) != user.role:
                logout(request)
                return redirect(login_url(roles[0], request.get_full_path()))
            if user.role not in roles:
                raise PermissionDenied("Your role can't open this page.")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator
