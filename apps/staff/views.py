"""
Staff: the most important role (12 Oct meeting). One place to confirm
applicants, assign judges, record conflicts, approve change requests,
run Round 2, configure events and forms, and see what happened.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST

from apps.awards.models import Award
from apps.core.models import ActivityLog, log
from apps.entries.models import Application
from apps.judging import services
from apps.judging.models import Conflict, JudgeProfile, ScoreChangeRequest

from .forms import ConflictForm, EventSettingsForm, JudgeForm, NewQuestionForm, RejectForm, Round2Form

S = Application.Status


def staff_only(view):
    return staff_member_required(login_url="accounts:verify_email")(view)


def rule_errors(view):
    """Turn a broken rule into a message instead of an error page."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except services.RuleError as e:
            messages.error(request, str(e))
            return redirect(request.META.get("HTTP_REFERER") or "staff:home")
    return wrapper


@staff_only
def home(request):
    apps = Application.objects.exclude(status=S.DRAFT)
    return render(request, "staff/home.html", {
        "to_check": apps.filter(status=S.SUBMITTED).count(),
        "in_pool": apps.filter(status=S.POOL).count(),
        "to_shortlist": apps.filter(status=S.JUDGED).count(),
        "edit_requests": apps.filter(edit_request=Application.EditRequest.REQUESTED).count(),
        "score_requests": ScoreChangeRequest.objects.filter(status="requested").count(),
        "judges": JudgeProfile.objects.count(),
    })


@staff_only
def reports(request):
    status = request.GET.get("status", "")
    apps = Application.objects.exclude(status=S.DRAFT).select_related("organisation", "award")
    if status:
        apps = apps.filter(status=status)
    return render(request, "staff/reports.html", {
        "apps": apps, "status": status, "statuses": [s for s in S if s != S.DRAFT],
    })


@staff_only
def report(request, pk):
    app = get_object_or_404(Application.objects.select_related("organisation", "award", "form_version"), pk=pk)
    assignments = app.assignments.select_related("judge")
    round2_judges = JudgeProfile.objects.filter(panels=app.award).exclude(conflicts__organisation=app.organisation)
    return render(request, "staff/report.html", {
        "app": app,
        "questions": [{"label": q["label"], "answer": app.answers.get(q["key"], "")}
                      for q in app.form_version.questions],
        "round1": assignments.filter(round=1),
        "round2": assignments.filter(round=2),
        "suggested": services.suggested_judges(app) if app.status in (S.POOL, S.ASSIGNED, S.JUDGING) else [],
        "still_needed": services.judges_still_needed(app),
        "conflicted": [c.judge for c in Conflict.objects.filter(organisation=app.organisation).select_related("judge")],
        "reject_form": RejectForm(),
        "round2_form": Round2Form(judges=round2_judges),
        "activity": app.activity.select_related("actor")[:20],
    })


@staff_only
@require_POST
@rule_errors
def report_action(request, pk):
    app = get_object_or_404(Application, pk=pk)
    action = request.POST.get("action")
    if action == "confirm":
        services.confirm(app, request.user)
        messages.success(request, "Confirmed. The report is in the pool.")
    elif action == "reject":
        form = RejectForm(request.POST)
        if not form.is_valid():
            raise services.RuleError("Give a reason for rejecting.")
        services.reject(app, request.user, form.cleaned_data["reason"])
        messages.success(request, "Rejected.")
    elif action == "auto_assign":
        picks = services.auto_assign(app, request.user, request)
        messages.success(request, f"Assigned to {', '.join(str(j) for j in picks)}. They've been emailed.")
    elif action == "assign":
        judges = list(JudgeProfile.objects.filter(pk__in=request.POST.getlist("judges")))
        services.assign(app, judges, request.user, request)
        messages.success(request, f"Assigned to {len(judges)} judge(s).")
    elif action == "shortlist":
        services.shortlist(app, request.user)
        messages.success(request, "Shortlisted for Round 2.")
    elif action == "round2":
        judges = JudgeProfile.objects.filter(panels=app.award).exclude(conflicts__organisation=app.organisation)
        form = Round2Form(request.POST, judges=judges)
        if not form.is_valid():
            raise services.RuleError("Fill in the meeting time, link and judges.")
        d = form.cleaned_data
        services.schedule_round2(app, d["scheduled_at"], d["meeting_link"], list(d["judges"]), request.user, request)
        messages.success(request, "Round 2 meeting scheduled. Judges have been emailed.")
    elif action in ("approve_edit", "decline_edit"):
        approve = action == "approve_edit"
        app.edit_request = Application.EditRequest.APPROVED if approve else Application.EditRequest.DECLINED
        app.save()
        log(request.user, f"{'Allowed' if approve else 'Refused'} the applicant to change the report", app)
        messages.success(request, "Edit approved." if approve else "Edit declined.")
    return redirect("staff:report", pk=app.pk)


