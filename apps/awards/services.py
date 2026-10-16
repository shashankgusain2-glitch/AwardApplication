"""
Award business logic: settings, rounds, form versions and criteria.
"""
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record
from apps.core.services import BusinessRuleError

from .models import Award, AwardRound, Criterion, FormVersion

# The portal screens use display labels; the database stores codes.
APPLICANT_TYPE_FROM_LABEL = {label: value for value, label in Award.ApplicantType.choices}
APPLICANT_TYPE_TO_LABEL = dict(Award.ApplicantType.choices)
DEMO_STATUS_TO_CODE = {"Open": "open", "Closing soon": "open", "Judging": "judging",
                       "Results": "results", "Upcoming": "upcoming"}


def parse_display_date(text):
    """'15 Dec 2026' → date. The portal screens show and accept dates like this."""
    try:
        return datetime.strptime(text.strip(), "%d %b %Y").date()
    except (ValueError, AttributeError):
        raise BusinessRuleError("Enter the closing date like 15 Dec 2026.") from None


def format_display_date(date):
    return f"{date.day} {date:%b %Y}" if date else ""


def get_or_create_from_demo(slug):
    """Make sure an Award row exists for one of the demo awards (portal screens)."""
    from apps.core import demo_data
    base = next((a for a in demo_data.AWARDS if a["slug"] == slug), None)
    if base is None:
        raise BusinessRuleError("Award not found.")
    award, created = Award.objects.get_or_create(slug=slug, defaults={
        "name": base["name"], "sector": base["sector"], "summary": base["summary"],
        "status": DEMO_STATUS_TO_CODE.get(base["status"], "upcoming"),
        "applicant_type": APPLICANT_TYPE_FROM_LABEL.get(base["applicant_type"], "organisation"),
        "judges_per_report": base["judges_per_entry"], "blind_judging": base["blind"],
        "entry_fee": base.get("fee_amount", 0),
    })
    if created:
        set_rounds(award, base["round_types"])
    return award


def set_rounds(award, kinds):
    award.rounds.all().delete()
    AwardRound.objects.bulk_create([AwardRound(award=award, number=i, kind=k) for i, k in enumerate(kinds, start=1)])


def screen_overrides():
    """Settings saved in the Award tables, in the shape the public award pages expect."""
    out = {}
    for award in Award.objects.prefetch_related("rounds"):
        values = {
            "blind": award.blind_judging,
            "judges_per_entry": award.judges_per_report,
            "applicant_type": APPLICANT_TYPE_TO_LABEL[award.applicant_type],
            "fee_amount": award.entry_fee,
        }
        kinds = [r.kind for r in award.rounds.all()]
        if kinds:
            values["round_types"] = kinds
        if award.closes_on:
            values["deadline"] = format_display_date(award.closes_on)
        out[award.slug] = values
    return out


# --- Forms (Rule 4) and criteria -------------------------------------------------

@transaction.atomic
def publish_form_version(award, questions, by):
    """Publish new questions as the next version. Existing versions never change."""
    if not questions:
        raise BusinessRuleError("A form needs at least one question.")
    keys = [q.get("key") for q in questions]
    if len(keys) != len(set(keys)) or not all(keys):
        raise BusinessRuleError("Every question needs a unique key.")
    latest = award.form_versions.order_by("-version").first()
    version = FormVersion.objects.create(award=award, version=(latest.version + 1 if latest else 1),
                                         questions=questions, published_at=timezone.now())
    record(by, "create", version, changes={"questions": len(questions)})
    return version


QUESTION_TYPES = {"text": "Short text", "textarea": "Long text", "file": "File"}


