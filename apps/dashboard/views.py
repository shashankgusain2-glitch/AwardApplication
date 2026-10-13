"""Leadership screens (sample data until the other apps' models are built)."""
from django.shortcuts import render

from apps.core import demo_data as d

ROLE = "leader"


def overview(request):
    rows = d.LEADER_OVERVIEW
    return render(request, "dashboard/overview.html", {
        "role": ROLE,
        "rows": rows,
        "total_entries": sum(r["entries"] for r in rows),
        "total_flags": sum(r["flags"] for r in rows),
        "open_count": sum(1 for r in rows if r["stage"] in ("Applications open", "Closing soon")),
    })


def review(request):
    return render(request, "dashboard/review.html", {
        "role": ROLE,
        "items": d.REVIEW_QUEUE,
    })


def results(request):
    return render(request, "dashboard/results.html", {
        "role": ROLE,
        "award": d.get_award("sustainability-leadership"),
        "results": d.RESULTS_TO_APPROVE,
    })
