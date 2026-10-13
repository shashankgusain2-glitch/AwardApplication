"""
Application ("report") business logic. Views and serializers call these;
they never change status or content directly.
"""
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record
from apps.core.services import BusinessRuleError

from .models import Application

S = Application.Status

# Which status changes staff/leaders may make by hand (the others happen
# automatically when judges are assigned and evaluations are submitted).
MANUAL_TRANSITIONS = {
    (S.SUBMITTED, S.REJECTED): ("staff", "leader"),     # failed the staff check
    (S.SCORED, S.APPROVED): ("leader",),                # leaders approve results
    (S.SCORED, S.REJECTED): ("staff", "leader"),
}


def visible_to(user):
    """Applications this user may see. Never trust ids from the URL; filter here."""
    qs = Application.objects.select_related("applicant", "award", "form_version")
    if user.role == User.Role.APPLICANT:
        return qs.filter(applicant=user)
    if user.role in (User.Role.STAFF, User.Role.LEADER):
        return qs
    if user.role == User.Role.JUDGE:
        return qs.filter(assignments__judge=user).distinct()
    return qs.none()


def _reference(award):
    prefix = "".join(w[0] for w in award.slug.split("-"))[:3].upper() or "APP"
    return f"{prefix}-{timezone.now():%Y}-{secrets.token_hex(3).upper()}"


def set_status(application, new_status, *, by=None, note=""):
    """Change status and write an audit entry. Used by every service."""
    old = application.status
    if old == new_status:
        return application
    application.status = new_status
    application.save(update_fields=["status", "updated_at"])
    record(by, "status_change", application, changes={"from": old, "to": new_status, "note": note})
    return application


@transaction.atomic
def create_draft(*, applicant, award, title):
    if applicant.role != User.Role.APPLICANT:
        raise BusinessRuleError("Only applicants can create applications.")
    if award.status != award.Status.OPEN:
        raise BusinessRuleError("This award isn't open for applications.")
    form = award.current_form
    if form is None:
        raise BusinessRuleError("This award has no published form yet.")
    if Application.objects.filter(applicant=applicant, award=award).exists():
        raise BusinessRuleError("You already have an application for this award.")
    for _ in range(5):   # a reference clash is very unlikely; retry just in case
        try:
            with transaction.atomic():
                app = Application.objects.create(reference=_reference(award), applicant=applicant, award=award,
                                                 form_version=form, title=title)
            break
        except IntegrityError:
            continue
    else:
        raise BusinessRuleError("Couldn't create the application. Please try again.")
    record(applicant, "create", app, changes={"award": award.slug, "form_version": form.version})
    return app


def _can_edit(application):
    return application.status == S.DRAFT or application.edit_allowed


def _check_answers(application, content):
    known = {q["key"] for q in application.form_version.questions}
    unknown = set(content) - known
    if unknown:
        raise BusinessRuleError(f"Unknown question(s): {', '.join(sorted(unknown))}.")


@transaction.atomic
def update(application, *, by, content=None, title=None):
    """Save answers (can be partial: the form saves midway)."""
    if application.applicant_id != by.id:
        raise BusinessRuleError("You can only change your own application.")
    if not _can_edit(application):
        raise BusinessRuleError("This application is submitted. Ask staff to allow changes first.")
    if content is not None:
        _check_answers(application, content)
        application.content = {**application.content, **content}
    if title is not None:
        application.title = title
    application.save()
    record(by, "update", application, changes={"fields": sorted((content or {}).keys())})
    return application


@transaction.atomic
def submit(application, *, by):
    if application.applicant_id != by.id:
        raise BusinessRuleError("You can only submit your own application.")
    if not _can_edit(application):
        raise BusinessRuleError("This application is already submitted.")
    missing = [q["label"] for q in application.form_version.questions
               if q.get("required") and not str(application.content.get(q["key"], "")).strip()]
    if missing:
        raise BusinessRuleError(f"Answer the required questions first: {', '.join(missing[:3])}.")
    first_time = application.status == S.DRAFT
    application.edit_allowed = False
    application.edit_requested = False
    if first_time:
        application.submitted_at = timezone.now()
    application.save()
    if first_time:
        set_status(application, S.SUBMITTED, by=by)
    else:
        record(by, "update", application, changes={"resubmitted_after_edit": True})
    return application


@transaction.atomic
def request_edit(application, *, by, reason):
    if application.applicant_id != by.id:
        raise BusinessRuleError("You can only ask about your own application.")
    if application.status == S.DRAFT:
        raise BusinessRuleError("Drafts can be changed without asking.")
    if not reason.strip():
        raise BusinessRuleError("Give a reason.")
    application.edit_requested = True
    application.edit_reason = reason
    application.save(update_fields=["edit_requested", "edit_reason", "updated_at"])
    record(by, "update", application, changes={"edit_requested": reason})
    return application


@transaction.atomic
def decide_edit(application, *, by, allow):
    if by.role not in (User.Role.STAFF, User.Role.LEADER):
        raise BusinessRuleError("Only staff or leaders can allow changes.")
    if not application.edit_requested:
        raise BusinessRuleError("The applicant hasn't asked to change this application.")
    application.edit_requested = False
    application.edit_allowed = allow
    application.save(update_fields=["edit_requested", "edit_allowed", "updated_at"])
    record(by, "update", application, changes={"edit_allowed": allow})
    return application


@transaction.atomic
def change_status(application, *, by, new_status, note=""):
    """Status changes staff/leaders make by hand (reject, approve)."""
    allowed_roles = MANUAL_TRANSITIONS.get((application.status, new_status))
    if allowed_roles is None:
        raise BusinessRuleError(f"Can't move an application from {application.status} to {new_status}.")
    if by.role not in allowed_roles:
        raise BusinessRuleError("Your role can't make this change.")
    return set_status(application, new_status, by=by, note=note)
