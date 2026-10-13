"""
Email verification: the applicant enters their email, gets a 6-digit code,
types it in, and is logged in. No passwords.
"""
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.entries.forms import CodeForm, EmailForm

SESSION_KEY = "email_verification"
CODE_LIFETIME_SECONDS = 10 * 60
MAX_ATTEMPTS = 5


@require_http_methods(["GET", "POST"])
def verify_email(request):
    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        code = f"{secrets.randbelow(1_000_000):06d}"
        request.session[SESSION_KEY] = {
            "email": email,
            "code": code,
            "expires": time.time() + CODE_LIFETIME_SECONDS,
            "attempts": 0,
        }
        send_mail(
            "Your login code",
            f"Your code is {code}. It expires in 10 minutes.",
            None,
            [email],
        )
        return redirect("accounts:verify_code")
    return render(request, "accounts/verify_email.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_code(request):
    pending = request.session.get(SESSION_KEY)
    if not pending:
        return redirect("accounts:verify_email")

    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if time.time() > pending["expires"]:
            del request.session[SESSION_KEY]
            messages.error(request, "That code has expired. Please ask for a new one.")
            return redirect("accounts:verify_email")

        pending["attempts"] += 1
        request.session[SESSION_KEY] = pending
        if pending["attempts"] > MAX_ATTEMPTS:
            del request.session[SESSION_KEY]
            messages.error(request, "Too many wrong codes. Please ask for a new one.")
            return redirect("accounts:verify_email")

        if secrets.compare_digest(form.cleaned_data["code"], pending["code"]):
            User = get_user_model()
            user, _ = User.objects.get_or_create(email=pending["email"], defaults={"username": pending["email"]})
            del request.session[SESSION_KEY]
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            if user.is_staff:
                return redirect("staff:home")
            if user.is_leader:
                return redirect("dashboard:overview")
            if hasattr(user, "judge"):
                return redirect("judging:tab")
            if not hasattr(user, "organisation"):
                return redirect("entries:register")
            return redirect("entries:events")
        form.add_error("code", "That code isn't right. Check the email and try again.")

    return render(request, "accounts/verify_code.html", {
        "form": form,
        "email": pending["email"],
        # Demo only: no real email is sent, so the code is shown on screen.
        "demo_code": pending["code"] if settings.SHOW_DEMO_EMAIL_CODE else None,
    })


@require_POST
def logout_view(request):
    logout(request)
    return redirect("core:home")
