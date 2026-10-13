"""
Leadership screens, on the real database. Leaders see everything and
approve results; they never change scores (that is the judges' job, with
staff permission: Rule 3).
"""
from django.contrib import messages
from django.db.models import Avg, Count, Max, Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import role_required
from apps.applications import services as application_services
from apps.applications.models import Application
from apps.awards.models import Award
from apps.core import overview as summaries
from apps.core.services import BusinessRuleError
from apps.evaluations.models import Evaluation

ROLE = "leader"
SUBMITTED = Q(assignments__evaluation__status=Evaluation.Status.SUBMITTED)


def _with_scores(reports):
    """Average, lowest and highest submitted total per report, and how many judges have submitted."""
    return reports.annotate(
        average=Avg("assignments__evaluation__total_score", filter=SUBMITTED),
        lowest=Min("assignments__evaluation__total_score", filter=SUBMITTED),
        highest=Max("assignments__evaluation__total_score", filter=SUBMITTED),
        judged=Count("assignments__evaluation", filter=SUBMITTED, distinct=True),
    )


@role_required("leader")
def overview(request):
    """Home page: the whole event at a glance, from the database."""
    return render(request, "dashboard/overview.html", {"role": ROLE, **summaries.leader_overview()})


@role_required("leader")
def review(request):
    """The full list: every submitted application, its status and its scores so far."""
    reports = application_services.visible_to(request.user).exclude(status=Application.Status.DRAFT) \
        .select_related("applicant__applicant_profile")
    filters = {"status": request.GET.get("status", ""), "award": request.GET.get("award", "")}
    if filters["status"]:
        reports = reports.filter(status=filters["status"])
    if filters["award"]:
        reports = reports.filter(award__slug=filters["award"])
    rows = _with_scores(reports).order_by("award__name", "-average")
    return render(request, "dashboard/review.html", {
        "role": ROLE,
        "reports": rows,
        "filters": filters,
        "statuses": [c for c in Application.Status.choices if c[0] != Application.Status.DRAFT],
        "awards": Award.objects.order_by("name"),
    })


@role_required("leader")
def results(request):
    """Scored reports waiting for a decision, best first, with every judge's total."""
    reports = _with_scores(application_services.visible_to(request.user)
                           .filter(status=Application.Status.SCORED)
                           .select_related("applicant__applicant_profile")).order_by("award__name", "-average")
    rows = []
    for report in reports:
        evaluations = Evaluation.objects.filter(assignment__report=report, status=Evaluation.Status.SUBMITTED) \
            .select_related("assignment__judge").order_by("assignment__round")
        rows.append({"report": report, "evaluations": evaluations,
                     "spread": (report.highest - report.lowest) if report.highest is not None else None})
    decided = application_services.visible_to(request.user).filter(
        status__in=[Application.Status.APPROVED, Application.Status.REJECTED]).order_by("-updated_at")[:20]
    return render(request, "dashboard/results.html", {"role": ROLE, "rows": rows, "decided": decided})


@role_required("leader")
@require_POST
def decide(request, pk):
    """Approve or reject a scored result. Goes through the same rule as the API (leaders approve)."""
    report = get_object_or_404(application_services.visible_to(request.user), pk=pk)
    new_status = Application.Status.APPROVED if request.POST.get("decision") == "approve" \
        else Application.Status.REJECTED
    try:
        application_services.change_status(report, by=request.user, new_status=new_status,
                                           note=request.POST.get("note", ""))
        messages.success(request, f"{report.reference}: {report.get_status_display().lower()}.")
    except BusinessRuleError as error:
        messages.error(request, str(error))
    return redirect("dashboard:results")