def questions_from_editor(rows):
    """
    Turn the form-builder rows into a question list for a new version.
    rows: [{key, label, type, section, subsection, required, identifying, remove}] in order. Rows marked
    remove, and new rows left blank, are dropped. Existing questions keep their key, so answers
    in applications on older versions stay linked; new questions get a key made from the label.
    """
    from django.utils.text import slugify

    questions, keys = [], set()
    for n, row in enumerate(rows, start=1):
        label = (row.get("label") or "").strip()
        if row.get("remove") or (not label and not row.get("key")):
            continue
        if not label:
            raise BusinessRuleError(f"Question {n} needs a question text (or tick Remove).")
        if row.get("type") not in QUESTION_TYPES:
            raise BusinessRuleError(f"Question {n}: choose short text, long text or file.")
        key = row.get("key") or slugify(label)[:40].replace("-", "_") or f"question_{n}"
        base, i = key, 2
        while key in keys:                       # two new questions with the same text
            key, i = f"{base}_{i}", i + 1
        keys.add(key)
        questions.append({"key": key, "label": label, "type": row["type"],
                          "section": (row.get("section") or "").strip() or "Questions",
                          "subsection": (row.get("subsection") or "").strip(),
                          "required": bool(row.get("required")), "identifying": bool(row.get("identifying"))})
    return questions


# --- Award administration (staff create and run any award) -----------------------

ROUND_KINDS = dict(AwardRound.Kind.choices)
MAX_ROUNDS = 2                                     # e.g. desk review, then a site visit or live round


def _unique_slug(name, exclude_pk=None):
    from django.utils.text import slugify
    base = slugify(name)[:50] or "award"
    slug, n = base, 2
    while Award.all_objects.filter(slug=slug).exclude(pk=exclude_pk).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def _check_award_fields(*, name, judges_per_report, opens_on, closes_on, rounds, blind_judging, entry_fee):
    if not (name or "").strip():
        raise BusinessRuleError("Give the award a name.")
    if not 1 <= judges_per_report <= 7:
        raise BusinessRuleError("Judges per report must be from 1 to 7.")
    if entry_fee < 0:
        raise BusinessRuleError("The entry fee can't be negative (0 means no fee).")
    if opens_on and closes_on and closes_on < opens_on:
        raise BusinessRuleError("The closing date can't be before the opening date.")
    if not rounds:
        raise BusinessRuleError("An award needs at least one judging round.")
    if len(rounds) > MAX_ROUNDS:
        raise BusinessRuleError(f"An award can have at most {MAX_ROUNDS} rounds.")
    if any(kind not in ROUND_KINDS for kind in rounds):
        raise BusinessRuleError("Each round must be a desk review, site visit or live presentation.")
    if blind_judging and "desk" not in rounds:
        raise BusinessRuleError("Blind judging needs a desk review round: on site visits and live "
                                "presentations judges meet the applicant.")


def _sync_rounds(award, rounds):
    """Change the rounds, but never remove a round that already has judges assigned."""
    from apps.assignments.models import JudgeAssignment
    used = set(JudgeAssignment.objects.filter(report__award=award).values_list("round", flat=True))
    dropped = {r.number for r in award.rounds.all()} - set(range(1, len(rounds) + 1))
    if used & dropped:
        raise BusinessRuleError(f"Round {min(used & dropped)} already has judges assigned, so it can't be removed.")
    set_rounds(award, rounds)


@transaction.atomic
def create_award(*, by, name, rounds, sector="", summary="", opens_on=None, closes_on=None,
                 applicant_type=Award.ApplicantType.ORGANISATION, judges_per_report=2, blind_judging=False,
                 entry_fee=0):
    """
    A new award, always starting as Upcoming (open it once it has a form, criteria and judges).
    Only a leader creates awards; they then choose its manager and staff (set_team).
    """
    from apps.accounts.models import User
    if not (by.role == User.Role.LEADER or by.is_superuser):
        raise BusinessRuleError("Only a leader can create a new award.")
    _check_award_fields(name=name, judges_per_report=judges_per_report, opens_on=opens_on, closes_on=closes_on,
                        rounds=rounds, blind_judging=blind_judging, entry_fee=entry_fee)
    award = Award.objects.create(slug=_unique_slug(name), name=name.strip(), sector=sector, summary=summary,
                                 status=Award.Status.UPCOMING, opens_on=opens_on, closes_on=closes_on,
                                 applicant_type=applicant_type, judges_per_report=judges_per_report,
                                 blind_judging=blind_judging, entry_fee=entry_fee)
    set_rounds(award, rounds)
    record(by, "create", award, changes={"name": award.name, "rounds": rounds})
    return award


