"""
Applicant screens, on the real database.

Every page is for logged-in applicants only and shows only their own data:
each view looks things up through the applications service's
`visible_to(user)`, so another applicant's application gives 404. Saving,
submitting and asking to edit go through the same services as the API.
"""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework.exceptions import ValidationError

from apps.accounts import services as account_services
from apps.accounts.models import ApplicantProfile
from apps.accounts.permissions import role_required
from apps.applications import files, services
from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.awards.models import Award
from apps.core.services import BusinessRuleError

ROLE = "applicant"

PROFILE_FIELDS = ["organisation_name", "gstin", "holder_pan", "sector", "organisation_size", "annual_turnover_band",
                  "established_year", "website", "address", "city", "state", "pincode", "contact_name",
                  "contact_designation", "contact_phone"]


def _errors(error):
    """A DRF ValidationError as {field: "first message"} for the form."""
    detail = error.detail if isinstance(error.detail, dict) else {"__all__": error.detail}
    return {field: str(problems[0] if isinstance(problems, list) else problems) for field, problems in detail.items()}


@role_required("applicant")
def dashboard(request):
    """Home page: this applicant's own applications and profile, from the database."""
    return render(request, "entries/dashboard.html", {"role": ROLE, **services.applicant_home(request.user)})


@role_required("applicant")
def organisation(request):
    """The applicant's organisation profile: filled once, used for every award."""
    profile = ApplicantProfile.objects.filter(user=request.user).first()
    errors, values = {}, {}
    if request.method == "POST":
        values = {f: request.POST.get(f, "").strip() for f in PROFILE_FIELDS}
        data = {**values, "established_year": values["established_year"] or None}
        try:
            account_services.save_profile(request.user, data, partial=False)
        except ValidationError as error:
            errors = _errors(error)
            messages.error(request, "Please fix the highlighted fields.")
        except BusinessRuleError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Organisation profile saved.")
            return redirect("entries:organisation")
    return render(request, "entries/organisation.html", {
        "role": ROLE,
        "profile": profile,
        "values": values or {f: getattr(profile, f, "") or "" for f in PROFILE_FIELDS},
        "errors": errors,
        "sizes": ApplicantProfile.Size.choices,
        "turnovers": ApplicantProfile.Turnover.choices,
        "gstin_locked": bool(profile and profile.verification_status == ApplicantProfile.Verification.VERIFIED),
    })


def _sections(application):
    """The application's form (its own version) grouped into sections, with the saved answers."""
    sections = []
    uploaded = {f.question_key: f for f in application.attachments.all()}
    for q in application.form_version.questions:
        name = q.get("section") or "Your application"
        if not sections or sections[-1]["name"] != name:
            sections.append({"name": name, "questions": []})
        value = application.content.get(q["key"], "")
        sections[-1]["questions"].append({**q, "value": value, "attachment": uploaded.get(q["key"])})
    for s in sections:
        s["done"] = sum(1 for q in s["questions"] if str(q["value"]).strip())
        s["total"] = len(s["questions"])
    return sections


# Session keys (per application): a file that failed to upload, and "highlight the missing
# required questions" (set by a failed submit, cleared by a successful one).
_UPLOAD_ERRORS = "upload_errors_{}"
_CHECK_REQUIRED = "check_required_{}"


def _first_section_with(application, keys):
    """The 1-based number of the first form section that contains any of these question keys."""
    names = []
    for q in application.form_version.questions:
        name = q.get("section") or "Your application"
        if not names or names[-1] != name:
            names.append(name)
        if q["key"] in keys:
            return len(names)
    return 1


