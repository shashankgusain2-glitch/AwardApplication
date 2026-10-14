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


@transaction.atomic
def save_screen_settings(slug, settings, by):
    """Save what staff chose on the Award settings screen into the Award tables."""
    award = get_or_create_from_demo(slug)
    before = {"blind_judging": award.blind_judging, "judges_per_report": award.judges_per_report,
              "rounds": [r.kind for r in award.rounds.all()]}
    award.blind_judging = settings["blind"]
    award.judges_per_report = settings["judges_per_entry"]
    award.applicant_type = APPLICANT_TYPE_FROM_LABEL.get(settings["applicant_type"], award.applicant_type)
    award.entry_fee = settings["fee_amount"]
    award.closes_on = parse_display_date(settings["deadline"])
    if award.opens_on and award.closes_on < award.opens_on:
        raise BusinessRuleError("The closing date can't be before the opening date.")
    award.save()
    set_rounds(award, settings["round_types"])
    record(by, "update", award, changes={"before": before, "after": {
        "blind_judging": award.blind_judging, "judges_per_report": award.judges_per_report,
        "rounds": settings["round_types"]}})
    return award


@transaction.atomic
def reset_screen_settings(slug, by):
    """Put the award's settings back to their defaults (its forms, criteria and reports are kept)."""
    from apps.core import demo_data
    base = next(a for a in demo_data.AWARDS if a["slug"] == slug)
    return save_screen_settings(slug, {
        "blind": base["blind"], "judges_per_entry": base["judges_per_entry"],
        "applicant_type": base["applicant_type"], "fee_amount": base.get("fee_amount", 0),
        "deadline": base["deadline"], "round_types": base["round_types"],
    }, by)


def screen_overrides():
    """Settings saved in the Award tables, in the shape the portal screens expect."""
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
    rows: [{key, label, type, section, required, identifying, remove}] in order. Rows marked
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
                          "required": bool(row.get("required")), "identifying": bool(row.get("identifying"))})
    return questions


def check_criteria_weights(award, round_number=1):
    total = sum(Criterion.objects.filter(award=award, round_number=round_number).values_list("weight", flat=True))
    if total != 100:
        raise BusinessRuleError(f"Round {round_number} weights add up to {total}, not 100.")
