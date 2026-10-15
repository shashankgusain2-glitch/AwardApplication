"""
Read-only summaries for the staff and leader home pages, from the real
database. Nothing here changes data.
"""
from django.db.models import Count, Q

from apps.accounts.models import ApplicantProfile
from apps.applications.models import Application
from apps.assignments.models import JudgeAssignment
from apps.awards.models import Award
from apps.evaluations.models import ScoreChangeRequest

from . import approvals

S = Application.Status
UNDER_EVALUATION = [S.ASSIGNED, S.IN_REVIEW]


def _per_award(awards=None):
    rows = []
    awards = (Award.objects.all() if awards is None else awards)
    awards = awards.select_related("manager").prefetch_related("rounds").annotate(
        drafts=Count("applications", filter=Q(applications__status=S.DRAFT, applications__is_deleted=False)),
        submitted=Count("applications", filter=Q(applications__status=S.SUBMITTED, applications__is_deleted=False)),
        evaluating=Count("applications", filter=Q(applications__status__in=UNDER_EVALUATION,
                                                  applications__is_deleted=False)),
        scored=Count("applications", filter=Q(applications__status=S.SCORED, applications__is_deleted=False)),
        approved=Count("applications", filter=Q(applications__status=S.APPROVED, applications__is_deleted=False)),
        rejected=Count("applications", filter=Q(applications__status=S.REJECTED, applications__is_deleted=False)),
    )
    for award in awards:
        live = JudgeAssignment.objects.filter(report__award=award).exclude(
            status__in=[JudgeAssignment.Status.DECLINED, JudgeAssignment.Status.SUPERSEDED])
        total, done = live.count(), live.filter(status=JudgeAssignment.Status.COMPLETED).count()
        rows.append({
            "award": award,
            "entries": award.submitted + award.evaluating + award.scored + award.approved + award.rejected,
            "progress": round(done * 100 / total) if total else 0,
            "evaluations_done": done, "evaluations_total": total,
        })
    return rows


def needing_judges(user=None):
    """
    Reports that still need judges in round 1: submitted ones with none yet, and ones
    with too few (a judge declined, or conflicts left too few eligible judges).
    With a user: only reports on the awards they may work on.
    """
    from apps.applications.services import visible_to
    from apps.assignments.services import ASSIGNABLE, judges_still_needed
    rows = []
    reports = Application.objects.all() if user is None else visible_to(user)
    for report in (reports.filter(status__in=ASSIGNABLE)
                   .select_related("award", "applicant__applicant_profile").order_by("submitted_at")):
        missing = judges_still_needed(report)
        if missing:
            rows.append({"report": report, "missing": missing,
                         "have": report.award.judges_per_report - missing})
    return rows


def organisations_for(user):
    """
    Applicant organisations this person may check: a leader sees all of them; staff and
    award managers the ones that have applied to one of their awards.
    """
    from apps.awards.access import awards_for, sees_every_award
    profiles = ApplicantProfile.objects.select_related("user")
    if sees_every_award(user):
        return profiles
    return profiles.filter(user__applications__award__in=awards_for(user)).distinct()


def organisations_to_verify(user):
    """Organisations waiting for the staff check, among the ones this person may check."""
    return organisations_for(user).filter(verification_status=ApplicantProfile.Verification.PENDING)


def staff_home(user):
    """The staff / award manager home page: only the awards this person is on."""
    from apps.awards.access import awards_for
    return {
        "to_verify": organisations_to_verify(user),
        "needing_judges": needing_judges(user),
        "staff_requests": len(approvals.waiting(approvals.T.WAITING_STAFF, user)),
        "leader_requests": len(approvals.waiting(approvals.T.WAITING_LEADER, user)),
        "awards": _per_award(awards_for(user)),
    }


def leader_overview():
    reports = Application.objects.exclude(status=S.DRAFT)
    return {
        "total": reports.count(),
        "evaluating": reports.filter(status__in=UNDER_EVALUATION).count(),
        "awaiting_approval": reports.filter(status=S.SCORED).count(),
        "decided": reports.filter(status__in=[S.APPROVED, S.REJECTED]).count(),
        "leader_requests": len(approvals.waiting(approvals.T.WAITING_LEADER)),
        "awards": _per_award(),
    }


# --- API: GET /api/v1/dashboard/summary/ --------------------------------------

def _counts(queryset, field, choices):
    found = dict(queryset.values_list(field).annotate(n=Count("id")).values_list(field, "n"))
    return {value: found.get(value, 0) for value, _ in choices}


def _award_rows(awards=None):
    return [{"slug": r["award"].slug, "name": r["award"].name, "status": r["award"].status,
             "drafts": r["award"].drafts, "entries": r["entries"], "evaluating": r["award"].evaluating,
             "scored": r["award"].scored, "approved": r["award"].approved, "rejected": r["award"].rejected,
             "evaluations_done": r["evaluations_done"], "evaluations_total": r["evaluations_total"],
             "progress": r["progress"]} for r in _per_award(awards)]


def summary_for(user):
    """
    Counts by status for the logged-in user's dashboard. Each role only gets
    numbers about what it may see: applicants their own reports, judges
    their own assignments, staff and award managers the awards they are on,
    leaders the whole event.
    """
    from apps.accounts.models import User
    from apps.applications.services import visible_to as reports_visible_to
    from apps.assignments.services import visible_to as assignments_visible_to

    if user.role == User.Role.APPLICANT:
        mine = reports_visible_to(user)
        return {"role": user.role, "total": mine.count(),
                "applications_by_status": _counts(mine, "status", S.choices)}
    if user.role == User.Role.JUDGE:
        mine = assignments_visible_to(user)
        return {"role": user.role, "total": mine.count(),
                "assignments_by_status": _counts(mine, "status", JudgeAssignment.Status.choices)}
    from apps.awards.access import awards_for
    from apps.evaluations.services import visible_to as evaluations_visible_to

    reports = reports_visible_to(user)
    return {
        "role": user.role,
        "total": reports.exclude(status=S.DRAFT).count(),
        "applications_by_status": _counts(reports, "status", S.choices),
        "organisations_to_verify": organisations_to_verify(user).count(),
        "submitted_without_judges": reports.filter(status=S.SUBMITTED).count(),
        "score_change_requests": ScoreChangeRequest.objects.filter(
            status=ScoreChangeRequest.Status.REQUESTED,
            evaluation__in=evaluations_visible_to(user)).count(),
        "edit_requests": reports.filter(edit_requested=True).count(),
        "awards": _award_rows(awards_for(user)),
    }
