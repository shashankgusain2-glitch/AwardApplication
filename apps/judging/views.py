"""
Judge screens, on the real database.

A judge only ever reaches their own assignments: every lookup goes through
the assignments service's `visible_to(user)`, so another judge's
assignment gives 404. What the judge may see of a report comes from
`report_for_judge()`, which removes identifying answers on blind awards
(Rule 1). Scores are saved through the evaluations service (Rule 3).
"""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import role_required
from apps.applications.models import Application
from apps.assignments import services as assignment_services
from apps.assignments.models import JudgeAssignment
from apps.core.services import BusinessRuleError
from apps.evaluations import services as evaluation_services
from apps.evaluations.models import Evaluation, ScoreChangeRequest

ROLE = "judge"


@role_required("judge")
def assignments(request):
    """Home page: this judge's own assignments from the database (blind judging applied)."""
    return render(request, "judging/assignments.html", {"role": ROLE, **assignment_services.judge_home(request.user)})


@role_required("judge")
@require_POST
def respond(request, pk):
    """Accept or decline an assignment. Only the judge's own: anyone else's gives 404."""
    assignment = get_object_or_404(assignment_services.visible_to(request.user), pk=pk)
    try:
        if request.POST.get("answer") == "accept":
            assignment_services.start_review(assignment, judge=request.user)
            messages.success(request, f"Accepted {assignment.report.reference}. You can grade it now.")
            return redirect("judging:score", pk=assignment.pk)
        assignment_services.decline(assignment, judge=request.user)
        messages.success(request, f"Declined {assignment.report.reference}. It goes back to the pool.")
    except BusinessRuleError as error:
        messages.error(request, str(error))
    return redirect("judging:assignments")


def _sections(answers):
    sections = []
    for answer in answers:
        name = answer.get("section") or "The entry"
        if not sections or sections[-1]["name"] != name:
            sections.append({"name": name, "questions": []})
        sections[-1]["questions"].append(answer)
    return sections


def _posted_scores(request, criteria):
    """{criterion_key: {"score": n, "comment": "..."}} for the criteria the judge filled in."""
    scores = {}
    for key in criteria:
        raw = request.POST.get(f"score_{key}", "").strip()
        if not raw:
            continue
        try:
            score = int(raw)
        except ValueError:
            raise BusinessRuleError(f"{criteria[key].label}: choose a score from 1 to 10.") from None
        scores[key] = {"score": score, "comment": request.POST.get(f"comment_{key}", "").strip()}
    return scores


@role_required("judge")
def score(request, pk=None):
    """
    Read the report (as the judge may see it) and grade it: save midway,
    submit, ask to change a submitted grade, and change it once staff allow.
    """
    if pk is None:   # "Score an entry" in the menu: the first report being graded, else the list
        first = assignment_services.visible_to(request.user).filter(status=JudgeAssignment.Status.IN_REVIEW).first()
        return redirect("judging:score", pk=first.pk) if first else redirect("judging:assignments")

    assignment = get_object_or_404(assignment_services.visible_to(request.user), pk=pk)
    award = assignment.report.award
    round_obj = award.rounds.filter(number=assignment.round).first()
    if round_obj is None:
        raise Http404("This round is no longer part of the award")
    criteria = evaluation_services.criteria_for(assignment)
    evaluation = Evaluation.objects.filter(assignment=assignment).first()

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action in ("save", "submit"):
                evaluation_services.save(assignment, judge=request.user, scores=_posted_scores(request, criteria),
                                         feedback=request.POST.get("feedback", ""), submit=action == "submit")
                messages.success(request, "Scores submitted. Any change now needs staff permission and a reason."
                                 if action == "submit" else "Scores saved. You can come back and finish later.")
            elif action == "request_change" and evaluation:
                evaluation_services.request_change(evaluation, judge=request.user,
                                                   reason=request.POST.get("reason", ""))
                messages.success(request, "Request sent to the programme staff.")
            elif action == "change" and evaluation:
                evaluation_services.change_scores(evaluation, judge=request.user,
                                                  scores=_posted_scores(request, criteria),
                                                  reason=request.POST.get("reason", ""))
                messages.success(request, "Scores changed. The change is recorded with your name, time and reason.")
        except BusinessRuleError as error:
            messages.error(request, str(error))
        return redirect("judging:score", pk=assignment.pk)

    saved = {s.criterion.key: s for s in evaluation.scores.select_related("criterion")} if evaluation else {}
    scorecard = [{"key": key, "label": c.label, "weight": c.weight,
                  "score": saved[key].score if key in saved else None,
                  "comment": saved[key].comment if key in saved else ""}
                 for key, c in sorted(criteria.items(), key=lambda kv: kv[1].order)]
    view = assignment_services.report_for_judge(assignment)
    submitted = bool(evaluation and evaluation.status == Evaluation.Status.SUBMITTED)
    change_request = (evaluation.change_requests.exclude(status=ScoreChangeRequest.Status.USED)
                      .order_by("-created_at").first() if submitted else None)
    return render(request, "judging/score.html", {
        "role": ROLE,
        "assignment": assignment,
        "award": award,
        "round": round_obj,
        "view": view,
        "sections": _sections(view["answers"]),
        "scorecard": scorecard,
        "evaluation": evaluation,
        "progress": round(len(saved) * 100 / len(scorecard)) if scorecard else 0,
        "scale": range(1, 11),
        "submitted": submitted,
        "can_grade": assignment.status in (JudgeAssignment.Status.PENDING, JudgeAssignment.Status.IN_REVIEW),
        "change_request": change_request,
        "changes_closed": (evaluation_services.REPLACED if assignment.status == JudgeAssignment.Status.SUPERSEDED
                           else evaluation_services.RESULT_DECIDED if assignment.report.status in (
                               Application.Status.APPROVED, Application.Status.REJECTED) else ""),
        "history": evaluation.score_changes.select_related("criterion", "changed_by") if evaluation else [],
    })
