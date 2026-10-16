"""
Application ("report") business logic. Views and serializers call these;
they never change status or content directly.
"""
import secrets

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record
from apps.awards.access import awards_for, check_can_work_on
from apps.core.services import BusinessRuleError
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import ApplicantRequest, Application

S = Application.Status

# Which status changes staff/leaders may make by hand (the others happen
# automatically when judges are assigned and evaluations are submitted). Award managers
# don't screen entries: that is staff work (apps/awards/access.py).
MANUAL_TRANSITIONS = {
    (S.SUBMITTED, S.ACCEPTED): ("staff", "leader"),     # passed the staff check
    (S.SUBMITTED, S.REJECTED): ("staff", "leader"),     # failed the staff check
    (S.ACCEPTED, S.REJECTED): ("staff", "leader"),      # found out later (e.g. a duplicate)
}
# An entry's result (successful / not) is the award manager's decision, published only when
# leadership approves the award's result as a whole (apps/awards/results.py).
OUTCOME_FROM = (S.SCORED, S.APPROVED, S.REJECTED)


def visible_to(user):
    """Applications this user may see. Never trust ids from the URL; filter here."""
    qs = Application.objects.select_related("applicant", "award", "form_version")
    if user.role == User.Role.APPLICANT:
        return qs.filter(applicant=user)
    if user.role == User.Role.LEADER:
        return qs
    if user.role in (User.Role.STAFF, User.Role.MANAGER):
        return qs.filter(award__in=awards_for(user))   # only the awards they are on
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


def can_edit(application):
    """Drafts can be changed; submitted ones only after staff allow an edit."""
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
    if not can_edit(application):
        raise BusinessRuleError("This application is submitted. Ask staff to allow changes first.")
    if content is not None:
        _check_answers(application, content)
        application.content = {**application.content, **content}
    if title is not None:
        application.title = title
    application.save()
    record(by, "update", application, changes={"fields": sorted((content or {}).keys())})
    return application


def missing_required(application):
    """Keys of the required questions that have no answer yet (a file question counts once uploaded)."""
    uploaded = set(application.attachments.values_list("question_key", flat=True))
    return {q["key"] for q in application.form_version.questions
            if q.get("required") and not str(application.content.get(q["key"], "")).strip()
            and q["key"] not in uploaded}


@transaction.atomic
def submit(application, *, by):
    if application.applicant_id != by.id:
        raise BusinessRuleError("You can only submit your own application.")
    if not can_edit(application):
        raise BusinessRuleError("This application is already submitted.")
    award = application.award
    if application.status == S.DRAFT and award.status != award.Status.OPEN:
        closed = f" (it closed on {award.closes_on:%d %b %Y})" if award.closes_on else ""
        raise BusinessRuleError(f"{award.name} isn't taking applications any more{closed}.")
    missing = [q["label"] for q in application.form_version.questions if q["key"] in missing_required(application)]
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
    notify(by, f"{application.reference} ({application.award.name}) was submitted. We'll tell you when it moves on.",
           kind=Notification.Kind.STATUS_CHANGE, link=reverse("entries:status"))
    return application


# --- Requests after submitting: staff check them, then a leader confirms (apps.core.approvals) ---

K = ApplicantRequest.Kind
R = Application.Reevaluation


def judging_started(application):
    """A judge has started or finished scoring this report (in its current judging)."""
    from apps.assignments.models import JudgeAssignment
    return application.assignments.filter(status__in=[JudgeAssignment.Status.IN_REVIEW,
                                                      JudgeAssignment.Status.COMPLETED]).exists()


def open_request(application, kind):
    return application.requests.filter(kind=kind, status__in=[ApplicantRequest.Status.REQUESTED,
                                                              ApplicantRequest.Status.STAFF_APPROVED]).first()


def edit_blocked(application):
    """Why the applicant can't ask to edit now ("" = they can). Edits are only possible before judging starts."""
    if application.status == S.DRAFT:
        return "Drafts can be changed without asking."
    if application.status not in (S.SUBMITTED, S.ACCEPTED, S.ASSIGNED) or judging_started(application):
        return ("Judging has started, so the report can't be edited any more. "
                "Once the result is out, you can ask for a re-evaluation.")
    if application.edit_allowed:
        return "You're already allowed to change it."
    return ""


def _what(application, kind):
    label = "Edit after submitting" if kind == K.EDIT else "Re-evaluation of the result"
    return f"{application.reference} ({application.award.name}) · {label}"


