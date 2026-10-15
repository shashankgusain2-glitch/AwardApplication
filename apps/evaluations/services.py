"""
Evaluation business logic: judges score only their own assignments, can
save midway, and change submitted scores only with staff permission and a
reason (every change recorded).
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.applications.models import Application
from apps.applications.services import set_status
from apps.assignments.models import JudgeAssignment
from apps.assignments.services import start_review
from apps.audit.services import record
from apps.awards.access import awards_for
from apps.awards.models import Criterion
from apps.core.services import BusinessRuleError
from apps.notifications.models import Notification
from apps.notifications.services import notify_team

from .models import CriterionScore, Evaluation, ScoreChange, ScoreChangeRequest

A = JudgeAssignment.Status
REPLACED = ("This report is being re-evaluated by other judges, so your scores are kept as they were "
            "and can't change.")


def assignment_progress(assignment):
    """How much of the report this judge has judged, 0-100 (submitted = 100; declined = 0)."""
    if assignment.status in (A.DECLINED, A.SUPERSEDED):
        return 0
    evaluation = Evaluation.objects.filter(assignment=assignment).first()
    if evaluation and evaluation.status == Evaluation.Status.SUBMITTED:
        return 100
    needed = Criterion.objects.filter(award_id=assignment.report.award_id, round_number=assignment.round).count()
    if not needed or not evaluation:
        return 0
    return round(min(evaluation.scores.count(), needed) * 100 / needed)


def report_progress(report):
    """
    How much of a report has been judged in its current round, 0-100, across all its judges:
    scores given ÷ (judges the award needs × criteria in the round). Judges still to be
    assigned count as nothing done yet, so 2 of 3 judges finished = 67%.
    """
    if report.status in (Application.Status.SCORED, Application.Status.APPROVED):
        return 100
    assignments = [a for a in report.assignments.all() if a.status not in (A.DECLINED, A.SUPERSEDED)]
    if not assignments:
        return 0
    current = max(a.round for a in assignments)
    in_round = [a for a in assignments if a.round == current]
    slots = max(report.award.judges_per_report, len(in_round))
    return round(sum(assignment_progress(a) for a in in_round) / slots)


def applicant_progress(report):
    """
    What the applicant may know while judges work: counts only, never who the judges
    are or what they scored. None when the report isn't with judges.
    """
    if report.status not in (Application.Status.ASSIGNED, Application.Status.IN_REVIEW):
        return None
    live = [a for a in report.assignments.all() if a.status not in (A.DECLINED, A.SUPERSEDED)]
    if not live:
        return None
    current = max(a.round for a in live)
    in_round = [a for a in live if a.round == current]
    finished = sum(a.status == A.COMPLETED for a in in_round)
    started = sum(a.status == A.IN_REVIEW for a in in_round)
    needed = max(report.award.judges_per_report, len(in_round))
    round_obj = next((r for r in report.award.rounds.all() if r.number == current), None)
    return {"round": current, "round_label": round_obj.get_kind_display() if round_obj else f"Round {current}",
            "needed": needed, "finished": finished, "started": started,
            "waiting": max(needed - finished - started, 0), "percent": report_progress(report)}


def visible_to(user):
    qs = Evaluation.objects.select_related("assignment__judge", "assignment__report").prefetch_related("scores")
    if user.role == User.Role.JUDGE:
        return qs.filter(assignment__judge=user)
    if user.role == User.Role.LEADER:
        return qs
    if user.role in (User.Role.STAFF, User.Role.MANAGER):
        return qs.filter(assignment__report__award__in=awards_for(user))   # only the awards they are on
    return qs.none()


def criteria_for(assignment):
    return {c.key: c for c in Criterion.objects.filter(award=assignment.report.award, round_number=assignment.round)}


def compute_total(evaluation):
    """Weighted total out of 10: sum(weight × score) / 100."""
    total = Decimal(0)
    for s in evaluation.scores.select_related("criterion"):
        total += Decimal(s.criterion.weight) * s.score
    return (total / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _own(assignment, judge):
    if judge.role != User.Role.JUDGE or assignment.judge_id != judge.id:
        raise BusinessRuleError("You can only evaluate reports assigned to you.")


def _clean_scores(assignment, scores):
    criteria = criteria_for(assignment)
    unknown = set(scores) - set(criteria)
    if unknown:
        raise BusinessRuleError(f"Unknown criteria: {', '.join(sorted(unknown))}.")
    for key, value in scores.items():
        score = value["score"] if isinstance(value, dict) else value
        # bool is a kind of int in Python: true/false must not count as 1/0
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 10:
            raise BusinessRuleError(f"{criteria[key].label}: score must be a whole number from 1 to 10.")
    return criteria


@transaction.atomic
def save(assignment, *, judge, scores, feedback=None, submit=False):
    """
    Save scores (partial is fine: grading is saved midway). Submitting needs
    every criterion and locks the evaluation.
    scores: {criterion_key: score} or {criterion_key: {"score": 8, "comment": "..."}}
    """
    _own(assignment, judge)
    if assignment.status == A.DECLINED:
        raise BusinessRuleError("This assignment was declined.")
    if assignment.status == A.SUPERSEDED:
        raise BusinessRuleError(REPLACED)
    if assignment.status == A.PENDING:
        start_review(assignment, judge=judge)
    evaluation, _ = Evaluation.objects.get_or_create(assignment=assignment)
    if evaluation.status == Evaluation.Status.SUBMITTED:
        raise BusinessRuleError("This evaluation is submitted. Ask staff for permission to change it.")
    criteria = _clean_scores(assignment, scores)
    for key, value in scores.items():
        score, comment = (value["score"], value.get("comment", "")) if isinstance(value, dict) else (value, "")
        CriterionScore.objects.update_or_create(evaluation=evaluation, criterion=criteria[key],
                                                defaults={"score": score, "comment": comment})
    if feedback is not None:
        evaluation.feedback = feedback
    evaluation.total_score = compute_total(evaluation)
    if submit:
        missing = set(criteria) - set(evaluation.scores.values_list("criterion__key", flat=True))
        if missing:
            raise BusinessRuleError("Score every criterion before submitting. Your scores so far are saved.")
        evaluation.status = Evaluation.Status.SUBMITTED
        evaluation.submitted_at = timezone.now()
        assignment.status = A.COMPLETED
        assignment.save(update_fields=["status", "updated_at"])
    evaluation.save()
    if submit:
        record(judge, "score", evaluation, changes={"total": str(evaluation.total_score),
                                                    "report": assignment.report.reference})
        _maybe_mark_scored(assignment.report, judge)
    return evaluation


def _maybe_mark_scored(report, by):
    done = report.assignments.filter(round=1, status=A.COMPLETED).count()
    if done >= report.award.judges_per_report and report.status in (Application.Status.ASSIGNED,
                                                                     Application.Status.IN_REVIEW):
        set_status(report, Application.Status.SCORED, by=by, note="all judges submitted")


RESULT_DECIDED = ("The result for this report has already been decided, so scores can't change any more. "
                  "The applicant can ask for a re-evaluation instead.")


def _result_decided(report):
    return report.status in (Application.Status.APPROVED, Application.Status.REJECTED)


@transaction.atomic
def request_change(evaluation, *, judge, reason):
    """A judge asks to change a submitted evaluation: staff check it, then a leader confirms it."""
    _own(evaluation.assignment, judge)
    if evaluation.assignment.status == A.SUPERSEDED:
        raise BusinessRuleError(REPLACED)
    if evaluation.status != Evaluation.Status.SUBMITTED:
        raise BusinessRuleError("Only submitted evaluations need permission to change.")
    if _result_decided(evaluation.assignment.report):
        raise BusinessRuleError(RESULT_DECIDED)
    if not reason.strip():
        raise BusinessRuleError("Give a reason for the change.")
    if evaluation.change_requests.filter(status__in=[ScoreChangeRequest.Status.REQUESTED,
                                                     ScoreChangeRequest.Status.STAFF_APPROVED,
                                                     ScoreChangeRequest.Status.APPROVED]).exists():
        raise BusinessRuleError("You already have a request waiting or approved.")
    req = ScoreChangeRequest.objects.create(evaluation=evaluation, reason=reason.strip())
    record(judge, "update", req, changes={"reason": reason.strip()})
    notify_team(evaluation.assignment.report.award, f"{_what(evaluation.assignment)}: {judge.display_name} asks. "
                f"Reason: {reason.strip()} Check it, then it goes to leadership to confirm.",
                kind=Notification.Kind.REQUEST, link=reverse("awards:entries"))
    return req


def _what(assignment):
    report = assignment.report
    return f"{report.reference} ({report.award.name}) · Score change by {assignment.judge.display_name}"


@transaction.atomic
def decide_change(change_request, *, by, approve, note=""):
    """The next step: staff check it, then a leader confirms. Only the leader's yes lets the judge change."""
    from apps.core import approvals

    assignment = change_request.evaluation.assignment
    if approve and _result_decided(assignment.report):
        raise BusinessRuleError(f"{assignment.report.reference}: {RESULT_DECIDED} Refuse this request.")
    if approve and assignment.status == A.SUPERSEDED:
        raise BusinessRuleError(f"{assignment.report.reference}: {REPLACED} Refuse this request.")
    approvals.step(change_request, by=by, approve=approve, note=note)
    approvals.tell(change_request, requester=assignment.judge, what=_what(assignment),
                   link=reverse("judging:score", args=[assignment.pk]),
                   effect="You can now change your scores; give a reason for each change (it is recorded).")
    return change_request


