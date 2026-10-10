"""Judge screens (sample data until the judging models are built)."""
from django.shortcuts import render

from apps.core import demo_data as d

ROLE = "judge"


def assignments(request):
    return render(request, "judging/assignments.html", {
        "role": ROLE,
        "judge": d.JUDGE,
        "assignments": d.ASSIGNMENTS,
    })


def score(request):
    scored = [c for c in d.SCORECARD if c["score"] is not None]
    return render(request, "judging/score.html", {
        "role": ROLE,
        "assignment": d.ASSIGNMENTS[0],
        "answers": d.ENTRY_ANSWERS,
        "scorecard": d.SCORECARD,
        "progress": round(len(scored) * 100 / len(d.SCORECARD)),
        "scale": range(1, 11),
    })
