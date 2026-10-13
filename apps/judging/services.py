"""
The judging rules, in one place. Views call these; they never change
assignments, scores or statuses directly.
"""
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.core.models import log
from apps.entries.models import Application

from .models import Assignment, Conflict, JudgeProfile, Round2Meeting, Score, ScoreChange, ScoreChangeRequest

A = Assignment.Status
S = Application.Status
LOGIN_SALT = "judge-login"
LOGIN_LINK_DAYS = 7


class RuleError(Exception):
    """An action that breaks a rule; shown to the user as a message."""


# --- Judge login link (the email that starts the judge's workflow) ----------

def login_link(judge, request=None):
    token = signing.dumps(judge.user_id, salt=LOGIN_SALT)
    path = reverse("judging:login", args=[token])
    return request.build_absolute_uri(path) if request else path


def user_id_from_token(token):
    return signing.loads(token, salt=LOGIN_SALT, max_age=LOGIN_LINK_DAYS * 24 * 3600)


def email_judge(judge, subject, text, request=None):
    link = login_link(judge, request)
    send_mail(subject, f"{text}\n\nOpen your judging tab: {link}", None, [judge.user.email])
    return link


# --- Who can judge a report --------------------------------------------------

def is_conflicted(judge, application):
    return Conflict.objects.filter(judge=judge, organisation=application.organisation).exists()


def active_assignments(application, round_no=1):
    return application.assignments.filter(round=round_no, status__in=[A.OFFERED, A.ACCEPTED, A.COMPLETED])


def suggested_judges(application, round_no=1):
    """
    Judges who may grade this report, best first:
    on the event's panel, no conflict (Rule 2), not already on it,
    not declined it before, and not over their workload limit.
    Ordered by priority, then lightest workload.
    """
    taken = application.assignments.filter(round=round_no).values_list("judge_id", flat=True)
    candidates = []
    for judge in application.award.judges.exclude(id__in=taken):
        if is_conflicted(judge, application) or judge.open_load >= judge.max_load:
            continue
        candidates.append(judge)
    return sorted(candidates, key=lambda j: (j.priority, j.open_load, j.name))


def judges_still_needed(application):
    return max(0, application.award.judges_per_report - active_assignments(application).count())


# --- Staff actions ----------------------------------------------------------

def confirm(application, by):
    if application.status != S.SUBMITTED:
        raise RuleError("Only submitted reports can be confirmed.")
    application.status = S.POOL
    application.save()
    log(by, "Confirmed the report and added it to the report pool", application)


def reject(application, by, reason):
    if application.status != S.SUBMITTED:
        raise RuleError("Only submitted reports can be rejected.")
    application.status = S.REJECTED
    application.save()
    log(by, f"Rejected the report (failed proof check): {reason}", application)


@transaction.atomic
def assign(application, judges, by, request=None):
    """Offer the report to these judges. Conflicted judges are refused, always."""
    if application.status not in (S.POOL, S.ASSIGNED, S.JUDGING):
        raise RuleError("Only confirmed reports in the pool can be assigned.")
    for judge in judges:
        if is_conflicted(judge, application):
            raise RuleError(f"{judge} has a recorded conflict with {application.organisation} and can't be assigned.")
        if judge not in suggested_judges(application):
            raise RuleError(f"{judge} can't take this report (not on the panel, already on it, or at their limit).")
        Assignment.objects.create(application=application, judge=judge, round=1)
        email_judge(judge, "A report has been assigned to you",
                    f"{application.award}: please accept or decline the report.", request)
        log(by, f"Assigned to {judge}", application)
    if judges and application.status == S.POOL:
        application.status = S.ASSIGNED
        application.save()


def auto_assign(application, by, request=None):
    """Pick the best judges until the report has as many as the event needs."""
    picks = suggested_judges(application)[:judges_still_needed(application)]
    if not picks:
        raise RuleError("No free judges without a conflict are available for this report.")
    assign(application, picks, by, request)
    return picks


def shortlist(application, by):
    if application.status != S.JUDGED:
        raise RuleError("Only judged reports can be shortlisted.")
    application.status = S.SHORTLISTED
    application.save()
    log(by, "Shortlisted for Round 2", application)


@transaction.atomic
def schedule_round2(application, when, link, judges, by, request=None):
    if application.status != S.SHORTLISTED:
        raise RuleError("Only shortlisted reports can have a Round 2 meeting.")
    if not judges:
        raise RuleError("Choose at least one judge for the meeting.")
    for judge in judges:
        if is_conflicted(judge, application):
            raise RuleError(f"{judge} has a recorded conflict with {application.organisation}.")
    Round2Meeting.objects.update_or_create(application=application,
                                           defaults={"scheduled_at": when, "meeting_link": link})
    for judge in judges:
        Assignment.objects.get_or_create(application=application, judge=judge, round=2,
                                         defaults={"status": A.ACCEPTED})
        email_judge(judge, "Round 2 meeting", f"{application.award}: online meeting on {when:%d %b %Y %H:%M}.", request)
    log(by, f"Scheduled Round 2 meeting with {', '.join(str(j) for j in judges)}", application)


