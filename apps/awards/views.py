"""
Programme staff screens, also used by award managers. Everyone here only ever
sees the awards they are on (apps/awards/access.py): staff the awards a leader or
manager allocated to them, managers the awards they manage. Creating an award is
a leader's job (dashboard). The home page, entries, judge assignment, the form
builder, award settings and duplicate review read and write the real database
through the services.
"""
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts import duplicates as duplicate_services
from apps.accounts import services as account_services
from apps.accounts.models import ApplicantProfile, DuplicateCandidate, User
from apps.accounts.permissions import role_required
from apps.applications import services as application_services
from apps.applications.models import Application
from apps.assignments import services as assignment_services
from apps.assignments.models import ConflictOfInterest
from apps.awards import services as award_services
from apps.awards.access import awards_for
from apps.awards.models import Award
from apps.core import approvals, overview
from apps.core.services import BusinessRuleError

OPEN = DuplicateCandidate.Status.OPEN


@role_required("staff", "manager")
def staff_home(request):
    """Home page: what needs staff today, from the database."""
    return render(request, "awards/staff_home.html", {"role": request.user.role, **overview.staff_home(request.user)})


@role_required("staff")
def form_builder(request, slug=None):
    """Each award's published form versions and their questions (read-only: published versions never change)."""
    awards = awards_for(request.user).order_by("name")
    award = get_object_or_404(awards, slug=slug) if slug else awards.filter(form_versions__isnull=False).first()
    if award is None:   # nothing set up yet
        return render(request, "awards/form_builder.html", {"role": request.user.role, "awards": awards, "award": None})
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
        "role": request.user.role, "awards": awards, "award": award, "versions": versions, "chosen": chosen,
        "sections": sections,
    })


@role_required("staff")
@require_http_methods(["GET", "POST"])
def form_edit(request, slug):
    """
    Edit the questions and publish them as a NEW version (Rule 4): the current
    version never changes, and applications already started keep their version.
    """
    award = get_object_or_404(awards_for(request.user), slug=slug)
    current = award.current_form
    blank = {"key": "", "label": "", "type": "textarea", "section": "", "subsection": "",
             "required": True, "identifying": False}
    if request.method == "POST":
        count = min(int(request.POST.get("rows", "0")) if request.POST.get("rows", "").isdigit() else 0, 300)
        rows = [{"key": request.POST.get(f"q-{n}-key", ""), "label": request.POST.get(f"q-{n}-label", ""),
                 "type": request.POST.get(f"q-{n}-type", ""), "section": request.POST.get(f"q-{n}-section", ""),
                 "subsection": request.POST.get(f"q-{n}-subsection", ""),
                 "required": request.POST.get(f"q-{n}-required") == "on",
                 "identifying": request.POST.get(f"q-{n}-identifying") == "on",
                 "remove": request.POST.get(f"q-{n}-remove") == "on"} for n in range(count)]
        try:
            version = award_services.publish_form_version(
                award, award_services.questions_from_editor(rows), request.user)
        except BusinessRuleError as error:
            messages.error(request, str(error))
            return _form_edit_page(request, award, current, rows)
        messages.success(request, f"Version {version.version} published. New applications use it; "
                                  f"applications already started keep their own version.")
        return redirect("awards:form_builder", slug=award.slug)
    rows = [{**blank, **q} for q in (current.questions if current else [])] or [dict(blank, section="Questions")]
    return _form_edit_page(request, award, current, rows)


