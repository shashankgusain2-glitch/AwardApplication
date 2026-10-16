"""
Two-step confirmation for requests made after submitting (TwoStepApproval models):

    asked ──staff check──▶ waiting for the final confirmation ──confirmed──▶ approved (takes effect)
      │                          │
      └──staff refuse──▶ refused └──refused──▶ refused

Who gives the final confirmation (confirmer()): the award's manager, for an applicant's edit
request and a judge's score change alike. If the award has no active manager, the staff check
is the final step. Leaders are never involved (they approve each award's result as a whole).

Staff on that award check first; the award manager never does the staff check (the strict
split in apps/awards/access.py: staff do, the manager decides). Nobody can skip that step,
and staff can't give the final confirmation. Every step is audited and the person who asked is told. The caller (the
service for each kind of request) checks its own "is it still allowed?" rule before each
step and applies the effect when this returns APPROVED.

Re-evaluations are the exception: one step, by the award's manager (manager_step), who then
chooses the fresh judges. A leader decides only when the award has no active manager.
"""
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import TwoStepApproval as T
from .services import BusinessRuleError


def award_manager(award):
    """The award's active manager, or None."""
    manager = award.manager
    return manager if manager is not None and manager.is_active else None


def is_edit(request):
    return getattr(request, "kind", None) == "edit"


def confirmer(request):
    """Who gives the final confirmation: the award manager, or None (then the staff check is final)."""
    return award_manager(award_of(request))


def staff_only(request):
    """An award with no active manager: the staff check is the final step."""
    return confirmer(request) is None


def confirmer_label(request):
    person = confirmer(request)
    return f"the award manager ({person.display_name})" if person else "programme staff"


def can_confirm(user, request):
    person = confirmer(request)
    return user.pk == person.pk if person else can_check(user, request)


def can_check(user, request):
    """The first step: programme staff on the award (never its manager, who decides)."""
    award = award_of(request)
    return user.role == User.Role.STAFF and award.staff.filter(pk=user.pk).exists()


def step(request, *, by, approve, note=""):
    """Take the next step on a request. Returns its new status (WAITING_LEADER, APPROVED or REFUSED)."""
    note = (note or "").strip()
    now = timezone.now()
    if request.status == T.WAITING_STAFF:
        if not can_check(by, request):
            if by.role in (User.Role.STAFF, User.Role.MANAGER):
                from apps.awards.access import check_can_work_on
                check_can_work_on(by, award_of(request))       # "you aren't on the team for ..."
            raise BusinessRuleError(f"Programme staff check this request first; it then goes to "
                                    f"{confirmer_label(request)} to confirm.")
        request.staff_by, request.staff_at, request.staff_note = by, now, note
        if not approve:
            request.status = T.REFUSED
            request.decided_by, request.decided_at = by, now
        elif staff_only(request):                   # no award manager: the staff check decides
            request.status = T.APPROVED
            request.decided_by, request.decided_at, request.decision_note = by, now, note
        else:
            request.status = T.WAITING_LEADER
    elif request.status == T.WAITING_LEADER:
        if not can_confirm(by, request):
            raise BusinessRuleError(f"Staff have checked this request; it now needs {confirmer_label(request)} "
                                    f"to confirm it.")
        request.decided_by, request.decided_at, request.decision_note = by, now, note
        request.status = T.APPROVED if approve else T.REFUSED
    else:
        raise BusinessRuleError("This request has already been decided.")
    request.save()
    record(by, "update", request, changes={"status": request.status, "note": note})
    return request.status


def reevaluation_approver(award):
    """Who decides a re-evaluation on this award: its active manager, else (None) any leader."""
    return award_manager(award)


def can_decide_reevaluation(user, award):
    """The award manager; the award's programme staff if it has no active manager. Never leaders."""
    approver = reevaluation_approver(award)
    if approver is not None:
        return user.pk == approver.pk
    return user.role == User.Role.STAFF and award.staff.filter(pk=user.pk).exists()


def manager_step(request, *, by, approve, note=""):
    """The award manager approves or refuses a re-evaluation in one step. Returns APPROVED or REFUSED."""
    award = award_of(request)
    if not request.waiting:
        raise BusinessRuleError("This request has already been decided.")
    if not can_decide_reevaluation(by, award):
        approver = reevaluation_approver(award)
        raise BusinessRuleError(f"The award manager ({approver.display_name}) decides re-evaluations for "
                                f"{award.name}." if approver else
                                f"{award.name} has no award manager, so its programme staff decide re-evaluations.")
    note = (note or "").strip()
    request.decided_by, request.decided_at, request.decision_note = by, timezone.now(), note
    request.status = T.APPROVED if approve else T.REFUSED
    request.save()
    record(by, "update", request, changes={"status": request.status, "note": note, "step": "award manager"})
    return request.status