@transaction.atomic
def update_award(award, *, by, rounds, **fields):
    _check_award_fields(name=fields["name"], judges_per_report=fields["judges_per_report"],
                        opens_on=fields.get("opens_on"), closes_on=fields.get("closes_on"), rounds=rounds,
                        blind_judging=fields["blind_judging"], entry_fee=fields["entry_fee"])
    before = {k: str(getattr(award, k)) for k in fields}
    for key, value in fields.items():
        setattr(award, key, value.strip() if isinstance(value, str) else value)
    award.save()
    _sync_rounds(award, rounds)
    record(by, "update", award, changes={"before": before, "after": {k: str(v) for k, v in fields.items()},
                                         "rounds": rounds})
    return award


def ready_to_open(award):
    """What is missing before applicants can apply: only the form. An empty list means ready."""
    problems = []
    if award.current_form is None:
        problems.append("Publish the application form (Form builder → Edit questions).")
    return problems


def ready_to_judge(award):
    """What is missing before judges can be assigned: criteria for every round and a panel."""
    problems = []
    for r in award.rounds.all():
        total = sum(award.criteria.filter(round_number=r.number).values_list("weight", flat=True))
        if total != 100:
            problems.append(f"Round {r.number} criteria weights add up to {total}, not 100.")
    if not award.judge_panel.exists():
        problems.append("Choose at least one judge for the panel.")
    return problems


def apply_date_rules(today=None):
    """
    Open and close awards by their dates, so staff don't have to remember to:
      Upcoming → Open    on the opening date, if the form is published and it hasn't closed yet
      Open     → Closed  the day after the closing date
    An award with no opening date stays Upcoming until staff open it. Each change is audited
    (no user: the system did it). Cheap when nothing is due: two small queries.
    """
    today = today or timezone.localdate()
    due_to_open = (Award.objects.filter(status=Award.Status.UPCOMING, opens_on__lte=today)
                   .exclude(closes_on__lt=today).filter(form_versions__published_at__isnull=False).distinct())
    due_to_close = Award.objects.filter(status=Award.Status.OPEN, closes_on__lt=today)
    changed = []
    for awards, status, reason in ((due_to_open, Award.Status.OPEN, "opening date reached"),
                                   (due_to_close, Award.Status.CLOSED, "closing date passed")):
        for award in awards:
            before = award.status
            award.status = status
            award.save(update_fields=["status", "updated_at"])
            record(None, "status_change", award, changes={"from": before, "to": status, "automatic": reason})
            changed.append(award)
    return changed


@transaction.atomic
def set_status(award, *, by, status):
    if status not in Award.Status.values:
        raise BusinessRuleError("Unknown award status.")
    if status == Award.Status.OPEN:
        problems = ready_to_open(award)
        if problems:
            raise BusinessRuleError("Not ready to open: " + " ".join(problems))
        if award.closes_on and award.closes_on < timezone.localdate():
            raise BusinessRuleError("The closing date has passed. Move the closing date later first.")
    if status == Award.Status.JUDGING:
        problems = ready_to_judge(award)
        if problems:
            raise BusinessRuleError("Not ready for judging: " + " ".join(problems))
    before = award.status
    award.status = status
    award.save(update_fields=["status", "updated_at"])
    record(by, "status_change", award, changes={"from": before, "to": status})
    return award


def criteria_locked(award):
    """Criteria can't change once any judge has scored this award: totals would change under them."""
    from apps.evaluations.models import CriterionScore
    return CriterionScore.objects.filter(criterion__award=award).exists()


