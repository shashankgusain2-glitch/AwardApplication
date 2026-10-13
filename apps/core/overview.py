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

S = Application.Status
UNDER_EVALUATION = [S.ASSIGNED, S.IN_REVIEW]


def _per_award():
    rows = []
    awards = Award.objects.prefetch_related("rounds").annotate(
        drafts=Count("applications", filter=Q(applications__status=S.DRAFT, applications__is_deleted=False)),
        submitted=Count("applications", filter=Q(applications__status=S.SUBMITTED, applications__is_deleted=False)),
        evaluating=Count("applications", filter=Q(applications__status__in=UNDER_EVALUATION,
                                                  applications__is_deleted=False)),
        scored=Count("applications", filter=Q(applications__status=S.SCORED, applications__is_deleted=False)),
        approved=Count("applications", filter=Q(applications__status=S.APPROVED, applications__is_deleted=False)),
        rejected=Count("applications", filter=Q(applications__status=S.REJECTED, applications__is_deleted=False)),
    )
    for award in awards:
        live = JudgeAssignment.objects.filter(report__award=award).exclude(status=JudgeAssignment.Status.DECLINED)
        total, done = live.count(), live.filter(status=JudgeAssignment.Status.COMPLETED).count()
        rows.append({
            "award": award,
            "entries": award.submitted + award.evaluating + award.scored + award.approved + award.rejected,
            "progress": round(done * 100 / total) if total else 0,
            "evaluations_done": done, "evaluations_total": total,
        })
    return rows


def staff_home():
    return {
        "to_verify": ApplicantProfile.objects.filter(verification_status=ApplicantProfile.Verification.PENDING)
                                             .select_related("user"),
        "unassigned": Application.objects.filter(status=S.SUBMITTED).select_related("award", "applicant"),
        "score_requests": ScoreChangeRequest.objects.filter(status=ScoreChangeRequest.Status.REQUESTED).count(),
        "edit_requests": Application.objects.filter(edit_requested=True).count(),
        "awards": _per_award(),
    }


def leader_overview():
    reports = Application.objects.exclude(status=S.DRAFT)
    return {
        "total": reports.count(),
        "evaluating": reports.filter(status__in=UNDER_EVALUATION).count(),
        "awaiting_approval": reports.filter(status=S.SCORED).count(),
        "decided": reports.filter(status__in=[S.APPROVED, S.REJECTED]).count(),
        "score_requests": ScoreChangeRequest.objects.filter(status=ScoreChangeRequest.Status.REQUESTED).count(),
        "awards": _per_award(),
    }
