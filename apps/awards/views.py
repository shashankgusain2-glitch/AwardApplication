"""
Programme staff screens. The home page, entries, judge assignment, the
form builder and award settings read and write the real database through
the services; the duplicate-review screen still shows sample data (there is
no duplicate-detection model yet).
"""
from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts import services as account_services
from apps.accounts.models import ApplicantProfile, User
from apps.accounts.permissions import role_required
from apps.applications import services as application_services
from apps.applications.models import Application
from apps.assignments import services as assignment_services
from apps.assignments.models import ConflictOfInterest
from apps.awards import services as award_services
from apps.awards.models import Award
from apps.core import demo_data as d
from apps.core import overview
from apps.core.services import BusinessRuleError
from apps.evaluations import services as evaluation_services
from apps.evaluations.models import ScoreChangeRequest

ROLE = "staff"


@role_required("staff")
def staff_home(request):
    """Home page: what needs staff today, from the database."""
    return render(request, "awards/staff_home.html", {"role": ROLE, **overview.staff_home()})


def _clean_settings(post):
    """Check the submitted settings. Returns (settings, errors)."""
    errors = []
    settings = {}

    round1 = post.get("round1_type", "")
    round2 = post.get("round2_type", "none")
    if round1 not in d.ROUND_TYPES:
        errors.append("Choose how Round 1 is judged.")
    if round2 != "none" and round2 not in d.ROUND_TYPES:
        errors.append("Choose how Round 2 is judged, or 'No Round 2'.")
    settings["round_types"] = [round1] + ([round2] if round2 != "none" else [])

    settings["blind"] = post.get("blind") == "on"
    if settings["blind"] and not d.blind_possible(settings["round_types"]):
        errors.append(
            "Blind judging isn't possible: every round is in person (site visit or live presentation), "
            "so judges meet the applicant. Add a desk review round or turn blind judging off."
        )

    try:
        settings["judges_per_entry"] = int(post.get("judges_per_entry", ""))
        if not 1 <= settings["judges_per_entry"] <= 7:
            raise ValueError
    except ValueError:
        errors.append("Judges per entry must be a number from 1 to 7.")

    settings["applicant_type"] = post.get("applicant_type", "")
    if settings["applicant_type"] not in d.APPLICANT_TYPES:
        errors.append("Choose who applies from the list.")

    try:
        settings["fee_amount"] = int(post.get("fee_amount") or 0)
        if settings["fee_amount"] < 0:
            raise ValueError
    except ValueError:
        errors.append("Entry fee must be 0 or more (0 means no fee).")

    settings["deadline"] = post.get("deadline", "").strip()
    if not settings["deadline"] or len(settings["deadline"]) > 40:
        errors.append("Enter a closing date (up to 40 characters).")

    return settings, errors


@role_required("staff")
@require_http_methods(["GET", "POST"])
def settings(request):
    """Award settings. Saved into the Award tables; the descriptions shown come from the award catalogue."""
    if request.method == "POST":
        slug = request.POST.get("slug")
        award = d.get_award(slug, request)
        if award is None or slug not in d.BUILT_AWARDS:
            raise Http404("Award not found")

        if "reset" in request.POST:
            award_services.reset_screen_settings(slug, request.user)
            messages.success(request, f"{award['name']} is back to its default settings.")
        else:
            new_settings, errors = _clean_settings(request.POST)
            if errors:
                for error in errors:
                    messages.error(request, f"{award['name']}: {error}")
                return redirect("awards:settings")
            try:
                award_services.save_screen_settings(slug, new_settings, request.user)
            except BusinessRuleError as error:
                messages.error(request, f"{award['name']}: {error}")
                return redirect("awards:settings")
            messages.success(request, f"Saved {award['name']}. Every screen now follows these settings.")
        return redirect("awards:settings")

    return render(request, "awards/settings.html", {
        "role": ROLE,
        "awards": d.built_awards(request),
        "applicant_types": d.APPLICANT_TYPES,
        "round_types": d.ROUND_TYPES,
    })