@staff_only
@require_http_methods(["GET", "POST"])
@rule_errors
def judges(request):
    judge_form = JudgeForm(request.POST or None, prefix="judge")
    conflict_form = ConflictForm(request.POST or None, prefix="conflict")
    if request.method == "POST":
        if "add_judge" in request.POST and judge_form.is_valid():
            d = judge_form.cleaned_data
            judge = services.get_or_create_judge(d["email"], d["name"], d["expertise"], d["priority"],
                                                 d["max_load"], d["panels"])
            link = services.email_judge(judge, "You've been selected as a judge",
                                        "You've been selected to judge awards.", request)
            log(request.user, f"Added judge {judge} (priority {judge.priority})")
            messages.success(request, f"{judge} added and emailed. Demo outbox, their login link: {link}")
            return redirect("staff:judges")
        if "add_conflict" in request.POST and conflict_form.is_valid():
            d = conflict_form.cleaned_data
            Conflict.objects.get_or_create(judge=d["judge"], organisation=d["organisation"],
                                           defaults={"note": d["note"], "recorded_by": request.user})
            log(request.user, f"Recorded a conflict: {d['judge']} and {d['organisation']}")
            messages.success(request, f"Conflict recorded. {d['judge']} will never be given {d['organisation']}'s reports.")
            return redirect("staff:judges")
    return render(request, "staff/judges.html", {
        "judges": JudgeProfile.objects.prefetch_related("panels").annotate(
            graded=Count("assignments", filter=Q(assignments__status="completed"))),
        "conflicts": Conflict.objects.select_related("judge", "organisation"),
        "judge_form": judge_form,
        "conflict_form": conflict_form,
    })


@staff_only
@require_POST
def judge_link(request, pk):
    judge = get_object_or_404(JudgeProfile, pk=pk)
    link = services.email_judge(judge, "Your judging link", "Here is your link to the judging tab.", request)
    messages.success(request, f"Link emailed to {judge}. Demo outbox: {link}")
    return redirect("staff:judges")


@staff_only
def requests(request):
    return render(request, "staff/requests.html", {
        "edit_requests": Application.objects.filter(edit_request=Application.EditRequest.REQUESTED)
        .select_related("organisation", "award"),
        "score_requests": ScoreChangeRequest.objects.filter(status="requested")
        .select_related("assignment__judge", "assignment__application__organisation"),
    })


@staff_only
@require_POST
@rule_errors
def score_request_action(request, pk):
    change_request = get_object_or_404(ScoreChangeRequest, pk=pk)
    approve = request.POST.get("action") == "approve"
    services.decide_change_request(change_request, approve, request.user)
    messages.success(request, "Change allowed. The judge can now change the scores." if approve else "Change refused.")
    return redirect("staff:requests")


@staff_only
@require_http_methods(["GET", "POST"])
def events(request):
    forms = []
    for award in Award.objects.all():
        form = EventSettingsForm(request.POST if request.POST.get("award") == str(award.pk) else None,
                                 instance=award, prefix=f"e{award.pk}")
        if request.method == "POST" and request.POST.get("award") == str(award.pk) and form.is_valid():
            form.save()
            log(request.user, f"Changed settings of {award}")
            messages.success(request, f"Saved {award}.")
            return redirect("staff:events")
        forms.append((award, form))
    return render(request, "staff/events.html", {"forms": forms})


@staff_only
@require_http_methods(["GET", "POST"])
def form_editor(request, slug):
    """Change an event's questions. Publishing makes a new version; old reports keep theirs (Rule 4)."""
    award = get_object_or_404(Award, slug=slug)
    current = award.current_form
    new_q = NewQuestionForm(request.POST or None)
    if request.method == "POST" and new_q.is_valid():
        keep = set(request.POST.getlist("keep"))
        questions = [q for q in current.questions if q["key"] in keep]
        label = new_q.cleaned_data["label"].strip()
        if label:
            key = slugify(label)[:40].replace("-", "_") or "q"
            while any(q["key"] == key for q in questions):
                key += "_2"
            questions.append({"key": key, "label": label, "type": new_q.cleaned_data["type"],
                              "required": new_q.cleaned_data["required"]})
        if not questions:
            messages.error(request, "A form needs at least one question.")
        elif questions == current.questions:
            messages.error(request, "Nothing changed.")
        else:
            version = current.publish_new_version(questions)
            log(request.user, f"Published {award} form version {version.number}")
            messages.success(request, f"Published version {version.number}. Reports already started keep their version.")
            return redirect("staff:form_editor", slug=slug)
    return render(request, "staff/form_editor.html", {
        "award": award, "current": current, "new_q": new_q,
        "versions": award.form_versions.annotate(used=Count("applications")).order_by("-number"),
    })


@staff_only
def activity(request):
    return render(request, "staff/activity.html", {
        "entries": ActivityLog.objects.select_related("actor", "application__organisation")[:200],
    })