@transaction.atomic
def change_scores(evaluation, *, judge, scores, reason):
    """Change submitted scores. Needs an approved request and a reason.   [Rule 3]"""
    assignment = evaluation.assignment
    _own(assignment, judge)
    if assignment.status == A.SUPERSEDED:
        raise BusinessRuleError(REPLACED)
    if _result_decided(assignment.report):
        raise BusinessRuleError(RESULT_DECIDED)
    approved = evaluation.change_requests.filter(status=ScoreChangeRequest.Status.APPROVED).first()
    if approved is None:
        raise BusinessRuleError("Ask for permission (staff, then leadership) before changing a submitted evaluation.")
    if not reason.strip():
        raise BusinessRuleError("Give a reason for the change.")
    criteria = _clean_scores(assignment, scores)
    current = {s.criterion.key: s for s in evaluation.scores.select_related("criterion")}
    changes = []
    for key, value in scores.items():
        new = value["score"] if isinstance(value, dict) else value
        score = current.get(key)
        if score is None or score.score == new:
            continue
        ScoreChange.objects.create(evaluation=evaluation, criterion=criteria[key], old_score=score.score,
                                   new_score=new, reason=reason, changed_by=judge, request=approved)
        changes.append({"criterion": key, "from": score.score, "to": new})
        score.score = new
        score.save(update_fields=["score"])
    evaluation.total_score = compute_total(evaluation)
    evaluation.save(update_fields=["total_score", "updated_at"])
    approved.status = ScoreChangeRequest.Status.USED
    approved.save(update_fields=["status", "updated_at"])
    record(judge, "score_change", evaluation, changes={"reason": reason, "changes": changes})
    return evaluation