@role_required("staff")
def form_builder(request, slug=None):
    """Each award's published form versions and their questions (read-only: published versions never change)."""
    awards = Award.objects.order_by("name")
    award = get_object_or_404(Award, slug=slug) if slug else awards.filter(form_versions__isnull=False).first()
    if award is None:   # nothing set up yet
        return render(request, "awards/form_builder.html", {"role": ROLE, "awards": awards, "award": None})
    versions = list(award.form_versions.annotate(applications_count=Count("applications")).order_by("-version"))
    try:
        wanted = int(request.GET.get("version", 0))
    except ValueError:
        wanted = 0
    chosen = next((v for v in versions if v.version == wanted), versions[0] if versions else None)
    sections = []
    for q in chosen.questions if chosen else []:
        name = q.get("section") or "Questions"
        if not sections or sections[-1]["name"] != name:
            sections.append({"name": name, "questions": []})
        sections[-1]["questions"].append(q)
    return render(request, "awards/form_builder.html", {
        "role": ROLE, "awards": awards, "award": award, "versions": versions, "chosen": chosen,
        "sections": sections,
    })


@role_required("staff")
@require_http_methods(["GET", "POST"])
def form_edit(request, slug):
    """
    Edit the questions and publish them as a NEW version (Rule 4): the current
    version never changes, and applications already started keep their version.
    """
    award = get_object_or_404(Award, slug=slug)
    current = award.current_form
    blank = {"key": "", "label": "", "type": "textarea", "section": "", "required": True, "identifying": False}
    if request.method == "POST":
        count = min(int(request.POST.get("rows", "0")) if request.POST.get("rows", "").isdigit() else 0, 300)
        rows = [{"key": request.POST.get(f"q-{n}-key", ""), "label": request.POST.get(f"q-{n}-label", ""),
                 "type": request.POST.get(f"q-{n}-type", ""), "section": request.POST.get(f"q-{n}-section", ""),
                 "required": request.POST.get(f"q-{n}-required") == "on",
                 "identifying": request.POST.get(f"q-{n}-identifying") == "on",
                 "remove": request.POST.get(f"q-{n}-remove") == "on"} for n in range(count)]
        try:
            version = award_services.publish_form_version(
                award, award_services.questions_from_editor(rows), request.user)
        except BusinessRuleError as error:
            messages.error(request, str(error))
            return render(request, "awards/form_edit.html", {
                "role": ROLE, "award": award, "current": current, "rows": rows,
                "types": award_services.QUESTION_TYPES})
        messages.success(request, f"Version {version.version} published. New applications use it; "
                                  f"applications already started keep their own version.")
        return redirect("awards:form_builder", slug=award.slug)
    rows = [{**blank, **q} for q in (current.questions if current else [])]
    rows += [dict(blank, section=rows[-1]["section"] if rows else "") for _ in range(3)]   # room for new questions
    return render(request, "awards/form_edit.html", {
        "role": ROLE, "award": award, "current": current, "rows": rows, "types": award_services.QUESTION_TYPES})


# --- Award administration: any number of awards, set up without code ------------

def _parse_award_form(post):
    """The award form's fields as Python values. Returns (fields, rounds, errors)."""
    from datetime import date
    errors = []

    def day(name, label):
        raw = post.get(name, "").strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            errors.append(f"{label}: use a date like 2026-12-15.")
            return None

    def number(name, label, default):
        raw = post.get(name, "").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            errors.append(f"{label} must be a whole number.")
            return default

    fields = {
        "name": post.get("name", "").strip(), "sector": post.get("sector", "").strip(),
        "summary": post.get("summary", "").strip(),
        "opens_on": day("opens_on", "Opens on"), "closes_on": day("closes_on", "Closes on"),
        "applicant_type": post.get("applicant_type", Award.ApplicantType.ORGANISATION),
        "judges_per_report": number("judges_per_report", "Judges per report", 2),
        "blind_judging": post.get("blind_judging") == "on",
        "entry_fee": number("entry_fee", "Entry fee", 0),
    }
    if fields["applicant_type"] not in Award.ApplicantType.values:
        errors.append("Choose who applies from the list.")
    rounds = []
    for n in range(1, 6):
        kind = post.get(f"round{n}", "")
        if not kind:
            break                                  # rounds are numbered with no gaps
        rounds.append(kind)
    return fields, rounds, errors


