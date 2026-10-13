"""
Evaluation business logic: judges score only their own assignments, can
save midway, and change submitted scores only with staff permission and a
reason (every change recorded).
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.applications.models import Application
from apps.applications.services import set_status
from apps.assignments.models import JudgeAssignment
from apps.assignments.services import start_review
from apps.audit.services import record
from apps.awards.models import Criterion
from apps.core.services import BusinessRuleError

from .models import CriterionScore, Evaluation, ScoreChange, ScoreChangeRequest

A = JudgeAssignment.Status


def visible_to(user):
    qs = Evaluation.objects.select_related("assignment__judge", "assignment__report").prefetch_related("scores")
    if user.role == User.Role.JUDGE:
        return qs.filter(assignment__judge=user)
    if user.role in (User.Role.STAFF, User.Role.LEADER):
        return qs
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
        if not isinstance(score, int) or not 1 <= score <= 10:
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
    if assignment.status in (A.DECLINED,):
        raise BusinessRuleError("This assignment was declined.")
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


@transaction.atomic
def request_change(evaluation, *, judge, reason):
    _own(evaluation.assignment, judge)
    if evaluation.status != Evaluation.Status.SUBMITTED:
        raise BusinessRuleError("Only submitted evaluations need permission to change.")
    if not reason.strip():
        raise BusinessRuleError("Give a reason for the change.")
    if evaluation.change_requests.filter(status__in=["requested", "approved"]).exists():
        raise BusinessRuleError("You already have a request waiting or approved.")
    req = ScoreChangeRequest.objects.create(evaluation=evaluation, reason=reason)
    record(judge, "update", req, changes={"reason": reason})
    return req


@transaction.atomic
def decide_change(change_request, *, by, approve):
    if by.role not in (User.Role.STAFF, User.Role.LEADER):
        raise BusinessRuleError("Only staff or leaders can allow score changes.")
    if change_request.status != ScoreChangeRequest.Status.REQUESTED:
        raise BusinessRuleError("This request has already been decided.")
    change_request.status = ScoreChangeRequest.Status.APPROVED if approve else ScoreChangeRequest.Status.DECLINED
    change_request.decided_by = by
    change_request.decided_at = timezone.now()
    change_request.save()
    record(by, "update", change_request, changes={"status": change_request.status})
    return change_request


@transaction.atomic
def change_scores(evaluation, *, judge, scores, reason):
    """Change submitted scores. Needs an approved request and a reason.   [Rule 3]"""
    assignment = evaluation.assignment
    _own(assignment, judge)
    approved = evaluation.change_requests.filter(status=ScoreChangeRequest.Status.APPROVED).first()
    if approved is None:
        raise BusinessRuleError("Ask staff for permission before changing a submitted evaluation.")
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