def _form_edit_page(request, award, current, rows):
    """One card per section in the editor; each row keeps its position n (the q-<n>-* field names)."""
    sections = []
    for n, row in enumerate(rows):
        name = row.get("section") or ""
        if not sections or sections[-1]["name"] != name:
            sections.append({"name": name, "rows": []})
        sections[-1]["rows"].append({**row, "n": n})
    return render(request, "awards/form_edit.html", {
        "role": request.user.role, "award": award, "current": current, "sections": sections, "row_count": len(rows),
        "subcategories": sorted({row["subsection"].strip() for row in rows if (row.get("subsection") or "").strip()}),
        "blank": {"key": "", "type": "textarea", "required": True}, "types": award_services.QUESTION_TYPES})


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
    for n in range(1, award_services.MAX_ROUNDS + 2):   # one past the limit, so extras are refused
        kind = post.get(f"round{n}", "")
        if not kind:
            break                                  # rounds are numbered with no gaps
        rounds.append(kind)
    return fields, rounds, errors


def _award_form_page(request, award, values, rounds, **extra):
    leader = request.user.role == User.Role.LEADER
    return render(request, "awards/award_form.html", {
        "role": request.user.role, "award": award, "values": values,
        "rounds": rounds + [""] * (award_services.MAX_ROUNDS - len(rounds)),
        "round_kinds": award_services.ROUND_KINDS, "applicant_types": Award.ApplicantType.choices,
        "list_url": "dashboard:awards" if leader else "awards:award_list", **extra,
    })


def _active(role):
    return User.objects.filter(role=role, is_active=True).order_by("name", "email")


@role_required("staff", "manager")
def award_list(request):
    """The awards this person is on (staff: allocated to them; managers: the ones they manage)."""
    awards = (awards_for(request.user).select_related("manager").prefetch_related("rounds", "judge_panel", "staff")
              .annotate(entries=Count("applications")))
    return render(request, "awards/award_list.html", {
        "role": request.user.role,
        "rows": [{"award": a, "problems": award_services.ready_to_open(a) + award_services.ready_to_judge(a)}
                 for a in awards],
    })


@role_required("leader")
@require_http_methods(["GET", "POST"])
def award_new(request):
    """Leaders create awards and choose the award manager; the manager (or leader) then picks the staff."""
    managers = _active(User.Role.MANAGER)
    chosen = request.POST.get("manager", "")
    if request.method == "POST":
        fields, rounds, errors = _parse_award_form(request.POST)
        manager = managers.filter(pk=chosen).first() if chosen.isdigit() else None
        if chosen and manager is None:
            errors.append("Choose an active award manager from the list.")
        if not errors:
            try:
                with transaction.atomic():
                    award = award_services.create_award(by=request.user, rounds=rounds, **fields)
                    if manager:
                        award_services.set_team(award, by=request.user, staff=[], manager=manager,
                                                change_manager=True)
            except BusinessRuleError as error:
                errors.append(str(error))
            else:
                messages.success(request, f"{award.name} created. Next: choose its staff here; its manager "
                                          f"then sets up the questions, criteria and judges, and opens it.")
                return redirect("awards:award_team", slug=award.slug)
        for error in errors:
            messages.error(request, error)
        return _award_form_page(request, None, fields, rounds, managers=managers, chosen_manager=chosen)
    return _award_form_page(request, None, {"judges_per_report": 2, "entry_fee": 0}, ["desk"],
                            managers=managers, chosen_manager="")


@role_required("manager", "leader")
@require_http_methods(["GET", "POST"])
def award_team(request, slug):
    """
    Who runs this award. A leader picks the award manager and the staff; the award's
    manager picks the staff and can invite a new staff member straight onto the team.
    Staff only ever see the awards they are on.
    """
    award = get_object_or_404(awards_for(request.user).select_related("manager"), slug=slug)
    leader = request.user.role == User.Role.LEADER
    staff = _active(User.Role.STAFF)
    if request.method == "POST" and request.POST.get("action") == "invite":
        return _invite_staff(request, award)
    if request.method == "POST":
        chosen_staff = list(staff.filter(pk__in=_ids(request.POST.getlist("staff"))))
        manager = None
        if leader and request.POST.get("manager", "").isdigit():
            manager = _active(User.Role.MANAGER).filter(pk=request.POST["manager"]).first()
        try:
            award_services.set_team(award, by=request.user, staff=chosen_staff, manager=manager,
                                    change_manager=leader)
        except BusinessRuleError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"{award.name}: team saved ({len(chosen_staff)} staff"
                                      f"{', manager ' + manager.display_name if manager else ''}).")
        return redirect("awards:award_team", slug=award.slug)
    on_team = set(award.staff.values_list("pk", flat=True))
    return render(request, "awards/award_team.html", {
        "role": request.user.role, "award": award, "leader": leader,
        "staff": [{"user": s, "checked": s.pk in on_team} for s in staff],
        "managers": _active(User.Role.MANAGER) if leader else None,
        "list_url": "dashboard:awards" if leader else "awards:award_list",
    })


