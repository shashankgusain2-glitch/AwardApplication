from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import role_required

from . import demo_data as d
from . import public_awards
from .models import TwoStepApproval as T
from .services import BusinessRuleError


def home(request):
    featured = [a for a in public_awards.all_awards() if a["can_apply"]][:3]
    return render(request, "core/home.html", {
        "stats": d.STATS,
        "featured": featured,
        "steps": d.HOW_IT_WORKS,
        "promises": d.TRUST_PROMISES,
        "winners": d.PAST_WINNERS,
        "sectors": d.SECTORS,
    })


def about(request):
    return render(request, "core/about.html", {
        "stats": d.STATS,
        "promises": d.TRUST_PROMISES,
    })


def award_list(request):
    sector = request.GET.get("sector", "")
    every = public_awards.all_awards()
    return render(request, "core/awards.html", {
        "awards": [a for a in every if not sector or a["sector"] == sector],
        "sectors": public_awards.sectors(every),
        "active_sector": sector,
    })


def award_detail(request, slug):
    award = public_awards.get_award(slug)
    if award is None:
        raise Http404("Award not found")
    return render(request, "core/award_detail.html", {
        "award": award,
        "details": public_awards.details(award),
    })


@role_required("staff", "manager")
@require_POST
def decide_request(request, type, pk):
    """
    One button for every request made after submitting (applicant edit, re-evaluation, judge
    score change). Staff take the first step (pass to leadership / refuse); a leader takes the
    last (confirm / refuse). The services check whose turn it is.
    """
    from apps.applications import services as applications
    from apps.applications.models import ApplicantRequest
    from apps.evaluations import services as evaluations
    from apps.evaluations.models import ScoreChangeRequest

    approve = request.POST.get("decision") == "approve"
    note = request.POST.get("note", "")
    try:
        if type == "applicant":
            req = get_object_or_404(ApplicantRequest, pk=pk)
            applications.decide_request(req, by=request.user, approve=approve, note=note)
            reference = req.application.reference
        elif type == "score":
            req = get_object_or_404(ScoreChangeRequest, pk=pk)
            evaluations.decide_change(req, by=request.user, approve=approve, note=note)
            reference = req.evaluation.assignment.report.reference
        else:
            raise Http404("Unknown request")
    except BusinessRuleError as error:
        messages.error(request, str(error))
    else:
        outcome = {T.WAITING_LEADER: f"passed to {req.confirmer_label} to confirm",
                   T.APPROVED: "confirmed: it takes effect now", T.REFUSED: "refused"}[req.status]
        messages.success(request, f"{reference}: {req.get_kind_display() if type == 'applicant' else 'score change'} "
                                  f"request {outcome}. The person who asked has been told.")
    target = request.POST.get("next", "")
    return redirect(target if target.startswith("/staff/") else "awards:entries")


@role_required("applicant", "judge", "staff", "manager", "leader")
def results(request):
    """The results board: decided results per award (what each role may see: apps/core/results.py)."""
    from apps.applications.services import can_request_reevaluation

    from . import results as board

    awards = list(board.awards_with_results(request.user))
    award = next((a for a in awards if a.slug == request.GET.get("award")), awards[0] if awards else None)
    data = board.board(request.user, award) if award else {"rows": [], "in_progress": [], "full": False}
    for report in data["rows"]:
        report.can_reevaluate = report.mine and can_request_reevaluation(report)
    return render(request, "core/results.html", {"role": request.user.role, "awards": awards, "award": award, **data})