def _award_form_page(request, award, values, rounds):
    return render(request, "awards/award_form.html", {
        "role": ROLE, "award": award, "values": values, "rounds": rounds + [""] * (5 - len(rounds)),
        "round_kinds": award_services.ROUND_KINDS, "applicant_types": Award.ApplicantType.choices,
    })


@role_required("staff")
def award_list(request):
    awards = Award.objects.prefetch_related("rounds", "judge_panel").annotate(entries=Count("applications"))
    return render(request, "awards/award_list.html", {
        "role": ROLE,
        "rows": [{"award": a, "problems": award_services.ready_to_open(a)} for a in awards],
    })


@role_required("staff")
@require_http_methods(["GET", "POST"])
def award_new(request):
    if request.method == "POST":
        fields, rounds, errors = _parse_award_form(request.POST)
        if not errors:
            try:
                award = award_services.create_award(by=request.user, rounds=rounds, **fields)
            except BusinessRuleError as error:
                errors.append(str(error))
            else:
                messages.success(request, f"{award.name} created. Next: add its questions, criteria and judges, "
                                          f"then open it.")
                return redirect("awards:award_edit", slug=award.slug)
        for error in errors:
            messages.error(request, error)
        return _award_form_page(request, None, fields, rounds)
    return _award_form_page(request, None, {"judges_per_report": 2, "entry_fee": 0}, ["desk"])


@role_required("staff")
@require_http_methods(["GET", "POST"])
def award_edit(request, slug):
    award = get_object_or_404(Award, slug=slug)
    if request.method == "POST":
        fields, rounds, errors = _parse_award_form(request.POST)
        if not errors:
            try:
                award_services.update_award(award, by=request.user, rounds=rounds, **fields)
            except BusinessRuleError as error:
                errors.append(str(error))
            else:
                messages.success(request, f"Saved {award.name}.")
                return redirect("awards:award_edit", slug=award.slug)
        for error in errors:
            messages.error(request, error)
        return _award_form_page(request, award, fields, rounds)
    values = {f: getattr(award, f) for f in ("name", "sector", "summary", "opens_on", "closes_on", "applicant_type",
                                              "judges_per_report", "blind_judging", "entry_fee")}
    return _award_form_page(request, award, values, [r.kind for r in award.rounds.all()])


@role_required("staff")
@require_POST
def award_status(request, slug):
    award = get_object_or_404(Award, slug=slug)
    try:
        award_services.set_status(award, by=request.user, status=request.POST.get("status", ""))
        messages.success(request, f"{award.name} is now {award.get_status_display().lower()}.")
    except BusinessRuleError as error:
        messages.error(request, str(error))
    return redirect("awards:award_edit", slug=award.slug)


