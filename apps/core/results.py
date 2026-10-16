"""
The results board (/results/): decided results per award, for every role.

    staff, managers  the full ranking of the awards they are on
    leaders          the full ranking of every award
    applicants       the successful entries, plus their own entry whatever its result
    judges           the successful entries

A result is out once leadership approves the award's result (the award manager decided each
scored entry: successful or not successful), which publishes it. Entries declined at the
staff check were never judged and aren't listed. The score is the average of the judges'
submitted totals. After a re-evaluation is approved the first judges' scores stop counting
(they are "Replaced"); the entry is listed as being re-evaluated, with its old result, until
leadership approves the award's updated result.
"""
from django.db.models import Avg, Count, Q

from apps.accounts.models import User
from apps.applications.models import Application
from apps.awards.access import awards_for
from apps.awards.models import Award
from apps.evaluations.models import Evaluation

S = Application.Status
R = Application.Reevaluation
DECIDED = [S.APPROVED, S.REJECTED]
COUNTED = Q(assignments__evaluation__status=Evaluation.Status.SUBMITTED) & ~Q(assignments__status="superseded")
JUDGED = Q(assignments__evaluation__status=Evaluation.Status.SUBMITTED)    # by anyone, replaced judges included
RESULT_LABEL = {S.APPROVED: "Successful", S.REJECTED: "Not successful"}


def sees_full_board(user, award):
    return user.role in (User.Role.STAFF, User.Role.MANAGER, User.Role.LEADER) and \
        awards_for(user).filter(pk=award.pk).exists()


def _on_board():
    """Published results (leadership approved the award's result), or entries being re-evaluated after one."""
    judged = Application.objects.filter(JUDGED).values("pk")
    return (Q(status__in=DECIDED) & Q(result_published=True) & Q(pk__in=judged)) | Q(reevaluation_status=R.ALLOWED)


def awards_with_results(user):
    awards = Award.objects.filter(applications__in=Application.objects.filter(_on_board())).distinct()
    if user.role in (User.Role.STAFF, User.Role.MANAGER):
        awards = awards.filter(pk__in=awards_for(user))
    return awards.order_by("name")


def board(user, award):
    """{"rows": ranked decided entries, "in_progress": entries being re-evaluated, "full": bool}."""
    full = sees_full_board(user, award)
    reports = (Application.objects.filter(award=award).filter(_on_board())
               .select_related("applicant__applicant_profile")
               .prefetch_related("requests")
               .annotate(average=Avg("assignments__evaluation__total_score", filter=COUNTED),
                         judged=Count("assignments__evaluation", filter=COUNTED, distinct=True)))
    decided = sorted([r for r in reports if r.status in DECIDED and r.result_published],
                     key=lambda r: (r.status != S.APPROVED, -(r.average or 0), r.reference))
    rank, previous = 0, None
    for n, report in enumerate(decided, start=1):
        key = (report.status, report.average)
        if key != previous:
            rank, previous = n, key
        report.rank = rank
        report.result_label = RESULT_LABEL[report.status]
        report.reevaluated = report.reevaluation_status == R.ALLOWED
        report.previous_label = RESULT_LABEL.get(report.reevaluation_previous_result, "")
        report.mine = report.applicant_id == user.pk
        report.open_request = next((q for q in report.requests.all()
                                    if q.kind == "reevaluation" and q.waiting), None)
    in_progress = [r for r in reports if not (r.status in DECIDED and r.result_published)]
    for report in in_progress:
        report.previous_label = RESULT_LABEL.get(report.reevaluation_previous_result, "")
        report.mine = report.applicant_id == user.pk
    if not full:
        decided = [r for r in decided if r.status == S.APPROVED or r.mine]
        in_progress = [r for r in in_progress if r.mine]
    return {"rows": decided, "in_progress": in_progress, "full": full}
