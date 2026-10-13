"""
Judge workflow: email link → judging tab → accept / decline → grade
(save partway) → submit → ask staff to change scores → change with a reason.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from . import services
from .models import Assignment


def judge_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "judge"):
            messages.error(request, "That page is for judges.")
            return redirect("core:home")
        return view(request, *args, **kwargs)
    return wrapper


def link_login(request, token):
    """The link in the judge's email logs them in and opens the judging tab."""
    try:
        user_id = services.user_id_from_token(token)
    except signing.BadSignature:
        messages.error(request, "This link is invalid or has expired. Ask staff for a new one.")
        return redirect("core:home")
    user = get_object_or_404(get_user_model(), pk=user_id, judge__isnull=False)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("judging:tab")


@judge_required
def tab(request):
    judge = request.user.judge
    mine = judge.assignments.select_related("application__award", "application__organisation")
    return render(request, "judging/tab.html", {
        "judge": judge,
        "offered": mine.filter(status=Assignment.Status.OFFERED, round=1),
        "grading": mine.filter(status=Assignment.Status.ACCEPTED, round=1),
        "done": mine.filter(status=Assignment.Status.COMPLETED, round=1),
        "round2": mine.filter(round=2),
    })


@judge_required
@require_POST
def respond(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, judge=request.user.judge)
    try:
        if request.POST.get("answer") == "accept":
            services.accept(assignment)
            messages.success(request, "Accepted. You can grade the report now.")
            return redirect("judging:grade", pk=assignment.pk)
        services.decline(assignment)
        messages.success(request, "Declined. The report goes back to the pool for another judge.")
    except services.RuleError as e:
        messages.error(request, str(e))
    return redirect("judging:tab")


def _read_scores(post, criteria):
    values, comments = {}, {}
    for c in criteria:
        raw = post.get(f"score_{c['key']}", "")
        if raw.isdigit() and 1 <= int(raw) <= 10:
            values[c["key"]] = int(raw)
        comments[c["key"]] = post.get(f"comment_{c['key']}", "").strip()[:1000]
    return values, comments


@judge_required
@require_http_methods(["GET", "POST"])
def grade(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk, judge=request.user.judge)
    if assignment.status in (Assignment.Status.OFFERED, Assignment.Status.DECLINED):
        return redirect("judging:tab")

    if request.method == "POST":
        action = request.POST.get("action")
        values, comments = _read_scores(request.POST, assignment.criteria)
        try:
            if action == "change":
                n = services.change_scores(assignment, values, request.POST.get("reason", ""), request.user)
                messages.success(request, f"{n} score(s) changed and recorded with your reason.")
            elif action == "request_change":
                services.request_change(assignment, request.POST.get("reason", ""))
                messages.success(request, "Request sent. Staff will contact you and confirm.")
            else:
                services.save_scores(assignment, values, comments, submit=(action == "submit"))
                messages.success(request, "Grades submitted." if action == "submit"
                                 else "Saved. You can finish later.")
        except services.RuleError as e:
            messages.error(request, str(e))
        return redirect("judging:grade", pk=assignment.pk)

    scores = assignment.scores_by_key
    rows = [{**c, "score": scores.get(c["key"])} for c in assignment.criteria]
    app = assignment.application
    questions = [{"label": q["label"], "answer": app.answers.get(q["key"], "")} for q in app.form_version.questions]
    return render(request, "judging/grade.html", {
        "a": assignment,
        "app": app,
        "rows": rows,
        "questions": questions,
        "scale": range(1, 11),
        "locked": assignment.status != Assignment.Status.ACCEPTED,
        "pending_request": assignment.change_requests.filter(status="requested").first(),
        "changes": assignment.score_changes.all(),
        "meeting": getattr(app, "round2_meeting", None) if assignment.round == 2 else None,
    })