@role_required("staff")
@require_http_methods(["GET", "POST"])
def award_criteria(request, slug):
    award = get_object_or_404(Award, slug=slug)
    locked = award_services.criteria_locked(award)
    if request.method == "POST":
        count = min(int(request.POST["rows"]) if request.POST.get("rows", "").isdigit() else 0, 100)
        rows = [{"round_number": request.POST.get(f"c-{n}-round", "1"), "key": request.POST.get(f"c-{n}-key", ""),
                 "label": request.POST.get(f"c-{n}-label", ""), "weight": request.POST.get(f"c-{n}-weight", ""),
                 "remove": request.POST.get(f"c-{n}-remove") == "on"} for n in range(count)]
        try:
            award_services.save_criteria(award, by=request.user, rows=rows)
        except BusinessRuleError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"Criteria saved for {award.name}.")
            return redirect("awards:award_criteria", slug=award.slug)
    else:
        rows = [{"round_number": c.round_number, "key": c.key, "label": c.label, "weight": c.weight}
                for c in award.criteria.all()]
    rounds = list(award.rounds.all())
    if not locked:
        rows = list(rows) + [{"round_number": r.number, "key": "", "label": "", "weight": ""}
                             for r in rounds for _ in range(2)]   # room to add two per round
    totals = {r.number: sum(int(c["weight"]) for c in rows if str(c["round_number"]) == str(r.number)
                            and str(c.get("weight", "")).isdigit() and c.get("label") and not c.get("remove"))
              for r in rounds}
    return render(request, "awards/award_criteria.html", {
        "role": ROLE, "award": award, "rows": rows, "rounds": rounds, "totals": totals, "locked": locked,
    })


@role_required("staff")
@require_http_methods(["GET", "POST"])
def award_panel(request, slug):
    award = get_object_or_404(Award, slug=slug)
    judges = User.objects.filter(role=User.Role.JUDGE).select_related("judge_profile").order_by("name", "email")
    if request.method == "POST":
        chosen = list(judges.filter(pk__in=_ids(request.POST.getlist("judges")), is_active=True))
        award_services.set_panel(award, by=request.user, judges=chosen)
        messages.success(request, f"{award.name}: {len(chosen)} judge{'s' if len(chosen) != 1 else ''} on the panel.")
        return redirect("awards:award_panel", slug=award.slug)
    on_panel = set(award.judge_panel.values_list("user_id", flat=True))
    return render(request, "awards/award_panel.html", {
        "role": ROLE, "award": award, "on_panel": on_panel,
        "judges": [{"user": j, "checked": j.pk in on_panel} for j in judges],
    })


@role_required("staff")
def entries(request):
    """
    Every application (staff see all), with what needs a decision:
    organisations to verify, edit requests and judges' score-change requests.
    """
    reports = application_services.visible_to(request.user).select_related("applicant__applicant_profile")
    filters = {"status": request.GET.get("status", ""), "award": request.GET.get("award", ""),
               "q": request.GET.get("q", "").strip()}
    if filters["status"]:
        reports = reports.filter(status=filters["status"])
    if filters["award"]:
        reports = reports.filter(award__slug=filters["award"])
    if filters["q"]:
        reports = reports.filter(Q(reference__icontains=filters["q"]) | Q(title__icontains=filters["q"])
                                 | Q(applicant__applicant_profile__organisation_name__icontains=filters["q"]))
    return render(request, "awards/entries.html", {
        "role": ROLE,
        "reports": reports.order_by("-updated_at"),
        "statuses": Application.Status.choices,
        "awards": Award.objects.order_by("name"),
        "filters": filters,
        "to_verify": ApplicantProfile.objects.filter(verification_status=ApplicantProfile.Verification.PENDING)
                                             .select_related("user"),
        "edit_requests": Application.objects.filter(edit_requested=True).select_related("award"),
        "score_requests": ScoreChangeRequest.objects.filter(status=ScoreChangeRequest.Status.REQUESTED)
                                                    .select_related("evaluation__assignment__judge",
                                                                    "evaluation__assignment__report"),
    })


def _ids(values):
    """Only whole-number ids from a form (anything else is ignored, not a crash)."""
    return [int(v) for v in values if str(v).isdigit()]


def _back(request, default="awards:entries"):
    """Go back to the staff page the form was on (only staff pages are allowed)."""
    target = request.POST.get("next", "")
    return redirect(target if target.startswith("/staff/") else default)


def _decide(request, action, success):
    try:
        action()
        messages.success(request, success)
    except BusinessRuleError as error:
        messages.error(request, str(error))
    return _back(request)


