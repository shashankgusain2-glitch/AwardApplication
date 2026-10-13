"""Judge screens (sample data until the judging models are built)."""
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render

from apps.accounts.permissions import role_required
from apps.core import demo_data as d

ROLE = "judge"


def _with_award(assignment, request):
    """Attach the award (with staff's current settings) and what the judge may see."""
    entry = d.ENTRIES[assignment["entry"]]
    award = d.get_award(entry["award"], request)
    kind = d.round_type(award, assignment["round"])
    if kind is None:
        return None  # staff removed this round from the award
    blind = d.is_blind_round(award, assignment["round"])
    return {
        **assignment,
        "award": award,
        "round_type": kind,
        "round_label": d.ROUND_TYPES[kind],
        "blind": blind,
        # Rule 1: the organisation's name is only passed on when the round is not blind.
        "applicant": None if blind else entry["org"],
    }


@role_required("judge")
def assignments(request):
    mine = d.assignments_for(request.user)   # only this judge's assignments
    return render(request, "judging/assignments.html", {
        "role": ROLE,
        "judge": d.JUDGES.get(request.user.email.lower(), {"name": request.user.display_name, "expertise": ""}),
        "assignments": [a for a in (_with_award(a, request) for a in mine) if a],
    })


@role_required("judge")
def score(request, entry_id=None):
    mine = d.assignments_for(request.user)
    if entry_id is None:
        if not mine:
            return redirect("judging:assignments")
        entry_id = mine[0]["entry"]
    assignment = next((a for a in mine if a["entry"] == entry_id), None)
    if assignment is None:
        if any(a["entry"] == entry_id for a in d.ASSIGNMENTS):
            raise PermissionDenied("This report is assigned to another judge.")
        raise Http404("No such report")
    assignment = _with_award(assignment, request)
    if assignment is None:
        raise Http404("This round is no longer part of the award")
    award = assignment["award"]

    sections, hidden = d.answers_for_judge(entry_id, award, assignment["round"])

    criteria = award["criteria"] if assignment["round"] == "Round 1" else award["round2_criteria"]
    saved = d.SAMPLE_SCORES.get(entry_id, {})
    scorecard = [
        {**c, "score": saved.get(c["name"], (None, ""))[0], "comment": saved.get(c["name"], (None, ""))[1]}
        for c in criteria
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