@role_required("applicant")
def application_form(request, slug=None):
    """
    /applicant/application/            pick an award (own applications and open awards)
    /applicant/application/<award>/    start, fill section by section, save, submit
    """
    mine = services.visible_to(request.user).select_related("award")
    if slug is None:
        entered = {a.award_id for a in mine}
        return render(request, "entries/application_pick.html", {
            "role": ROLE, "applications": mine,
            "open_awards": Award.objects.filter(status=Award.Status.OPEN).exclude(id__in=entered),
            "upcoming_awards": Award.objects.filter(status=Award.Status.UPCOMING).exclude(id__in=entered),
        })

    award = get_object_or_404(Award, slug=slug)
    application = mine.filter(award=award).first()

    if request.method == "POST":
        action = request.POST.get("action", "save")   # the Save / Next / Back buttons send only "go"
        try:
            if action == "start":
                application = services.create_draft(applicant=request.user, award=award,
                                                    title=request.POST.get("title", "").strip() or award.name)
                messages.success(request, f"Application {application.reference} started. Your answers save as you go.")
                return redirect("entries:form", slug=award.slug)
            if application is None:
                raise Http404("No application for this award")
            if action in ("save", "submit"):
                file_keys = {q["key"] for q in application.form_version.questions if q.get("type") == "file"}
                keys = [k for k in request.POST.getlist("keys") if k not in file_keys]
                answers = {k: request.POST.get(f"q_{k}", "").strip() for k in keys}
                upload_errors = {}
                if services.can_edit(application):
                    services.update(application, by=request.user, content=answers)
                    for key in file_keys:
                        if f"f_{key}" in request.FILES:
                            try:
                                files.attach(application, by=request.user, question_key=key,
                                             upload=request.FILES[f"f_{key}"])
                            except BusinessRuleError as error:   # flag that question; keep the other answers
                                upload_errors[key] = str(error)
                if upload_errors:
                    request.session[_UPLOAD_ERRORS.format(application.pk)] = upload_errors
                    messages.error(request, "Your other answers were saved, but a file couldn't be uploaded. "
                                            "It's highlighted in red below.")
                    return redirect(f"{request.path}?section={request.POST.get('section') or '1'}")
                if action == "submit":
                    missing = services.missing_required(application)
                    if missing:
                        request.session[_CHECK_REQUIRED.format(application.pk)] = True
                        first = _first_section_with(application, missing)
                        messages.error(request, f"{len(missing)} required question{'s' if len(missing) != 1 else ''} "
                                                f"still need{'s' if len(missing) == 1 else ''} an answer. "
                                                f"They're highlighted in red.")
                        return redirect(f"{request.path}?section={first}")
                    services.submit(application, by=request.user)
                    request.session.pop(_CHECK_REQUIRED.format(application.pk), None)
                    messages.success(request, f"{application.reference} submitted. It is now locked.")
                    return redirect("entries:status")
                messages.success(request, "Saved.")
            elif action == "request_edit":
                services.request_edit(application, by=request.user, reason=request.POST.get("reason", ""))
                messages.success(request, "Your request was sent to the programme staff.")
        except BusinessRuleError as error:
            messages.error(request, str(error))
        section = request.POST.get("go") or request.POST.get("section") or "1"
        return redirect(f"{request.path}?section={section}")

    if application is None:
        if award.status != Award.Status.OPEN:
            upcoming = award.status == Award.Status.UPCOMING and award.opens_on
            when = f" It opens on {award.opens_on:%d %b %Y}." if upcoming else ""
            messages.info(request, f"{award.name} isn't open for applications.{when}")
            return redirect("entries:form")
        return render(request, "entries/application_start.html", {"role": ROLE, "award": award})

    sections = _sections(application)
    editable = services.can_edit(application)
    problems = request.session.pop(_UPLOAD_ERRORS.format(application.pk), {}) if editable else {}
    if editable and request.session.get(_CHECK_REQUIRED.format(application.pk)):
        # After a failed submit, unanswered required questions stay red until they're answered.
        for key in services.missing_required(application):
            problems.setdefault(key, "This question is required. Please answer it before you submit.")
    for s in sections:
        for q in s["questions"]:
            q["problem"] = problems.get(q["key"], "")
        s["problems"] = sum(1 for q in s["questions"] if q["problem"])
    try:
        index = max(0, min(int(request.GET.get("section", 1)) - 1, len(sections) - 1))
    except ValueError:
        index = 0
    done = sum(s["done"] for s in sections)
    total = sum(s["total"] for s in sections) or 1
    return render(request, "entries/application_form.html", {
        "problem_count": len(problems),
        "problem_sections": [(n, s) for n, s in enumerate(sections, start=1) if s["problems"]],
        "role": ROLE,
        "award": award,
        "application": application,
        "editable": editable,
        "edit_blocked": services.edit_blocked(application),
        "edit_request": application.requests.filter(kind="edit").first(),
        "sections": sections,
        "current": sections[index] if sections else {"name": "", "questions": []},
        "current_index": index + 1,
        "has_previous": index > 0,
        "has_next": index < len(sections) - 1,
        "progress": round(done * 100 / total),
        "other_applications": [a for a in mine if a.award_id != award.id],
    })


STEPS = [  # what the applicant sees on the timeline, in order
    (Application.Status.DRAFT, "Draft started"),
    (Application.Status.SUBMITTED, "Submitted"),
    (Application.Status.ASSIGNED, "Judges assigned"),
    (Application.Status.IN_REVIEW, "Being judged"),
    (Application.Status.SCORED, "Scored, waiting for the decision"),
]


def _timeline(application):
    """Steps with the date each one happened (from the audit log) and which are done."""
    dates = {}
    for entry in AuditLog.objects.filter(entity="application", entity_id=str(application.pk)).order_by("timestamp"):
        if entry.action == AuditLog.Action.CREATE:
            dates.setdefault(Application.Status.DRAFT, entry.timestamp)
        elif entry.action == AuditLog.Action.STATUS_CHANGE:
            dates[entry.changes.get("to")] = entry.timestamp
    order = [s for s, _ in STEPS]
    final = application.status in (Application.Status.APPROVED, Application.Status.REJECTED)
    reached = len(order) if final else order.index(application.status) + 1
    steps = [{"label": label, "date": dates.get(status), "state": "done" if i < reached else "todo"}
             for i, (status, label) in enumerate(STEPS)]
    if not final and reached:
        steps[reached - 1]["state"] = "current"
    if final:
        steps.append({"label": application.get_status_display(), "date": dates.get(application.status),
                      "state": "done"})
    return steps


@role_required("applicant")
def application_status(request):
    """Where each of the applicant's own applications is, with dates."""
    applications = services.visible_to(request.user).select_related("award", "form_version").order_by("-updated_at")
    return render(request, "entries/application_status.html", {
        "role": ROLE,
        "rows": [{"application": a, "timeline": _timeline(a), "can_reevaluate": services.can_request_reevaluation(a),
                  "requests": list(a.requests.select_related("staff_by", "decided_by"))} for a in applications],
    })


@role_required("applicant")
@require_POST
def delete_draft(request, pk):
    application = get_object_or_404(services.visible_to(request.user), pk=pk)
    if application.status != Application.Status.DRAFT:
        messages.error(request, "Only drafts can be deleted.")
    else:
        application.delete()   # soft delete
        messages.success(request, f"Draft {application.reference} deleted.")
    return redirect("entries:dashboard")


@role_required("applicant")
@require_POST
def request_reevaluation(request, pk):
    """Ask once, after the result, for fresh judges to score the application again."""
    application = get_object_or_404(services.visible_to(request.user), pk=pk)
    try:
        services.request_reevaluation(application, by=request.user, reason=request.POST.get("reason", ""))
    except BusinessRuleError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"{application.reference}: your request for a re-evaluation was sent to the "
                                  f"programme staff. You'll get a notification when they decide.")
    return redirect("entries:status")
