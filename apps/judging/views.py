"""Judge screens (sample data until the judging models are built)."""
from django.http import Http404
from django.shortcuts import render

from apps.core import demo_data as d

ROLE = "judge"


def _with_award(assignment, request):
    """Attach the award (with staff's current settings) and what the judge may see."""
    entry = d.ENTRIES[assignment["entry"]]
    award = d.get_award(entry["award"], request)
    blind = award["blind"] and assignment["round"] == "Round 1"
    return {
        **assignment,
        "award": award,
        "blind": blind,
        # Rule 1: the organisation's name is only passed on when judging is not blind.
        "applicant": None if blind else entry["org"],
    }


def assignments(request):
    return render(request, "judging/assignments.html", {
        "role": ROLE,
        "judge": d.JUDGE,
        "assignments": [_with_award(a, request) for a in d.ASSIGNMENTS],
    })


def score(request, entry_id="A-0042"):
    assignment = next((a for a in d.ASSIGNMENTS if a["entry"] == entry_id), None)
    if assignment is None:
        raise Http404("Not assigned to you")
    assignment = _with_award(assignment, request)
    award = assignment["award"]

    sections, hidden = d.answers_for_judge(entry_id, award, assignment["round"])

    saved = d.SAMPLE_SCORES.get(entry_id, {})
    scorecard = [
        {**c, "score": saved.get(c["name"], (None, ""))[0], "comment": saved.get(c["name"], (None, ""))[1]}
        for c in award["criteria"]
    ]
    scored = sum(1 for c in scorecard if c["score"] is not None)

    return render(request, "judging/score.html", {
        "role": ROLE,
        "assignment": assignment,
        "award": award,
        "sections": sections,
        "hidden": hidden,
        "scorecard": scorecard,
        "progress": round(scored * 100 / len(scorecard)) if scorecard else 0,
        "scale": range(1, 11),
        "submitted": assignment["status"] == "Submitted",
    })
