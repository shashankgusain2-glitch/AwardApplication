"""
The public website's award pages, built from the real Award tables.

Every award staff create (Awards → New award) shows here with its own rounds,
criteria, dates and fee. The two seeded demo awards also keep their extra
website text (icon, eligibility, FAQs) from apps/core/demo_data.py; any
other award gets sensible generic text.
"""
from datetime import timedelta

from django.utils import timezone

from apps.awards.models import Award

from . import demo_data as d

CLOSING_SOON_DAYS = 14
DEFAULT_ICON = "🏅"


def _date(day):
    return f"{day.day} {day:%b %Y}" if day else ""


def _status_label(award, today):
    closing = award.closes_on and award.closes_on - today <= timedelta(CLOSING_SOON_DAYS)
    if award.status == Award.Status.OPEN and closing:
        return "Closing soon"
    return award.get_status_display()


def _deadline(award):
    if award.status == Award.Status.UPCOMING and award.opens_on:
        return f"Opens {_date(award.opens_on)}"
    if award.status in (Award.Status.JUDGING, Award.Status.RESULTS, Award.Status.CLOSED):
        return "Closed"
    return _date(award.closes_on) or "To be announced"


def _form_length(award):
    form = award.current_form
    if not form or not form.questions:
        return "Application form"
    sections = len({q.get("section") or "Questions" for q in form.questions})
    count = len(form.questions)
    return f"{count} question{'s' if count != 1 else ''} in {sections} section{'s' if sections != 1 else ''}"


def to_card(award, today=None):
    """One Award as the dict the public templates use."""
    today = today or timezone.localdate()
    extra = next((a for a in d.AWARDS if a["slug"] == award.slug and a["slug"] in d.BUILT_AWARDS), {})
    kinds = [r.kind for r in award.rounds.all()]
    blind = award.blind_judging and d.blind_possible(kinds)
    criteria = list(award.criteria.all())
    return {
        "slug": award.slug,
        "name": award.name,
        "sector": award.sector or "General",
        "summary": award.summary,
        "icon": extra.get("icon", DEFAULT_ICON),
        "status": _status_label(award, today),
        "can_apply": award.status == Award.Status.OPEN,
        "deadline": _deadline(award),
        "opens_on": award.opens_on,
        "closes_on": award.closes_on,
        "round_types": kinds,
        "rounds": len(kinds),
        "blind": blind,
        "rounds_info": [{"number": n, "type": k, "label": d.ROUND_TYPES.get(k, k),
                         "is_blind": blind and k in d.BLIND_POSSIBLE} for n, k in enumerate(kinds, start=1)],
        "judges_per_entry": award.judges_per_report,
        "applicant_type": award.get_applicant_type_display(),
        "fee_amount": award.entry_fee,
        "fee": f"₹{award.entry_fee:,} entry fee" if award.entry_fee else "No entry fee",
        "form_length": extra.get("form_length") or _form_length(award),
        "eligibility": extra.get("eligibility", []),
        "criteria": [{"name": c.label, "weight": c.weight} for c in criteria if c.round_number == 1],
        "round2_criteria": [{"name": c.label, "weight": c.weight} for c in criteria if c.round_number == 2],
        "extra_faqs": extra.get("extra_faqs", []),
    }


def _queryset():
    return Award.objects.prefetch_related("rounds", "criteria", "form_versions").order_by("name")


def all_awards():
    """Every award (not deleted): open ones first, then upcoming, then the rest; by name within each."""
    order = {Award.Status.OPEN: 0, Award.Status.UPCOMING: 1, Award.Status.JUDGING: 2,
             Award.Status.RESULTS: 3, Award.Status.CLOSED: 4}
    today = timezone.localdate()
    awards = sorted(_queryset(), key=lambda a: (order.get(a.status, 9), a.name.lower()))
    return [to_card(a, today) for a in awards]


def get_award(slug):
    award = _queryset().filter(slug=slug).first()
    return to_card(award) if award else None


def sectors(awards):
    return sorted({a["sector"] for a in awards})


def details(award):
    """Content for an award's public detail page: the shared text, plus real dates."""
    out = d.award_details(award)
    out["criteria"] = award["criteria"]          # the real ones only, never the generic sample list
    out["timeline"] = [
        {"date": _date(award["opens_on"]) or "To be announced", "label": "Applications open"},
        {"date": _date(award["closes_on"]) or "To be announced", "label": "Applications close"},
    ] + [{"date": "After the deadline" if r["number"] == 1 else "For shortlisted entries",
          "label": f"Round {r['number']}: {r['label'].lower()}"} for r in award["rounds_info"]] + [
        {"date": "After judging", "label": "Winners announced"}]
    return out