def _ask(application, *, by, kind, reason):
    if not reason.strip():
        raise BusinessRuleError("Give a reason." if kind == K.EDIT
                                else "Tell us why you're asking for a re-evaluation.")
    if open_request(application, kind):
        raise BusinessRuleError("You already have a request waiting for a decision.")
    req = ApplicantRequest.objects.create(application=application, kind=kind, requested_by=by, reason=reason.strip())
    record(by, "create", req, changes={"kind": kind, "reason": reason.strip()})
    if kind == K.REEVALUATION:
        _tell_reevaluation_approver(application, reason.strip())
    else:
        _tell_edit_checkers(application, reason.strip())
    return req


def _tell_edit_checkers(application, reason):
    """An edit request goes to the award's programme staff (its manager only if it has no staff). Never leaders."""
    award = application.award
    people = list(award.staff.filter(is_active=True))
    if not people and award.manager and award.manager.is_active:
        people = [award.manager]
    next_step = ("then it goes to the award manager to confirm" if award.manager and award.manager.is_active
                 else "your check decides it (this award has no manager)")
    for person in people:
        notify(person, f"{_what(application, K.EDIT)}: the applicant asks. Reason: {reason} Check it before a "
               f"judge starts; {next_step}.", kind=Notification.Kind.REQUEST, link=reverse("awards:entries"))


def close_edit_requests(application, *, by):
    """
    A judge started on the report: edits are only possible before judging, so any open edit
    request is refused, the applicant is told why, and the staff's reminders are cleared.
    """
    from apps.notifications.models import Notification as N

    for req in application.requests.filter(kind=K.EDIT, status__in=[ApplicantRequest.Status.REQUESTED,
                                                                     ApplicantRequest.Status.STAFF_APPROVED]):
        req.status = ApplicantRequest.Status.DECLINED
        req.decided_by, req.decided_at = by, timezone.now()
        req.decision_note = "A judge has started judging, so the report can't be edited any more."
        req.save()
        record(by, "update", req, changes={"status": req.status, "why": "judging started"})
        notify(req.requested_by, f"{_what(application, K.EDIT)}: closed because a judge has started judging. "
               f"Once the result is out, you can ask for a re-evaluation.",
               kind=Notification.Kind.STATUS_CHANGE, link=reverse("entries:status"))
        N.objects.filter(is_read=False, message__startswith=_what(application, K.EDIT)).exclude(
            user=req.requested_by).update(is_read=True, read_at=timezone.now())
    if application.edit_requested:
        application.edit_requested = False
        application.save(update_fields=["edit_requested", "updated_at"])


def _tell_reevaluation_approver(application, reason):
    """Re-evaluations go to the award manager (its staff decide if it has no manager); staff are told too."""
    from apps.core.approvals import reevaluation_approver

    message = (f"{_what(application, K.REEVALUATION)}: the applicant asks. Reason: {reason} "
               f"Approve it and choose new judges, or refuse it.")
    link = reverse("awards:reevaluations")
    approver = reevaluation_approver(application.award)
    if approver is not None:
        notify(approver, message, kind=Notification.Kind.REQUEST, link=link)
        for person in application.award.staff.filter(is_active=True):
            notify(person, f"{_what(application, K.REEVALUATION)}: the applicant asks; the award manager decides.",
                   kind=Notification.Kind.INFO, link=link)
    else:                                       # no award manager: its programme staff decide
        for person in application.award.staff.filter(is_active=True):
            notify(person, message, kind=Notification.Kind.REQUEST, link=link)


@transaction.atomic
def request_edit(application, *, by, reason):
    """Ask to change a submitted report. Only before judging starts."""
    if application.applicant_id != by.id:
        raise BusinessRuleError("You can only ask about your own application.")
    blocked = edit_blocked(application)
    if blocked:
        raise BusinessRuleError(blocked)
    _ask(application, by=by, kind=K.EDIT, reason=reason)
    application.edit_requested = True
    application.edit_reason = reason.strip()
    application.save(update_fields=["edit_requested", "edit_reason", "updated_at"])
    return application


def has_result(application):
    """
    A result is out: judges scored it, the award manager decided it and leadership approved the
    award's result (published). An entry declined at the staff check is also "rejected", but
    nobody judged it, so it has no result.
    """
    from apps.evaluations.models import Evaluation
    return application.status in (S.APPROVED, S.REJECTED) and application.result_published and \
        Evaluation.objects.filter(assignment__report=application, status=Evaluation.Status.SUBMITTED).exists()


def provisional(application):
    """Decided by the award manager, but leadership hasn't approved the award's result yet."""
    from apps.evaluations.models import Evaluation
    return application.status in (S.APPROVED, S.REJECTED) and not application.result_published and \
        Evaluation.objects.filter(assignment__report=application, status=Evaluation.Status.SUBMITTED).exists()


def as_applicant_sees(applications):
    """
    The applicant doesn't see a provisional result: until leadership approves the award's result
    it shows as "Scored, waiting for the decision". Changes the objects in memory only (never saved).
    """
    for application in applications:
        if provisional(application):
            application.status = S.SCORED
    return applications


