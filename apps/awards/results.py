"""
An award's result, decided per entry by the award manager and approved as a whole by leadership.

    judges score ─▶ the award manager marks each scored entry Successful / Not successful
                    (provisional: applicants don't see it)
                 ─▶ every entry decided ─▶ "Send results to leadership"     (results_status = submitted)
                 ─▶ a leader approves the award's result                     (approved: published)
                    or sends it back with a note                             (returned: the manager changes it)

Approving publishes every decided entry in the award at once: it appears on the results board,
each applicant is told their result, and re-evaluation becomes possible. After a re-evaluation
the manager decides that entry again and sends the award's updated result the same way.
If an award has no active manager, its programme staff prepare the result.
"""
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.applications.models import Application
from apps.applications.services import set_status
from apps.audit.services import record
from apps.core.services import BusinessRuleError
from apps.evaluations.models import Evaluation
from apps.notifications.models import Notification
from apps.notifications.services import notify, notify_role, notify_team

from .models import Award

S = Application.Status
RESULTS = Award.Results
PIPELINE = [S.SUBMITTED, S.ACCEPTED, S.ASSIGNED, S.IN_REVIEW]     # still with staff or judges
OUTCOMES = {True: S.APPROVED, False: S.REJECTED}
LABEL = {S.APPROVED: "Successful", S.REJECTED: "Not successful"}


def _judged(qs):
    return qs.filter(assignments__evaluation__status=Evaluation.Status.SUBMITTED).distinct()


def preparer_label(award):
    manager = award.manager
    return manager.display_name if manager and manager.is_active else "the award's programme staff"


def can_prepare(user, award):
    """The award's manager; its programme staff only if it has no active manager."""
    manager = award.manager
    if manager is not None and manager.is_active:
        return user.pk == manager.pk
    return user.role == User.Role.STAFF and award.staff.filter(pk=user.pk).exists()


def state(award):
    """Where the award's result stands: the entries in each stage and what still blocks sending it."""
    entries = Application.objects.filter(award=award).exclude(status=S.DRAFT)
    in_pipeline = list(entries.filter(status__in=PIPELINE))
    to_decide = list(entries.filter(status=S.SCORED))
    decided = list(_judged(entries.filter(status__in=OUTCOMES.values(), result_published=False)))
    published = list(entries.filter(result_published=True))
    blockers = []
    if in_pipeline:
        blockers.append(f"{len(in_pipeline)} entr{'y is' if len(in_pipeline) == 1 else 'ies are'} still with staff "
                        f"or judges.")
    if to_decide:
        blockers.append(f"{len(to_decide)} scored entr{'y needs' if len(to_decide) == 1 else 'ies need'} a "
                        f"result (Successful or Not successful).")
    if not decided and not blockers:
        blockers.append("There is no new result to send.")
    if award.results_status == RESULTS.SUBMITTED:
        blockers = ["Waiting for leadership to approve it."]
    return {"in_pipeline": in_pipeline, "to_decide": to_decide, "decided": decided, "published": published,
            "blockers": blockers, "can_send": not blockers}


@transaction.atomic
def decide_entry(report, *, by, successful, note=""):
    """The award manager marks one scored entry Successful or Not successful (not published yet)."""
    award = Award.objects.select_related("manager").get(pk=report.award_id)   # its result state, fresh
    if not can_prepare(by, award):
        raise BusinessRuleError(f"{preparer_label(award)} decides each entry's result for {award.name}; "
                                f"leadership then approves the award's result as a whole.")
    if report.result_published:
        raise BusinessRuleError("This result is already published. It can only change through a re-evaluation.")
    if award.results_status == RESULTS.SUBMITTED:
        raise BusinessRuleError("The award's result is with leadership. It can change only if they send it back.")
    judged = _judged(Application.objects.filter(pk=report.pk)).exists()
    if report.status not in (S.SCORED, *OUTCOMES.values()) or not judged:
        raise BusinessRuleError("Only entries every judge has scored can get a result.")
    set_status(report, OUTCOMES[bool(successful)], by=by, note=note or "award manager's decision")
    return report


@transaction.atomic
def send_to_leadership(award, *, by, note=""):
    if not can_prepare(by, award):
        raise BusinessRuleError(f"{preparer_label(award)} sends {award.name}'s result to leadership.")
    blockers = state(award)["blockers"]
    if blockers:
        raise BusinessRuleError("Not ready to send: " + " ".join(blockers))
    award.results_status, award.results_note = RESULTS.SUBMITTED, (note or "").strip()
    award.results_submitted_by, award.results_submitted_at = by, timezone.now()
    award.results_decided_by = award.results_decided_at = None
    award.save()
    record(by, "status_change", award, changes={"results": RESULTS.SUBMITTED, "note": award.results_note})
    notify_role(User.Role.LEADER, f"{award.name}: the award's result is ready for your approval "
                f"(sent by {by.display_name}).", kind=Notification.Kind.REQUEST,
                link=reverse("dashboard:results") + f"?award={award.slug}")
    return award


def _check_leader(by, award):
    if not (by.role == User.Role.LEADER or by.is_superuser):
        raise BusinessRuleError("Only leadership approves an award's result.")
    if award.results_status != RESULTS.SUBMITTED:
        raise BusinessRuleError(f"{award.name}'s result isn't waiting for leadership.")


@transaction.atomic
def approve(award, *, by, note=""):
    """Approve the award's result as a whole: every decided entry is published and its applicant told."""
    _check_leader(by, award)
    newly = state(award)["decided"]
    for report in newly:
        report.result_published = True
        report.save(update_fields=["result_published", "updated_at"])
        notify(report.applicant, f"{award.name}: the results are out. {report.reference} was "
               f"{LABEL[report.status].lower()}.", kind=Notification.Kind.STATUS_CHANGE,
               link=reverse("core:results") + f"?award={award.slug}")
    award.results_status = RESULTS.APPROVED
    award.results_decided_by, award.results_decided_at = by, timezone.now()
    award.save()
    record(by, "status_change", award, changes={"results": RESULTS.APPROVED, "published": len(newly),
                                                "note": (note or "").strip()})
    notify_team(award, f"{award.name}: leadership approved the award's result. It is now on the results board.",
                kind=Notification.Kind.INFO, link=reverse("core:results") + f"?award={award.slug}")
    return award


@transaction.atomic
def send_back(award, *, by, note):
    _check_leader(by, award)
    if not (note or "").strip():
        raise BusinessRuleError("Say what needs another look: the award manager sees your note.")
    award.results_status, award.results_note = RESULTS.RETURNED, note.strip()
    award.results_decided_by, award.results_decided_at = by, timezone.now()
    award.save()
    record(by, "status_change", award, changes={"results": RESULTS.RETURNED, "note": award.results_note})
    notify_team(award, f"{award.name}: leadership sent the award's result back. Note: {award.results_note}",
                kind=Notification.Kind.REQUEST, link=reverse("awards:prepare_results") + f"?award={award.slug}")
    return award