def decide_change_request(change_request, approve, by):
    if change_request.status != ScoreChangeRequest.Status.REQUESTED:
        raise RuleError("This request has already been decided.")
    change_request.status = (ScoreChangeRequest.Status.APPROVED if approve
                             else ScoreChangeRequest.Status.DECLINED)
    change_request.decided_by = by
    change_request.decided_at = timezone.now()
    change_request.save()
    assignment = change_request.assignment
    assignment.change_allowed = approve
    assignment.save()
    log(by, f"{'Allowed' if approve else 'Refused'} {assignment.judge} to change scores", assignment.application)


# --- Judge actions -----------------------------------------------------------

def accept(assignment):
    if assignment.status != A.OFFERED:
        raise RuleError("This report is not waiting for your answer.")
    assignment.status = A.ACCEPTED
    assignment.save()
    application = assignment.application
    if application.status == S.ASSIGNED:
        application.status = S.JUDGING
        application.save()
    log(assignment.judge.user, "Accepted the report", application)


def decline(assignment):
    """Declined reports go back to the report allocation pool."""
    if assignment.status != A.OFFERED:
        raise RuleError("This report is not waiting for your answer.")
    assignment.status = A.DECLINED
    assignment.save()
    application = assignment.application
    if not active_assignments(application).exists():
        application.status = S.POOL
        application.save()
    log(assignment.judge.user, "Declined the report; it goes back to the pool", application)


@transaction.atomic
def save_scores(assignment, values, comments, submit=False):
    """
    Save some or all scores (partial grading is kept).
    Submitting needs every criterion scored, then the grading is locked.
    """
    if assignment.status != A.ACCEPTED:
        raise RuleError("You can only grade a report you have accepted and not yet submitted.")
    for c in assignment.criteria:
        value = values.get(c["key"])
        if value is None:
            continue
        Score.objects.update_or_create(assignment=assignment, criterion=c["key"],
                                       defaults={"value": value, "comment": comments.get(c["key"], "")})
    if submit:
        if assignment.scores.count() < len(assignment.criteria):
            raise RuleError("Score every part before submitting. Your scores so far are saved.")
        assignment.status = A.COMPLETED
        assignment.completed_at = timezone.now()
        assignment.save()
        log(assignment.judge.user, f"Submitted Round {assignment.round} grades", assignment.application)
        _update_after_grading(assignment.application, assignment.round)


def _update_after_grading(application, round_no):
    award = application.award
    done = application.assignments.filter(round=round_no, status=A.COMPLETED).count()
    if round_no == 1 and done >= award.judges_per_report and application.status == S.JUDGING:
        application.status = S.JUDGED
        application.save()
        log(None, "All judges have graded: report judged", application)
    if round_no == 2 and not application.assignments.filter(round=2).exclude(status=A.COMPLETED).exists():
        application.status = S.ROUND2_DONE
        application.save()
        log(None, "Round 2 graded", application)


def request_change(assignment, reason):
    if assignment.status != A.COMPLETED:
        raise RuleError("You can only ask to change a report you have already graded.")
    if assignment.change_requests.filter(status__in=["requested", "approved"]).exists():
        raise RuleError("You already have a request waiting or approved.")
    if not reason.strip():
        raise RuleError("Give a reason for the change.")
    ScoreChangeRequest.objects.create(assignment=assignment, reason=reason)
    log(assignment.judge.user, f"Asked staff to change scores: {reason}", assignment.application)


@transaction.atomic
def change_scores(assignment, values, reason, by):
    """
    Change scores of a graded report. Needs staff approval first, and a reason.  [Rule 3]
    Every changed part is recorded: who, when, old value, new value, why.
    """
    approved = assignment.change_requests.filter(status=ScoreChangeRequest.Status.APPROVED).first()
    if not (assignment.change_allowed and approved):
        raise RuleError("Ask staff for permission before changing a graded report.")
    if not reason.strip():
        raise RuleError("Give a reason for the change.")
    current = assignment.scores_by_key
    changed = 0
    for key, new in values.items():
        score = current.get(key)
        if score is None or new is None or new == score.value:
            continue
        ScoreChange.objects.create(assignment=assignment, criterion=key, old_value=score.value, new_value=new,
                                   reason=reason, changed_by=by, request=approved)
        score.value = new
        score.save()
        changed += 1
    approved.status = ScoreChangeRequest.Status.USED
    approved.save()
    assignment.change_allowed = False
    assignment.save()
    log(by, f"Changed {changed} score(s): {reason}", assignment.application)
    return changed


def get_or_create_judge(email, name, expertise, priority, max_load, panels):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user, _ = User.objects.get_or_create(email=email.lower(), defaults={"username": email.lower()})
    judge, _ = JudgeProfile.objects.update_or_create(
        user=user, defaults={"name": name, "expertise": expertise, "priority": priority, "max_load": max_load})
    judge.panels.set(panels)
    return judge
