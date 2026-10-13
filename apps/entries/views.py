"""Applicant screens (sample data until the entries models are built)."""
from django.http import Http404
from django.shortcuts import render

from apps.core import demo_data as d

ROLE = "applicant"

# The applicant's entry for each award (sample)
MY_ENTRY = {"business-excellence": "A-0042", "kaizen": "K-0007"}


def dashboard(request):
    open_awards = [a for a in d.all_awards(request) if a["status"] in ("Open", "Closing soon")]
    return render(request, "entries/dashboard.html", {
        "role": ROLE,
        "applications": d.MY_APPLICATIONS,
        "open_awards": open_awards,
        "organisation": d.APPLICANT_ORG,
    })


def organisation(request):
    return render(request, "entries/organisation.html", {
        "role": ROLE,
        "organisation": d.APPLICANT_ORG,
    })


def application_form(request, slug="business-excellence"):
    award = d.get_award(slug, request)
    if award is None or slug not in MY_ENTRY:
        raise Http404("No application for this award")
    entry_id = MY_ENTRY[slug]
    sections = d.entry_answers(entry_id)

    for s in sections:
        s["done"] = sum(1 for q in s["questions"] if q["value"])
        s["total"] = len(s["questions"])
    done = sum(s["done"] for s in sections)
    total = sum(s["total"] for s in sections)

    try:
        index = max(0, min(int(request.GET.get("section", 1)) - 1, len(sections) - 1))
    except ValueError:
        index = 0

    return render(request, "entries/application_form.html", {
        "role": ROLE,
        "award": award,
        "entry_id": entry_id,
        "submitted": entry_id == "K-0007",
        "sections": sections,
        "current": sections[index],
        "current_index": index + 1,
        "has_previous": index > 0,
        "has_next": index < len(sections) - 1,
        "progress": round(done * 100 / total),
        "other_awards": [d.get_award(s, request) for s in MY_ENTRY if s != slug],
    })


def application_status(request):
    return render(request, "entries/application_status.html", {
        "role": ROLE,
        "application": d.MY_APPLICATIONS[1],
        "timeline": d.APPLICATION_TIMELINE,
    })