def _invite_staff(request, award):
    """Create a staff account, put it on this award's team and email the set-your-password link."""
    from django.conf import settings as django_settings
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email

    email = request.POST.get("email", "").strip().lower()
    name = request.POST.get("name", "").strip()
    try:
        if not name:
            raise BusinessRuleError("Give the person's name.")
        validate_email(email)
        with transaction.atomic():
            person = account_services.create_account(created_by=request.user, email=email, name=name,
                                                     role=User.Role.STAFF)
            award_services.set_team(award, by=request.user, staff=[*award.staff.filter(is_active=True), person])
            link = account_services.invite(person, by=request.user)
    except ValidationError:
        messages.error(request, "Enter a valid email address.")
    except BusinessRuleError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"{person.display_name} added to the {award.name} team. An email with a "
                                  f"set-your-password link was sent to {person.email}.")
        if django_settings.SHOW_INVITE_LINKS:
            messages.info(request, f"Email may not be set up yet: send {person.email} this one-time link "
                                   f"yourself: {link}")
    return redirect("awards:award_team", slug=award.slug)


@role_required("staff", "manager")
@require_http_methods(["GET", "POST"])
def award_edit(request, slug):
    award = get_object_or_404(awards_for(request.user), slug=slug)
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


@role_required("staff", "manager")
@require_POST
def award_status(request, slug):
    award = get_object_or_404(awards_for(request.user), slug=slug)
    try:
        award_services.set_status(award, by=request.user, status=request.POST.get("status", ""))
        messages.success(request, f"{award.name} is now {award.get_status_display().lower()}.")
    except BusinessRuleError as error:
        messages.error(request, str(error))
    return redirect("awards:award_edit", slug=award.slug)


@role_required("staff", "manager")
@require_http_methods(["GET", "POST"])
def award_criteria(request, slug):
    award = get_object_or_404(awards_for(request.user), slug=slug)
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
        "role": request.user.role, "award": award, "rows": rows, "rounds": rounds, "totals": totals, "locked": locked,
    })


@role_required("staff", "manager")
@require_http_methods(["GET", "POST"])
def award_panel(request, slug):
    award = get_object_or_404(awards_for(request.user), slug=slug)
    judges = User.objects.filter(role=User.Role.JUDGE).select_related("judge_profile").order_by("name", "email")
    if request.method == "POST":
        chosen = list(judges.filter(pk__in=_ids(request.POST.getlist("judges")), is_active=True))
        award_services.set_panel(award, by=request.user, judges=chosen)
        messages.success(request, f"{award.name}: {len(chosen)} judge{'s' if len(chosen) != 1 else ''} on the panel.")
        return redirect("awards:award_panel", slug=award.slug)
    on_panel = set(award.judge_panel.values_list("user_id", flat=True))
    return render(request, "awards/award_panel.html", {
        "role": request.user.role, "award": award, "on_panel": on_panel,
        "judges": [{"user": j, "checked": j.pk in on_panel} for j in judges],
    })


