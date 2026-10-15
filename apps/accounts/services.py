"""
Account business logic: sign-up, accounts created by leaders, and staff
verification of organisations.
"""
from django.contrib.auth import password_validation
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record
from apps.core.services import BusinessRuleError
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import ApplicantProfile, JudgeProfile, User


def _check_new_email(email):
    if User.objects.filter(email__iexact=email.strip()).exists():
        raise BusinessRuleError("An account with this email already exists.")


@transaction.atomic
def register_applicant(*, email, password, name, organisation_name=""):
    """Self sign-up. Always creates an applicant, whatever the request says."""
    _check_new_email(email)
    candidate = User(email=email, name=name)
    password_validation.validate_password(password, candidate)
    user = User.objects.create_user(email=email, password=password, name=name, role=User.Role.APPLICANT)
    if organisation_name:
        ApplicantProfile.objects.create(user=user, organisation_name=organisation_name)
    record(user, "create", user, changes={"role": user.role, "via": "sign-up"})
    return user


@transaction.atomic
def create_account(*, created_by, email, name, role, password=None, **judge_fields):
    """
    Staff, award manager, judge and leader accounts are never self-registered: a
    leader (or a superuser) creates them. An award manager may create staff accounts
    only (for their award's team).
    """
    by_manager = created_by.role == User.Role.MANAGER and role == User.Role.STAFF
    if not (created_by.role == User.Role.LEADER or created_by.is_superuser or by_manager):
        raise BusinessRuleError("Only a leader can create accounts. Award managers can add programme staff.")
    if role not in User.Role.values:
        raise BusinessRuleError("Unknown role.")
    _check_new_email(email)
    if password:
        password_validation.validate_password(password, User(email=email, name=name))
    user = User.objects.create_user(email=email, password=password, name=name, role=role)
    if role == User.Role.JUDGE:
        JudgeProfile.objects.create(user=user, **judge_fields)
    record(created_by, "create", user, changes={"role": role})
    return user


def invite(user, *, by):
    """
    Email a "set your password" link to an account a leader created. It is
    Django's password-reset link, so it works once and expires
    (PASSWORD_RESET_TIMEOUT, 3 days by default). Sent after the save commits.
    """
    from django.conf import settings
    from django.contrib.auth.tokens import default_token_generator
    from django.core.mail import send_mail
    from django.urls import reverse
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    if not user.is_active:
        raise BusinessRuleError("This account is deactivated. Reactivate it before sending an invite.")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = settings.SITE_URL.rstrip("/") + reverse("accounts:password_reset_confirm",
                                                  args=[uid, default_token_generator.make_token(user)])
    body = (f"Hello {user.display_name},\n\n{by.display_name} created your {user.get_role_display()} account "
            f"on the Awards Platform.\n\nSet your password here (the link works once and expires in a few days):\n"
            f"{link}\n\nThen log in with {user.email}.")
    transaction.on_commit(lambda: send_mail("[Awards Platform] Your account is ready", body, None, [user.email]))
    record(by, "update", user, changes={"invite_sent": True})
    return link


@transaction.atomic
def verify_organisation(profile, *, by, approve, note=""):
    """Staff check a new organisation before its reports go to judges (13 Oct meeting)."""
    if by.role not in (User.Role.STAFF, User.Role.MANAGER, User.Role.LEADER):
        raise BusinessRuleError("Only staff, award managers or leaders can verify organisations.")
    if approve and not profile.gstin:
        raise BusinessRuleError("The organisation needs a GSTIN before it can be verified.")
    before = profile.verification_status
    profile.verification_status = (ApplicantProfile.Verification.VERIFIED if approve
                                   else ApplicantProfile.Verification.REJECTED)
    profile.verified_by = by
    profile.verified_at = timezone.now()
    profile.verification_note = note
    profile.save()
    record(by, "verify", profile, changes={"from": before, "to": profile.verification_status, "note": note})
    from django.urls import reverse
    message = (f"{profile.organisation_name} is verified. Your applications can now go to judges." if approve
               else f"{profile.organisation_name} couldn't be verified. {note}".strip())
    notify(profile.user, message, kind=Notification.Kind.STATUS_CHANGE, link=reverse("entries:organisation"))
    return profile


@transaction.atomic
def set_active(user, *, by, active):
    """
    Leaders deactivate or reactivate accounts (nothing is deleted). A
    deactivated user's refresh tokens are blacklisted, so the API stops
    working for them at once; web sessions end on their next request.
    """
    if not (by.role == User.Role.LEADER or by.is_superuser):
        raise BusinessRuleError("Only a leader can deactivate or reactivate accounts.")
    if user.pk == by.pk:
        raise BusinessRuleError("You can't deactivate your own account.")
    if user.is_active == active:
        return user
    user.is_active = active
    user.save(update_fields=["is_active", "updated_at"])
    if not active:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
    record(by, "update", user, changes={"is_active": active})
    return user


@transaction.atomic
def save_profile(user, data, *, partial=True):
    """
    Create or update the applicant's own organisation profile. Used by the
    API (/profiles/mine/) and the web form, so both check the same rules:
    GSTIN and PAN format, one profile per GSTIN, and a verified
    organisation's GSTIN can't change. Raises a DRF ValidationError.
    """
    from .api.serializers import ApplicantProfileSerializer

    if user.role != User.Role.APPLICANT:
        raise BusinessRuleError("Only applicants have an organisation profile.")
    profile = ApplicantProfile.objects.filter(user=user).first()
    serializer = ApplicantProfileSerializer(profile, data=data, partial=partial and profile is not None)
    serializer.is_valid(raise_exception=True)
    saved = serializer.save(user=user)
    record(user, "create" if profile is None else "update", saved)
    return saved