def can_request_reevaluation(application):
    """Once the result is out, and only once per application."""
    return has_result(application) and not application.reevaluation_status


@transaction.atomic
def request_reevaluation(application, *, by, reason):
    if application.applicant_id != by.id:
        raise BusinessRuleError("You can only ask about your own application.")
    if not has_result(application):
        raise BusinessRuleError("You can ask for a re-evaluation once the result is out (an entry declined at "
                                "the staff check wasn't judged, so it has no result to re-evaluate).")
    if application.reevaluation_status:
        raise BusinessRuleError("You have already asked for a re-evaluation of this application.")
    _ask(application, by=by, kind=K.REEVALUATION, reason=reason)
    application.reevaluation_status = R.REQUESTED
    application.reevaluation_previous_result = application.status
    application.save(update_fields=["reevaluation_status", "reevaluation_previous_result", "updated_at"])
    return application


@transaction.atomic
def decide_request(req, *, by, approve, note=""):
    """
    The next confirmation step on an applicant's request (staff check, then a leader confirms).
    Each yes re-checks that the request still makes sense; only the leader's yes applies it.
    """
    from apps.core import approvals

    application = req.application
    if approve:   # still allowed? (judging may have started, or the result changed, since they asked)
        if req.kind == K.EDIT and edit_blocked(application):
            raise BusinessRuleError(f"{application.reference}: judging has started, so it can't be edited any "
                                    f"more. Refuse this request; the applicant can ask for a re-evaluation "
                                    f"after the result.")
        if req.kind == K.REEVALUATION and not has_result(application):
            raise BusinessRuleError(f"{application.reference} has no final result to re-evaluate any more.")
    if req.kind == K.REEVALUATION:
        return _decide_reevaluation_request(req, by=by, approve=approve, note=note)
    status = approvals.step(req, by=by, approve=approve, note=note)
    if req.kind == K.EDIT:
        if status == ApplicantRequest.Status.APPROVED:
            application.edit_allowed = True
        if status in (ApplicantRequest.Status.APPROVED, ApplicantRequest.Status.DECLINED):
            application.edit_requested = False
            application.save(update_fields=["edit_requested", "edit_allowed", "updated_at"])
    elif status == ApplicantRequest.Status.APPROVED:
        _start_reevaluation(application, by)
    elif status == ApplicantRequest.Status.DECLINED:
        application.reevaluation_status = R.REFUSED
        application.save(update_fields=["reevaluation_status", "updated_at"])
    link = reverse("entries:form", args=[application.award.slug]) if req.kind == K.EDIT else reverse("entries:status")
    effect = ("You can now change your application, then submit it again." if req.kind == K.EDIT else
              "New judges will score your application, then the result will be decided again.")
    approvals.tell(req, requester=req.requested_by, what=_what(application, req.kind), link=link, effect=effect)
    return req


def _decide_reevaluation_request(req, *, by, approve, note):
    """One step by the award manager. Approved: the first judges' work stops counting; fresh judges are needed."""
    from apps.core import approvals

    application = req.application
    status = approvals.manager_step(req, by=by, approve=approve, note=note)
    what = _what(application, K.REEVALUATION)
    note_text = f" Note: {req.decision_note}" if req.decision_note else ""
    if status == ApplicantRequest.Status.APPROVED:
        _start_reevaluation(application, by)
        for person in application.award.staff.filter(is_active=True):
            notify(person, f"{what}: approved by the award manager. Choose the new judges (the first judges "
                   f"aren't offered again).", kind=Notification.Kind.REQUEST,
                   link=reverse("awards:assign", args=[application.pk]))
        notify(req.requested_by, f"{what}: approved by the award manager. New judges will score your application, "
               f"then the result will be decided again.{note_text}",
               kind=Notification.Kind.STATUS_CHANGE, link=reverse("core:results"))
    else:
        application.reevaluation_status = R.REFUSED
        application.save(update_fields=["reevaluation_status", "updated_at"])
        notify(req.requested_by, f"{what}: your request was refused. Your result stays as it is.{note_text}",
               kind=Notification.Kind.STATUS_CHANGE, link=reverse("core:results"))
    return req


def _start_reevaluation(application, by):
    """The first judges' work becomes 'Replaced' (kept, no longer counted); fresh judges score it again."""
    from apps.assignments.models import JudgeAssignment

    application.reevaluation_status = R.ALLOWED
    application.result_published = False        # its new result is published with the award's updated result
    application.save(update_fields=["reevaluation_status", "result_published", "updated_at"])
    for assignment in application.assignments.exclude(status__in=[JudgeAssignment.Status.DECLINED,
                                                                  JudgeAssignment.Status.SUPERSEDED]):
        before = assignment.status
        assignment.status = JudgeAssignment.Status.SUPERSEDED
        assignment.save(update_fields=["status", "updated_at"])
        record(by, "update", assignment, changes={"status": {"from": before, "to": assignment.status},
                                                  "why": "re-evaluation confirmed"})
    set_status(application, S.ACCEPTED, by=by,       # already checked by staff: straight back to the judges' pool
               note=f"re-evaluation confirmed; was {application.reevaluation_previous_result}")