@transaction.atomic
def save_criteria(award, *, by, rows):
    """
    Replace the award's criteria. rows: [{round_number, key, label, weight, remove}] in order.
    Weights must add up to 100 in every round. Locked once judging has started.
    """
    from django.utils.text import slugify
    if criteria_locked(award):
        raise BusinessRuleError("Judges have already scored this award, so its criteria can't change.")
    rounds = {r.number for r in award.rounds.all()}
    kept, totals = [], {}
    for n, row in enumerate(rows, start=1):
        label = (row.get("label") or "").strip()
        if row.get("remove") or not label:
            continue
        try:
            number = int(row.get("round_number") or 1)
        except (TypeError, ValueError):
            raise BusinessRuleError(f"Criterion {n} ({label}): unknown round.") from None
        if number not in rounds:
            raise BusinessRuleError(f"Criterion {n}: round {number} doesn't exist for this award.")
        try:
            weight = int(row.get("weight"))
        except (TypeError, ValueError):
            raise BusinessRuleError(f"Criterion {n} ({label}): the weight must be a whole number.") from None
        if not 1 <= weight <= 100:
            raise BusinessRuleError(f"Criterion {n} ({label}): the weight must be from 1 to 100.")
        key = row.get("key") or slugify(label)[:50]
        kept.append({"round_number": number, "key": key, "label": label, "weight": weight})
        totals[number] = totals.get(number, 0) + weight
    for number in sorted(rounds):
        if totals.get(number, 0) != 100:
            raise BusinessRuleError(f"Round {number} weights add up to {totals.get(number, 0)}, not 100.")
    keys = [(c["round_number"], c["key"]) for c in kept]
    if len(keys) != len(set(keys)):
        raise BusinessRuleError("Two criteria in the same round have the same name.")
    award.criteria.all().delete()
    for order, c in enumerate(kept):
        Criterion.objects.create(award=award, order=order, **c)
    record(by, "update", award, changes={"criteria": [f"R{c['round_number']} {c['label']} {c['weight']}%"
                                                      for c in kept]})
    return kept


@transaction.atomic
def set_panel(award, *, by, judges):
    """The judges who may be assigned this award's reports. Removing a judge keeps their existing assignments."""
    from apps.accounts.models import JudgeProfile, User
    judges = [j for j in judges if j.role == User.Role.JUDGE]
    wanted = {j.pk for j in judges}
    for profile in JudgeProfile.objects.filter(awards=award).exclude(user_id__in=wanted):
        profile.awards.remove(award)
    for judge in judges:
        profile, _ = JudgeProfile.objects.get_or_create(user=judge)
        profile.awards.add(award)
    record(by, "update", award, changes={"panel": sorted(j.email for j in judges)})
    return judges


def check_criteria_weights(award, round_number=1):
    total = sum(Criterion.objects.filter(award=award, round_number=round_number).values_list("weight", flat=True))
    if total != 100:
        raise BusinessRuleError(f"Round {round_number} weights add up to {total}, not 100.")


@transaction.atomic
def set_team(award, *, by, staff, manager=None, change_manager=False):
    """
    Who runs this award. A leader picks the award manager and the staff; the award's
    manager picks the staff only. Newly added people are told. Audited.
    """
    from apps.accounts.models import User
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    is_leader = by.role == User.Role.LEADER or by.is_superuser
    if not is_leader and not (by.role == User.Role.MANAGER and award.manager_id == by.pk):
        raise BusinessRuleError("Only a leader or this award's manager can choose its team.")
    if change_manager and not is_leader:
        raise BusinessRuleError("Only a leader can choose an award's manager.")
    if change_manager and manager is not None and (manager.role != User.Role.MANAGER or not manager.is_active):
        raise BusinessRuleError("The award manager must be an active account with the Award manager role.")
    if any(s.role != User.Role.STAFF or not s.is_active for s in staff):
        raise BusinessRuleError("Only active programme staff accounts can be allocated to an award.")

    before_staff = set(award.staff.values_list("pk", flat=True))
    before_manager = award.manager
    award.staff.set(staff)
    if change_manager:
        award.manager = manager
        award.save(update_fields=["manager", "updated_at"])
    record(by, "update", award, changes={
        "staff": sorted(s.email for s in staff),
        **({"manager": manager.email if manager else None} if change_manager else {})})

    from django.urls import reverse
    link = reverse("awards:staff_home")
    for person in staff:
        if person.pk not in before_staff:
            notify(person, f"You've been added to the team for {award.name}.", kind=Notification.Kind.INFO,
                   link=link)
    if change_manager and manager is not None and manager != before_manager:
        notify(manager, f"You are now the award manager for {award.name}.", kind=Notification.Kind.INFO,
               link=link)
    return award