def tell(request, *, requester, what, link, effect=""):
    """Tell the right people what just happened to a request, after step(). effect: what approval means for them."""
    who = request.staff_by.display_name if request.staff_by else "Staff"
    note = f" Note: {request.note}" if request.note else ""
    person, label = confirmer(request), confirmer_label(request)
    if request.status == T.WAITING_LEADER:
        message = (f"{what}: checked by {who}, waiting for you to confirm. Reason given: {request.reason}"
                   + (f" Staff note: {request.staff_note}" if request.staff_note else ""))
        if person:
            notify(person, message, kind=Notification.Kind.REQUEST, link=_staff_link())
        notify(requester, f"{what}: the programme staff checked your request and passed it to {label} "
               f"to confirm.", kind=Notification.Kind.STATUS_CHANGE, link=link)
    elif request.status == T.APPROVED:
        by_whom = "the award manager" if person else "programme staff"
        notify(requester, f"{what}: approved by {by_whom}. {effect}{note}".replace("  ", " "),
               kind=Notification.Kind.STATUS_CHANGE, link=link)
        if request.staff_by:
            notify(request.staff_by, f"{what}: confirmed by {by_whom}.", kind=Notification.Kind.STATUS_CHANGE,
                   link=_staff_link())
    elif request.status == T.REFUSED:
        notify(requester, f"{what}: your request was refused.{note}", kind=Notification.Kind.STATUS_CHANGE,
               link=link)


def _staff_link():
    from django.urls import reverse
    return reverse("awards:entries")


def award_of(request):
    """The award a request belongs to (an applicant request or a judge's score change)."""
    if hasattr(request, "application"):
        return request.application.award
    return request.evaluation.assignment.report.award


def waiting(status, user=None):
    """
    Every request at one stage (WAITING_STAFF or WAITING_LEADER), oldest first, in one shape
    for the staff and leadership pages: applicant edits, re-evaluations and judges' score changes.
    With a user: only requests on the awards they may work on (staff and managers see their own).
    """
    from apps.applications.models import ApplicantRequest
    from apps.awards.access import awards_for, sees_every_award
    from apps.evaluations.models import ScoreChangeRequest

    # Re-evaluations aren't two-step: the award manager decides them on their own page.
    applicant_requests = ApplicantRequest.objects.filter(status=status).exclude(kind=ApplicantRequest.Kind.REEVALUATION)
    score_requests = ScoreChangeRequest.objects.filter(status=status)
    if user is not None and not sees_every_award(user):
        applicant_requests = applicant_requests.filter(application__award__in=awards_for(user))
        score_requests = score_requests.filter(evaluation__assignment__report__award__in=awards_for(user))

    rows = []
    for req in applicant_requests.select_related(
            "application__award", "application__applicant__applicant_profile", "requested_by", "staff_by"):
        app = req.application
        profile = getattr(app.applicant, "applicant_profile", None)
        rows.append({"kind": req.kind, "label": req.get_kind_display(), "request": req, "type": "applicant",
                     "confirmer": confirmer(req), "confirmer_label": confirmer_label(req),
                     "reference": app.reference, "award": app.award.name, "report_status": app.get_status_display(),
                     "who": getattr(profile, "organisation_name", "") or app.applicant.email,
                     "who_role": "Applicant"})
    for req in score_requests.select_related(
            "evaluation__assignment__report__award", "evaluation__assignment__judge", "staff_by"):
        assignment = req.evaluation.assignment
        rows.append({"kind": "score", "label": "Change a submitted score", "request": req, "type": "score",
                     "confirmer": confirmer(req), "confirmer_label": confirmer_label(req),
                     "reference": assignment.report.reference, "award": assignment.report.award.name,
                     "report_status": assignment.report.get_status_display(),
                     "who": assignment.judge.display_name, "who_role": "Judge"})
    return sorted(rows, key=lambda r: r["request"].created_at)


def to_confirm(user, rows):
    """The rows this person gives the final confirmation on."""
    return [r for r in rows if can_confirm(user, r["request"])]