@role_required("staff", "manager")
def entries(request):
    """
    Every application on the awards this person is on, with what needs a decision:
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
        "role": request.user.role,
        "reports": reports.order_by("-updated_at"),
        "statuses": Application.Status.choices,
        "awards": awards_for(request.user).order_by("name"),
        "filters": filters,
        "to_verify": overview.organisations_to_verify(request.user),
        # verification follows the main record after a merge, so ask the duplicates service
        "verified_ids": {p.pk for p in ApplicantProfile.objects.filter(user__in=reports.values("applicant"))
                         if duplicate_services.is_verified(p)},
        "duplicate_ids": {pk for c in duplicate_services.candidates_for(request.user, status=OPEN)
                          for pk in (c.profile_a_id, c.profile_b_id)},
        **_requests_for(request.user),
    })


def _requests_for(user):
    """Requests on this person's awards: to check (staff), to confirm (the award manager), and the rest."""
    to_check = approvals.waiting(approvals.T.WAITING_STAFF, user)
    for row in to_check:
        row["can_check"] = approvals.can_check(user, row["request"])
    checked = approvals.waiting(approvals.T.WAITING_LEADER, user)
    mine = approvals.to_confirm(user, checked)
    return {"staff_requests": to_check, "confirm_requests": mine,
            "leader_requests": [r for r in checked if r not in mine]}


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


@role_required("staff", "manager")
@require_POST
def verify_organisation(request, pk):
    profile = get_object_or_404(overview.organisations_for(request.user), pk=pk)   # only on their awards
    approve = request.POST.get("decision") == "approve"
    return _decide(request, lambda: account_services.verify_organisation(
        profile, by=request.user, approve=approve, note=request.POST.get("note", "")),
        f"{profile.organisation_name}: {'verified' if approve else 'not verified'}.")


@role_required("staff", "manager")
@require_POST
def accept_report(request, pk):
    """Staff check passed: the entry can now be assigned to judges."""
    report = get_object_or_404(application_services.visible_to(request.user), pk=pk)
    return _decide(request, lambda: application_services.accept_entry(report, by=request.user),
                   f"{report.reference} accepted for judging. You can assign judges now.")


@role_required("staff", "manager")
@require_POST
def reject_report(request, pk):
    """Staff check failed: the entry is declined with a reason the applicant sees."""
    report = get_object_or_404(application_services.visible_to(request.user), pk=pk)
    return _decide(request, lambda: application_services.decline_entry(
        report, by=request.user, note=request.POST.get("note", "")), f"{report.reference} declined.")


@role_required("staff", "manager")
def assign(request, pk=None):
    """
    /staff/assign/        reports that still need judges (round 1)
    /staff/assign/<id>/   pick judges for one report: only eligible judges are offered
                          (on the panel, no recorded conflict, under their workload limit)
    """
    assignable = application_services.visible_to(request.user).filter(status__in=assignment_services.ASSIGNABLE)
    needing = [r for r in assignable.select_related("award", "applicant__applicant_profile").order_by("submitted_at")
               if assignment_services.judges_still_needed(r) > 0]
    if pk is None:
        return render(request, "awards/assign_list.html", {"role": request.user.role, "reports": needing})

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
        "role": request.user.role,
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


NOT_SHARED = "other"   # the tab for pairs that didn't both enter one award


def _duplicate_side(profile, award):
    """One organisation in a pair, as the duplicate card shows it."""
    main = duplicate_services.root(profile)
    entries = list(duplicate_services.entries_of([profile]).order_by("award__name"))
    return {"profile": profile, "main": main if main.pk != profile.pk else None,
            "verified": duplicate_services.is_verified(profile),
            "here": [e for e in entries if award and e.award_id == award.pk],
            "elsewhere": [e for e in entries if not award or e.award_id != award.pk]}


