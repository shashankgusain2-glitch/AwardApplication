"""
Account business logic: sign-up, accounts created by leaders, and staff
verification of organisations.
"""
from django.contrib.auth import password_validation
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record
from apps.core.services import BusinessRuleError

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
    Staff, judge and leader accounts are never self-registered: only a
    leader (or a superuser) creates them.
    """
    if not (created_by.role == User.Role.LEADER or created_by.is_superuser):
        raise BusinessRuleError("Only a leader can create accounts.")
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


@transaction.atomic
def verify_organisation(profile, *, by, approve, note=""):
    """Staff check a new organisation before its reports go to judges (13 Oct meeting)."""
    if by.role not in (User.Role.STAFF, User.Role.LEADER):
        raise BusinessRuleError("Only staff or leaders can verify organisations.")
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
    return profile
