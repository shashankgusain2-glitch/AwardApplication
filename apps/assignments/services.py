"""
Judge assignment business logic: who may judge a report, assigning and
reassigning, judges accepting or declining, and staff-recorded conflicts.
"""
from django.db import transaction
from django.db.models import Count, Q

from apps.accounts.models import ApplicantProfile, User
from apps.applications.models import Application
from apps.applications.services import set_status
from apps.audit.services import record
from apps.core.services import BusinessRuleError
from apps.notifications.services import notify

from .models import ConflictOfInterest, JudgeAssignment

A = JudgeAssignment.Status
OPEN_STATUSES = [A.PENDING, A.IN_REVIEW]
ASSIGNABLE = [Application.Status.SUBMITTED, Application.Status.ASSIGNED, Application.Status.IN_REVIEW]


def visible_to(user):
    """Assignments this user may see. A judge only ever sees their own."""
    qs = JudgeAssignment.objects.select_related("judge", "report__award", "report__form_version", "assigned_by")
    if user.role == User.Role.JUDGE:
        return qs.filter(judge=user)
    if user.role in (User.Role.STAFF, User.Role.LEADER):
        return qs
    return qs.none()


def _profile(report):
    return ApplicantProfile.objects.filter(user=report.applicant).first()


def has_conflict(judge, report):
    profile = _profile(report)
    return bool(profile) and ConflictOfInterest.objects.filter(judge=judge, applicant_profile=profile).exists()


def eligible_judges(report, round=1):
    """
    Judges who may take this report, best first: active judges on the award's
    panel, no recorded conflict (Rule 2), not already on it, under their
    workload limit. Ordered by priority, then lightest workload.
    """
    taken = report.assignments.filter(round=round).values_list("judge_id", flat=True)
    profile = _profile(report)
    judges = (User.objects.filter(role=User.Role.JUDGE, is_active=True, judge_profile__awards=report.award)
              .exclude(id__in=taken)
              .annotate(open_count=Count("judge_assignments",
                                         filter=Q(judge_assignments__status__in=OPEN_STATUSES)))
              .select_related("judge_profile"))
    if profile:
        judges = judges.exclude(conflicts__applicant_profile=profile)
    judges = [j for j in judges if j.open_count < j.judge_profile.max_open_assignments]
    return sorted(judges, key=lambda j: (j.judge_profile.priority, j.open_count, j.email))


def _check_can_assign(by):
    if by.role not in (User.Role.STAFF, User.Role.LEADER):
        raise BusinessRuleError("Only staff or leaders can assign judges.")


@transaction.atomic
def assign(report, judge, *, by, round=1):
    _check_can_assign(by)
    if judge.role != User.Role.JUDGE:
        raise BusinessRuleError(f"{judge} isn't a judge.")
    if report.status not in ASSIGNABLE:
        raise BusinessRuleError("Only submitted reports can be assigned to judges.")
    profile = _profile(report)
    if not profile or profile.verification_status != ApplicantProfile.Verification.VERIFIED:
        raise BusinessRuleError("Staff must verify the applicant's organisation before assigning judges.")
    if has_conflict(judge, report):
        raise BusinessRuleError(f"{judge} has a recorded conflict with this organisation.")
    if judge not in eligible_judges(report, round):
        raise BusinessRuleError(f"{judge} can't take this report (not on the panel, already assigned, "
                                f"or at their workload limit).")
    assignment = JudgeAssignment.objects.create(judge=judge, report=report, round=round, assigned_by=by)
    if report.status == Application.Status.SUBMITTED:
        set_status(report, Application.Status.ASSIGNED, by=by)
    record(by, "assign", assignment, changes={"judge": judge.email, "report": report.reference, "round": round})
    notify(judge, f"New report to judge: {report.reference}", kind="assignment")
    return assignment


@transaction.atomic
def reassign(assignment, new_judge, *, by):
    """Move an unfinished assignment to another judge; the old one is kept as declined."""
    _check_can_assign(by)
    if assignment.status == A.COMPLETED:
        raise BusinessRuleError("A completed evaluation can't be reassigned.")
    old_judge = assignment.judge
    assignment.status = A.DECLINED
    assignment.save(update_fields=["status", "updated_at"])
    new = assign(assignment.report, new_judge, by=by, round=assignment.round)
    record(by, "reassign", new, changes={"from": old_judge.email, "to": new_judge.email})
    return new


@transaction.atomic
def bulk_assign(pairs, *, by, round=1):
    """
    Assign many (report, judge) pairs at once. All or nothing: if any pair
    breaks a rule, nothing is saved and the error names the pair.
    """
    made = []
    for n, (report, judge) in enumerate(pairs, start=1):
        try:
            made.append(assign(report, judge, by=by, round=round))
        except BusinessRuleError as error:
            raise BusinessRuleError(f"Item {n} ({report.reference} → {judge.email}): {error}") from None
    return made