def decide_edit(application, *, by, allow, note=""):
    """The next step on the application's open edit request (the API's decide-edit)."""
    req = open_request(application, K.EDIT)
    if req is None:
        raise BusinessRuleError("The applicant hasn't asked to change this application.")
    decide_request(req, by=by, approve=allow, note=note)
    application.refresh_from_db()
    return application


def decide_reevaluation(application, *, by, allow, note=""):
    """The next step on the application's open re-evaluation request (the API's decide-reevaluation)."""
    req = open_request(application, K.REEVALUATION)
    if req is None:
        raise BusinessRuleError("There's no re-evaluation request waiting for this application.")
    decide_request(req, by=by, approve=allow, note=note)
    application.refresh_from_db()
    return application


@transaction.atomic
def change_status(application, *, by, new_status, note=""):
    """
    Status changes made by hand: staff accept or decline a submitted entry; the award manager
    decides a scored entry's result (apps/awards/results.py; published when leadership approves).
    """
    if new_status in (S.APPROVED, S.REJECTED) and application.status in OUTCOME_FROM:
        from apps.awards import results
        return results.decide_entry(application, by=by, successful=new_status == S.APPROVED, note=note)
    allowed_roles = MANUAL_TRANSITIONS.get((application.status, new_status))
    if allowed_roles is None:
        raise BusinessRuleError(f"Can't move an application from {application.status} to {new_status}.")
    if by.role == User.Role.MANAGER:
        raise BusinessRuleError("Programme staff accept or decline entries; the award manager doesn't.")
    if by.role not in allowed_roles:
        raise BusinessRuleError("Your role can't make this change.")
    check_can_work_on(by, application.award)
    if new_status == S.ACCEPTED:
        _check_can_accept(application)
    if application.status in (S.SUBMITTED, S.ACCEPTED) and new_status == S.REJECTED and not note.strip():
        raise BusinessRuleError("Give a reason for declining: the applicant sees it.")
    set_status(application, new_status, by=by, note=note)
    outcome = {S.APPROVED: "approved", S.ACCEPTED: "accepted for judging"}.get(new_status, "not successful")
    notify(application.applicant, f"{application.reference} ({application.award.name}): your application was {outcome}."
           + (f" Note: {note}" if note else ""), kind=Notification.Kind.STATUS_CHANGE, link=reverse("entries:status"))
    return application


def _check_can_accept(application):
    """Staff accept an entry only for a verified organisation with no undecided duplicate in this award."""
    from apps.accounts import duplicates
    from apps.accounts.models import ApplicantProfile

    profile = ApplicantProfile.objects.filter(user=application.applicant).first()
    if not duplicates.is_verified(profile):
        raise BusinessRuleError("Verify the organisation first: entries are accepted only from verified "
                                "organisations.")
    clash = duplicates.open_duplicate_in_award(profile, application.award)
    if clash:
        raise BusinessRuleError(f"{clash.profile_a.organisation_name} and {clash.profile_b.organisation_name} may be "
                                f"the same organisation, and both entered {application.award.name}. Programme staff "
                                f"decide it on Duplicate review first.")


def accept_entry(application, *, by, note=""):
    """Staff check passed: the entry can go to judges."""
    return change_status(application, by=by, new_status=S.ACCEPTED, note=note)


def decline_entry(application, *, by, note):
    """Staff check failed (not eligible, a duplicate entry, ...). The applicant sees the reason."""
    return change_status(application, by=by, new_status=S.REJECTED, note=note)


def applicant_home(user):
    """Everything the applicant's home page shows: only this applicant's own data."""
    from apps.accounts.models import ApplicantProfile
    from apps.awards.models import Award
    from apps.evaluations.services import applicant_progress

    applications = as_applicant_sees(list(visible_to(user).prefetch_related("assignments", "award__rounds")
                                          .order_by("-updated_at")))
    for application in applications:
        application.judging = applicant_progress(application)
    entered = {a.award_id for a in applications}
    return {
        "applications": applications,
        "profile": ApplicantProfile.objects.filter(user=user).first(),
        "open_awards": Award.objects.filter(status=Award.Status.OPEN).exclude(id__in=entered)
                                    .prefetch_related("rounds"),
        "drafts": [a for a in applications if a.status == S.DRAFT],
    }
