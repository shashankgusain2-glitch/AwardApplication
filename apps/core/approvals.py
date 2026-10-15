"""
Two-step confirmation for requests made after submitting (TwoStepApproval models):

    asked ──staff check──▶ waiting for the final confirmation ──confirmed──▶ approved (takes effect)
      │                          │
      └──staff refuse──▶ refused └──refused──▶ refused

Who gives the final confirmation (confirmer()):
    an applicant's edit request   the award's manager; if the award has no active manager, the
                                  staff check is the final step (leaders are never involved)
    a judge's score change        a leader

Staff on that award check first (the award manager may, only if the award has no staff, and
not for an edit they would then confirm themselves); nobody can skip that step, and staff
can't give the final confirmation. Every step is audited and the person who asked is told. The caller (the
service for each kind of request) checks its own "is it still allowed?" rule before each
step and applies the effect when this returns APPROVED.

Re-evaluations are the exception: one step, by the award's manager (manager_step), who then
chooses the fresh judges. A leader decides only when the award has no active manager.
"""
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record
from apps.notifications.models import Notification
from apps.notifications.services import notify, notify_role

from .models import TwoStepApproval as T
from .services import BusinessRuleError


def award_manager(award):
    """The award's active manager, or None."""
    manager = award.manager
    return manager if manager is not None and manager.is_active else None


def is_edit(request):
    return getattr(request, "kind", None) == "edit"


def confirmer(request):
    """Who gives the final confirmation: a user (the award manager), or None (leaders, or staff for an edit)."""
    return award_manager(award_of(request)) if is_edit(request) else None


def staff_only(request):
    """An edit on an award with no active manager: the staff check is the final step."""
    return is_edit(request) and confirmer(request) is None


def confirmer_label(request):
    person = confirmer(request)
    if person:
        return f"the award manager ({person.display_name})"
    return "programme staff" if staff_only(request) else "leadership"


def can_confirm(user, request):
    person = confirmer(request)
    if person:
        return user.pk == person.pk
    if staff_only(request):
        return can_check(user, request)
    return user.role == User.Role.LEADER


def can_check(user, request):
    """The first step: staff on the award; its manager only when the award has no active staff."""
    award = award_of(request)
    if user.role == User.Role.STAFF:
        return award.staff.filter(pk=user.pk).exists()
    if user.role == User.Role.MANAGER and award.manager_id == user.pk:
        return not award.staff.filter(is_active=True).exists()
    return False


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
    if request.status in (T.APPROVED, T.REFUSED) and not is_edit(request):
        _clear_leader_reminders(request)
    return request.status


def _clear_leader_reminders(request):
    """Decided: the leaders' "waiting for you" notifications about it are no longer work to do."""
    from django.utils import timezone as tz
    Notification.objects.filter(link=_leader_link(request), is_read=False).update(is_read=True, read_at=tz.now())


def reevaluation_approver(award):
    """Who decides a re-evaluation on this award: its active manager, else (None) any leader."""
    return award_manager(award)


def can_decide_reevaluation(user, award):
    approver = reevaluation_approver(award)
    if approver is not None:
        return user.pk == approver.pk
    return user.role == User.Role.LEADER


def manager_step(request, *, by, approve, note=""):
    """The award manager approves or refuses a re-evaluation in one step. Returns APPROVED or REFUSED."""
    award = award_of(request)
    if not request.waiting:
        raise BusinessRuleError("This request has already been decided.")
    if not can_decide_reevaluation(by, award):
        approver = reevaluation_approver(award)
        raise BusinessRuleError(f"The award manager ({approver.display_name}) decides re-evaluations for "
                                f"{award.name}." if approver else
                                f"{award.name} has no award manager, so a leader decides re-evaluations.")
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
        elif not is_edit(request):                  # leaders only ever hear about score changes
            notify_role(User.Role.LEADER, message, kind=Notification.Kind.REQUEST, link=_leader_link(request))
        notify(requester, f"{what}: the programme staff checked your request and passed it to {label} "
               f"to confirm.", kind=Notification.Kind.STATUS_CHANGE, link=link)
    elif request.status == T.APPROVED:
        by_whom = "the award manager" if person else "programme staff" if staff_only(request) else "leadership"
        notify(requester, f"{what}: approved by {by_whom}. {effect}{note}".replace("  ", " "),
               kind=Notification.Kind.STATUS_CHANGE, link=link)
        if request.staff_by:
            notify(request.staff_by, f"{what}: confirmed by {by_whom}.", kind=Notification.Kind.STATUS_CHANGE,
                   link=_staff_link())
    elif request.status == T.REFUSED:
        notify(requester, f"{what}: your request was refused.{note}", kind=Notification.Kind.STATUS_CHANGE,
               link=link)


def _leader_link(request):
    """The leader's page for this one request, with Confirm and Refuse."""
    from django.urls import reverse
    kind = "applicant" if hasattr(request, "application") else "score"
    return reverse("dashboard:request_detail", args=[kind, request.pk])


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
                     "confirmer": None, "confirmer_label": "leadership",
                     "reference": assignment.report.reference, "award": assignment.report.award.name,
                     "report_status": assignment.report.get_status_display(),
                     "who": assignment.judge.display_name, "who_role": "Judge"})
    return sorted(rows, key=lambda r: r["request"].created_at)


def for_leaders(rows):
    """The rows a leader confirms: judges' score changes (never applicants' edits)."""
    return [r for r in rows if r["confirmer"] is None and r["kind"] == "score"]


def to_confirm(user, rows):
    """The rows this person gives the final confirmation on."""
    return [r for r in rows if can_confirm(user, r["request"])]