@role_required("staff")
def duplicates(request):
    """
    Programme staff only. Possible duplicate organisations, one tab per award: a pair is
    listed under an award only when both organisations entered it. The rest (one entered,
    or neither) are on the "Not in the same award" tab. Merge, keep separate, or undo.
    """
    user = request.user
    decided = request.GET.get("show") == "decided"
    pairs = duplicate_services.candidates_for(user)
    pairs = list(pairs.exclude(status=DuplicateCandidate.Status.OPEN) if decided
                 else pairs.filter(status=DuplicateCandidate.Status.OPEN))
    in_awards = {c.pk: duplicate_services.award_ids(c) for c in pairs}

    tabs = [{"key": a.slug, "award": a, "count": sum(a.pk in in_awards[c.pk] for c in pairs)}
            for a in awards_for(user).order_by("name")]
    tabs.append({"key": NOT_SHARED, "award": None, "count": sum(not in_awards[c.pk] for c in pairs)})
    chosen = request.GET.get("award") or next((t["key"] for t in tabs if t["count"]), tabs[0]["key"] if tabs else "")
    tab = next((t for t in tabs if t["key"] == chosen), None)
    award = tab["award"] if tab else None
    if tab is None:
        shown = []
    elif award is None:
        shown = [c for c in pairs if not in_awards[c.pk]]
    else:
        shown = [c for c in pairs if award.pk in in_awards[c.pk]]

    cards = [{"pair": c, "a": _duplicate_side(c.profile_a, award), "b": _duplicate_side(c.profile_b, award),
              "blockers": duplicate_services.merge_blockers(c) if c.status == DuplicateCandidate.Status.OPEN else []}
             for c in shown]
    return render(request, "awards/duplicates.html", {
        "role": user.role, "tabs": tabs, "tab": tab, "award": award, "cards": cards, "decided": decided,
        "can_decline": user.role in ("staff", "manager"),
    })


@role_required("staff")
@require_POST
def duplicate_decide(request, pk):
    pair = get_object_or_404(duplicate_services.candidates_for(request.user), pk=pk)
    action, note = request.POST.get("action"), request.POST.get("note", "").strip()
    if action == "merge":
        keep = pair.profile_a if request.POST.get("keep") == str(pair.profile_a_id) else pair.profile_b
        return _decide(request, lambda: duplicate_services.merge(pair, by=request.user, keep=keep, note=note),
                       f"Merged: {keep.organisation_name} is now the main record. Conflicts and verification "
                       f"apply to both.")
    if action == "separate":
        return _decide(request, lambda: duplicate_services.keep_separate(pair, by=request.user, note=note),
                       "Kept as separate organisations. This pair won't be flagged again.")
    if action == "undo":
        return _decide(request, lambda: duplicate_services.undo(pair, by=request.user),
                       "Decision undone. The pair is waiting for review again.")
    messages.error(request, "Unknown action.")
    return _back(request, "awards:duplicates")


# --- Re-evaluations: the award manager decides, then chooses fresh judges ----------------

@role_required("staff", "manager")
def reevaluations(request):
    """
    Re-evaluation requests on this person's awards. The award manager (a leader, if the award
    has no manager) approves or refuses; approving sends them straight to choosing new judges.
    Staff see the list and the progress, but don't decide.
    """
    from apps.applications.models import ApplicantRequest
    from apps.core import approvals
    from apps.core.results import RESULT_LABEL
    from apps.evaluations.services import applicant_progress

    mine = awards_for(request.user)
    requests = (ApplicantRequest.objects.filter(kind=ApplicantRequest.Kind.REEVALUATION, application__award__in=mine)
                .select_related("application__award__manager", "application__applicant__applicant_profile",
                                "decided_by").order_by("-created_at"))
    waiting = [r for r in requests if r.waiting]
    for req in waiting:
        app = req.application
        req.can_decide = approvals.can_decide_reevaluation(request.user, app.award)
        req.approver = approvals.reevaluation_approver(app.award)
        req.previous = RESULT_LABEL.get(app.status, app.get_status_display())
        req.scores = list(app.assignments.filter(evaluation__status="submitted").exclude(status="superseded")
                          .values_list("evaluation__total_score", flat=True))
    in_progress = [r.application for r in requests if r.status == ApplicantRequest.Status.APPROVED
                   and r.application.status not in (Application.Status.APPROVED, Application.Status.REJECTED)]
    for app in in_progress:
        app.needed = assignment_services.judges_still_needed(app)
        app.progress = applicant_progress(app)
    done = [r for r in requests if not r.waiting][:20]
    return render(request, "awards/reevaluations.html", {
        "role": request.user.role, "waiting": waiting, "in_progress": in_progress, "done": done,
        "can_assign": request.user.role in ("staff", "manager"),
    })


