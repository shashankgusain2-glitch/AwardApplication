"""
Login (one form for every role), applicant sign-up, logout and password reset.
"""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .forms import LoginForm, SignUpForm
from .permissions import ROLE_HOME, SESSION_ROLE


def _start_session(request, user):
    """Log in and store the role in the session next to the user id."""
    login(request, user, backend="apps.accounts.backends.EmailBackend")
    request.session[SESSION_ROLE] = user.role


def _safe_next(request, user):
    """Go back to the page they asked for, if it's on this site; else their home."""
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                               require_https=request.is_secure()):
        return nxt
    return reverse_lazy(ROLE_HOME[user.role])


@require_http_methods(["GET", "POST"])
def login_view(request):
    """One login for every role; the account's role decides where they land."""
    if request.user.is_authenticated and request.method == "GET" and request.session.get(SESSION_ROLE):
        return redirect(ROLE_HOME[request.user.role])

    form = LoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        _start_session(request, form.user)
        return redirect(_safe_next(request, form.user))

    return render(request, "accounts/login.html", {
        "form": form,
        "next": request.GET.get("next", request.POST.get("next", "")),
    })


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect(ROLE_HOME[request.user.role])
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        _start_session(request, user)
        messages.success(request, "Your applicant account is ready. Welcome!")
        return redirect(ROLE_HOME[user.role])
    return render(request, "accounts/signup.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)   # also clears the session, including the role
    messages.success(request, "You've been logged out.")
    return redirect("core:home")


# Forgot password: Django's built-in flow, with our own pages.
# In the demo, the reset email is printed in the server log (no real email).
password_reset = auth_views.PasswordResetView.as_view(
    template_name="accounts/password_reset_form.html",
    email_template_name="accounts/password_reset_email.txt",
    subject_template_name="accounts/password_reset_subject.txt",
    success_url=reverse_lazy("accounts:password_reset_done"),
)
password_reset_done = auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html")
password_reset_confirm = auth_views.PasswordResetConfirmView.as_view(
    template_name="accounts/password_reset_confirm.html",
    success_url=reverse_lazy("accounts:password_reset_complete"),
)
password_reset_complete = auth_views.PasswordResetCompleteView.as_view(
    template_name="accounts/password_reset_complete.html")