def judges_still_needed(report, round=1):
    """How many more judges this report needs in this round (declined ones don't count)."""
    have = report.assignments.filter(round=round).exclude(status=A.DECLINED).count()
    return max(report.award.judges_per_report - have, 0)


@transaction.atomic
def auto_assign(report, *, by, round=1):
    """Fill the report up to the award's judges-per-report with the best eligible judges."""
    _check_can_assign(by)
    needed = judges_still_needed(report, round)
    if needed == 0:
        return []
    picks = eligible_judges(report, round)[:needed]
    if not picks:
        raise BusinessRuleError(f"{report.reference}: no eligible judges left (panel, conflicts, workload).")
    return [assign(report, judge, by=by, round=round) for judge in picks]


@transaction.atomic
def auto_assign_many(reports, *, by, round=1):
    made = []
    for report in reports:
        made += auto_assign(report, by=by, round=round)
    return made


def _own(assignment, judge):
    if assignment.judge_id != judge.id:
        raise BusinessRuleError("This assignment isn't yours.")


@transaction.atomic
def start_review(assignment, *, judge):
    """The judge accepts: they get access to grade the report."""
    _own(assignment, judge)
    if assignment.status == A.IN_REVIEW:
        return assignment
    if assignment.status != A.PENDING:
        raise BusinessRuleError("This assignment can't be started.")
    assignment.status = A.IN_REVIEW
    assignment.save(update_fields=["status", "updated_at"])
    if assignment.report.status == Application.Status.ASSIGNED:
        set_status(assignment.report, Application.Status.IN_REVIEW, by=judge)
    record(judge, "update", assignment, changes={"status": A.IN_REVIEW})
    return assignment


@transaction.atomic
def decline(assignment, *, judge):
    """Declined reports go back to the allocation pool (12 Oct meeting)."""
    _own(assignment, judge)
    if assignment.status != A.PENDING:
        raise BusinessRuleError("Only reports you haven't started can be declined.")
    assignment.status = A.DECLINED
    assignment.save(update_fields=["status", "updated_at"])
    report = assignment.report
    if not report.assignments.filter(status__in=OPEN_STATUSES + [A.COMPLETED]).exists():
        set_status(report, Application.Status.SUBMITTED, by=judge, note="back to the pool")
    record(judge, "update", assignment, changes={"status": A.DECLINED})
    return assignment


@transaction.atomic
def record_conflict(*, judge, profile, by, reason=""):
    """
    Staff record a conflict (judges don't declare them). Any unfinished
    assignment between that judge and organisation is withdrawn at once.
    """
    if by.role not in (User.Role.STAFF, User.Role.LEADER):
        raise BusinessRuleError("Only staff or leaders can record conflicts.")
    conflict, _ = ConflictOfInterest.objects.get_or_create(
        judge=judge, applicant_profile=profile, defaults={"reason": reason, "recorded_by": by})
    withdrawn = JudgeAssignment.objects.filter(judge=judge, report__applicant=profile.user, status__in=OPEN_STATUSES)
    for assignment in withdrawn:
        assignment.status = A.DECLINED
        assignment.save(update_fields=["status", "updated_at"])
        record(by, "update", assignment, changes={"status": A.DECLINED, "why": "conflict recorded"})
    record(by, "create", conflict, changes={"judge": judge.email, "organisation": profile.organisation_name})
    return conflict


def report_for_judge(assignment):
    """
    What the judge may see of the report.                          [Rule 1]
    In a blind award's desk-review round, identifying answers and the
    applicant's identity are removed here, before anything is sent.
    """
    report = assignment.report
    award = report.award
    round_obj = award.rounds.filter(number=assignment.round).first()
    blind = award.blind_judging and (round_obj is None or round_obj.kind == "desk")
    questions = report.form_version.questions
    hidden = {q["key"] for q in questions if q.get("identifying")} if blind else set()
    return {
        "reference": report.reference,
        "award": award.name,
        "title": report.title,
        "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
        "report_status": report.status,
        "blind": blind,
        "applicant": None if blind else report.applicant.display_name,
        "answers": [{"key": q["key"], "label": q["label"],
                     "value": None if q["key"] in hidden else report.content.get(q["key"], ""),
                     "hidden": q["key"] in hidden} for q in questions],
    }


def judge_home(user):
    """The judge's home page: only their own assignments, as they may see them (blind applied)."""
    rows = []
    for assignment in visible_to(user).prefetch_related("report__award__rounds").order_by("status", "-assigned_at"):
        round_obj = next((r for r in assignment.report.award.rounds.all() if r.number == assignment.round), None)
        rows.append({
            "assignment": assignment,
            "view": report_for_judge(assignment),
            "round_label": round_obj.get_kind_display() if round_obj else f"Round {assignment.round}",
        })
    counts = {s: sum(1 for r in rows if r["assignment"].status == s) for s in A.values}
    return {"rows": rows, "counts": counts, "total": len(rows)}