@role_required("staff", "manager")
@require_POST
def reevaluation_decide(request, pk):
    from apps.applications.models import ApplicantRequest

    req = get_object_or_404(ApplicantRequest.objects.filter(
        kind=ApplicantRequest.Kind.REEVALUATION, application__award__in=awards_for(request.user)), pk=pk)
    approve = request.POST.get("decision") == "approve"
    try:
        application_services.decide_request(req, by=request.user, approve=approve,
                                            note=request.POST.get("note", ""))
    except BusinessRuleError as error:
        messages.error(request, str(error))
        return redirect("awards:reevaluations")
    reference = req.application.reference
    if not approve:
        messages.success(request, f"{reference}: re-evaluation refused. The applicant has been told.")
        return redirect("awards:reevaluations")
    messages.success(request, f"{reference}: re-evaluation approved. Choose the new judges now; the first judges "
                              f"aren't offered again.")
    if request.user.role in ("staff", "manager"):
        return redirect("awards:assign", pk=req.application.pk)
    return redirect("awards:reevaluations")


# --- Results: the award manager decides each entry, then sends the award's result -----------

@role_required("staff", "manager")
def prepare_results(request):
    """
    One tab per award: entries still with staff or judges, scored entries to decide
    (Successful / Not successful, with every judge's total), decided entries, and
    "Send results to leadership". Leadership approves the award's result as a whole.
    """
    from apps.awards import results
    from apps.dashboard.views import _with_scores
    from apps.evaluations.models import Evaluation

    awards = list(awards_for(request.user).select_related("manager", "results_decided_by").order_by("name"))
    award = next((a for a in awards if a.slug == request.GET.get("award")), awards[0] if awards else None)
    context = {"role": request.user.role, "awards": awards, "award": award}
    if award:
        st = results.state(award)
        ids = [r.pk for r in st["to_decide"] + st["decided"]]
        scored = {r.pk: r for r in _with_scores(Application.objects.filter(pk__in=ids)
                                                .select_related("applicant__applicant_profile"))}
        for report in scored.values():
            report.totals = list(Evaluation.objects.filter(assignment__report=report, status="submitted")
                                 .exclude(assignment__status="superseded")
                                 .values_list("total_score", flat=True))
        context.update({
            "state": st, "can_prepare": results.can_prepare(request.user, award),
            "preparer": results.preparer_label(award),
            "to_decide": sorted((scored[r.pk] for r in st["to_decide"]), key=lambda r: -(r.average or 0)),
            "decided": sorted((scored[r.pk] for r in st["decided"]),
                              key=lambda r: (r.status != Application.Status.APPROVED, -(r.average or 0))),
        })
    return render(request, "awards/prepare_results.html", context)


@role_required("staff", "manager")
@require_POST
def decide_result(request, pk):
    from apps.awards import results

    report = get_object_or_404(application_services.visible_to(request.user), pk=pk)
    successful = request.POST.get("decision") == "successful"
    return _decide(request, lambda: results.decide_entry(report, by=request.user, successful=successful),
                   f"{report.reference}: {'successful' if successful else 'not successful'} (not published until "
                   f"leadership approves the award's result).")


@role_required("staff", "manager")
@require_POST
def send_results(request, slug):
    from apps.awards import results

    award = get_object_or_404(awards_for(request.user), slug=slug)
    return _decide(request, lambda: results.send_to_leadership(award, by=request.user,
                                                              note=request.POST.get("note", "")),
                   f"{award.name}: result sent to leadership for approval.")
