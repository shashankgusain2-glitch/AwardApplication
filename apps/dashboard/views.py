"""Leadership screens (sample data until the other apps' models are built)."""
from django.shortcuts import render

from apps.accounts.permissions import role_required
from apps.core import demo_data as d
from apps.core import overview as summaries

ROLE = "leader"


@role_required("leader")
def overview(request):
    """Home page: the whole event at a glance, from the database."""
    return render(request, "dashboard/overview.html", {"role": ROLE, **summaries.leader_overview()})


@role_required("leader")
def review(request):
    return render(request, "dashboard/review.html", {
        "role": ROLE,
        "items": d.REVIEW_QUEUE,
    })


@role_required("leader")
def results(request):
    return render(request, "dashboard/results.html", {
        "role": ROLE,
        "award": d.get_award("sustainability-leadership"),
        "results": d.RESULTS_TO_APPROVE,
    })
