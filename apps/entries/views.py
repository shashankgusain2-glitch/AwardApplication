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
from apps.applications import services
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
    for q in application.form_version.questions:
        name = q.get("section") or "Your application"
        if not sections or sections[-1]["name"] != name:
            sections.append({"name": name, "questions": []})
        value = application.content.get(q["key"], "")
        sections[-1]["questions"].append({**q, "value": value})
    for s in sections:
        s["done"] = sum(1 for q in s["questions"] if str(q["value"]).strip())
        s["total"] = len(s["questions"])
    return sections


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
                keys = request.POST.getlist("keys")
                answers = {k: request.POST.get(f"q_{k}", "").strip() for k in keys}
                if services.can_edit(application):
                    services.update(application, by=request.user, content=answers)
                if action == "submit":
                    services.submit(application, by=request.user)
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
            raise Http404("This award isn't open")
        return render(request, "entries/application_start.html", {"role": ROLE, "award": award})

    sections = _sections(application)
    try:
        index = max(0, min(int(request.GET.get("section", 1)) - 1, len(sections) - 1))
    except ValueError:
        index = 0
    done = sum(s["done"] for s in sections)
    total = sum(s["total"] for s in sections) or 1
    return render(request, "entries/application_form.html", {
        "role": ROLE,
        "award": award,
        "application": application,
        "editable": services.can_edit(application),
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
        "rows": [{"application": a, "timeline": _timeline(a)} for a in applications],
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