@role_required("staff")
@require_POST
def verify_organisation(request, pk):
    profile = get_object_or_404(ApplicantProfile, pk=pk)
    approve = request.POST.get("decision") == "approve"
    return _decide(request, lambda: account_services.verify_organisation(
        profile, by=request.user, approve=approve, note=request.POST.get("note", "")),
        f"{profile.organisation_name}: {'verified' if approve else 'not verified'}.")


@role_required("staff")
@require_POST
def decide_edit(request, pk):
    report = get_object_or_404(application_services.visible_to(request.user), pk=pk)
    allow = request.POST.get("decision") == "allow"
    return _decide(request, lambda: application_services.decide_edit(report, by=request.user, allow=allow),
                   f"{report.reference}: edit {'allowed' if allow else 'refused'}.")


@role_required("staff")
@require_POST
def decide_score_change(request, pk):
    change_request = get_object_or_404(ScoreChangeRequest, pk=pk)
    approve = request.POST.get("decision") == "approve"
    return _decide(request, lambda: evaluation_services.decide_change(change_request, by=request.user,
                                                                      approve=approve),
                   f"Score change {'allowed' if approve else 'refused'}.")


@role_required("staff")
@require_POST
def reject_report(request, pk):
    """Staff check: a submitted report that isn't eligible is rejected (with a note)."""
    report = get_object_or_404(application_services.visible_to(request.user), pk=pk)
    return _decide(request, lambda: application_services.change_status(
        report, by=request.user, new_status=Application.Status.REJECTED, note=request.POST.get("note", "")),
        f"{report.reference} rejected.")


@role_required("staff")
def assign(request, pk=None):
    """
    /staff/assign/        reports that still need judges (round 1)
    /staff/assign/<id>/   pick judges for one report: only eligible judges are offered
                          (on the panel, no recorded conflict, under their workload limit)
    """
    needing = [r for r in Application.objects.filter(status__in=assignment_services.ASSIGNABLE)
               .select_related("award", "applicant__applicant_profile").order_by("submitted_at")
               if assignment_services.judges_still_needed(r) > 0]
    if pk is None:
        return render(request, "awards/assign_list.html", {"role": ROLE, "reports": needing})

    report = get_object_or_404(application_services.visible_to(request.user), pk=pk)
    if request.method == "POST":
        try:
            if request.POST.get("action") == "auto":
                made = assignment_services.auto_assign(report, by=request.user)
            else:
                judges = list(User.objects.filter(pk__in=_ids(request.POST.getlist("judges")), role=User.Role.JUDGE))
                if not judges:
                    raise BusinessRuleError("Choose at least one judge.")
                made = assignment_services.bulk_assign([(report, j) for j in judges], by=request.user)
            names = ", ".join(a.judge.display_name for a in made) or "nobody (it already has enough judges)"
            messages.success(request, f"{report.reference}: assigned {names}. They have been notified.")
        except BusinessRuleError as error:
            messages.error(request, str(error))
        return redirect("awards:assign", pk=report.pk)

    profile = ApplicantProfile.objects.filter(user=report.applicant).first()
    return render(request, "awards/assign.html", {
        "role": ROLE,
        "report": report,
        "profile": profile,
        "current": report.assignments.select_related("judge").order_by("round", "assigned_at"),
        "eligible": assignment_services.eligible_judges(report),
        "needed": assignment_services.judges_still_needed(report),
        "assignable": report.status in assignment_services.ASSIGNABLE,
        "conflicted": ConflictOfInterest.objects.filter(applicant_profile=profile).count() if profile else 0,
        "verified": bool(profile and profile.verification_status == ApplicantProfile.Verification.VERIFIED),
        "next_reports": [r for r in needing if r.pk != report.pk][:5],
    })


@role_required("staff")
def duplicates(request):
    """Sample data: duplicate detection needs its own model (a later step)."""
    return render(request, "awards/duplicates.html", {
        "role": ROLE,
        "duplicates": d.DUPLICATES,
    })
