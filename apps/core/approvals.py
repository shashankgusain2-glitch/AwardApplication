"""
Two-step confirmation for requests made after submitting (TwoStepApproval models):

    asked ──staff check──▶ waiting for leadership ──leader confirms──▶ approved (takes effect)
      │                          │
      └──staff refuse──▶ refused └──leader refuses──▶ refused

Staff always check first; a leader can't skip that step, and staff can't give the final
confirmation. Every step is audited and the person who asked is told. The caller (the
service for each kind of request) checks its own "is it still allowed?" rule before each
step and applies the effect when this returns APPROVED.
"""
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record
from apps.notifications.models import Notification
from apps.notifications.services import notify, notify_role

from .models import TwoStepApproval as T
from .services import BusinessRuleError


def step(request, *, by, approve, note=""):
    """Take the next step on a request. Returns its new status (WAITING_LEADER, APPROVED or REFUSED)."""
    note = (note or "").strip()
    now = timezone.now()
    if request.status == T.WAITING_STAFF:
        if by.role != User.Role.STAFF:
            raise BusinessRuleError("Programme staff check this request first; it then comes to leadership.")
        request.staff_by, request.staff_at, request.staff_note = by, now, note
        request.status = T.WAITING_LEADER if approve else T.REFUSED
        if not approve:
            request.decided_by, request.decided_at = by, now
    elif request.status == T.WAITING_LEADER:
        if by.role != User.Role.LEADER:
            raise BusinessRuleError("Staff have checked this request; it now needs a leader to confirm it.")
        request.decided_by, request.decided_at, request.decision_note = by, now, note
        request.status = T.APPROVED if approve else T.REFUSED
    else:
        raise BusinessRuleError("This request has already been decided.")
    request.save()
    record(by, "update", request, changes={"status": request.status, "note": note})
    return request.status


def tell(request, *, requester, what, link, effect=""):
    """Tell the right people what just happened to a request, after step(). effect: what approval means for them."""
    who = request.staff_by.display_name if request.staff_by else "Staff"
    note = f" Note: {request.note}" if request.note else ""
    if request.status == T.WAITING_LEADER:
        notify_role(User.Role.LEADER, f"{what}: checked by {who}, waiting for a leader to confirm. "
                    f"Reason given: {request.reason}" + (f" Staff note: {request.staff_note}" if request.staff_note
                                                         else ""),
                    kind=Notification.Kind.REQUEST, link=_leader_link())
        notify(requester, f"{what}: the programme staff checked your request and passed it to leadership "
               f"to confirm.", kind=Notification.Kind.STATUS_CHANGE, link=link)
    elif request.status == T.APPROVED:
        notify(requester, f"{what}: approved by leadership. {effect}{note}".replace("  ", " "),
               kind=Notification.Kind.STATUS_CHANGE, link=link)
        if request.staff_by:
            notify(request.staff_by, f"{what}: confirmed by leadership.", kind=Notification.Kind.STATUS_CHANGE,
                   link=_staff_link())
    elif request.status == T.REFUSED:
        notify(requester, f"{what}: your request was refused.{note}", kind=Notification.Kind.STATUS_CHANGE,
               link=link)


def _leader_link():
    from django.urls import reverse
    return reverse("dashboard:requests")


def _staff_link():
    from django.urls import reverse
    return reverse("awards:entries")


def waiting(status):
    """
    Every request at one stage (WAITING_STAFF or WAITING_LEADER), oldest first, in one shape
    for the staff and leadership pages: applicant edits, re-evaluations and judges' score changes.
    """
    from apps.applications.models import ApplicantRequest
    from apps.evaluations.models import ScoreChangeRequest

    rows = []
    for req in ApplicantRequest.objects.filter(status=status).select_related(
            "application__award", "application__applicant__applicant_profile", "requested_by", "staff_by"):
        app = req.application
        profile = getattr(app.applicant, "applicant_profile", None)
        rows.append({"kind": req.kind, "label": req.get_kind_display(), "request": req, "type": "applicant",
                     "reference": app.reference, "award": app.award.name, "report_status": app.get_status_display(),
                     "who": getattr(profile, "organisation_name", "") or app.applicant.email,
                     "who_role": "Applicant"})
    for req in ScoreChangeRequest.objects.filter(status=status).select_related(
            "evaluation__assignment__report__award", "evaluation__assignment__judge", "staff_by"):
        assignment = req.evaluation.assignment
        rows.append({"kind": "score", "label": "Change a submitted score", "request": req, "type": "score",
                     "reference": assignment.report.reference, "award": assignment.report.award.name,
                     "report_status": assignment.report.get_status_display(),
                     "who": assignment.judge.display_name, "who_role": "Judge"})
    return sorted(rows, key=lambda r: r["request"].created_at)
