"""
Applicant screens (sample data until the entries models are built).

Every page is for logged-in applicants only, and shows only their own data:
the sample applications belong to the demo applicant; anyone else who signs
up starts with an empty dashboard and blank forms.
"""
from django.http import Http404
from django.shortcuts import render

from apps.accounts.permissions import role_required
from apps.core import demo_data as d

ROLE = "applicant"

# The demo applicant's entry for each award (sample)
MY_ENTRY = {"business-excellence": "A-0042", "kaizen": "K-0007"}


def _own(request):
    """True if the sample applications belong to the logged-in applicant."""
    return d.owns_sample_data(request.user)


@role_required("applicant")
def dashboard(request):
    open_awards = [a for a in d.all_awards(request) if a["status"] in ("Open", "Closing soon")]
    return render(request, "entries/dashboard.html", {
        "role": ROLE,
        "applications": d.MY_APPLICATIONS if _own(request) else [],
        "open_awards": open_awards,
        "organisation": d.APPLICANT_ORG if _own(request) else {},
    })


@role_required("applicant")
def organisation(request):
    return render(request, "entries/organisation.html", {
        "role": ROLE,
        "organisation": d.APPLICANT_ORG if _own(request) else {"contact_email": request.user.email},
    })


@role_required("applicant")
def application_form(request, slug="business-excellence"):
    award = d.get_award(slug, request)
    if award is None or slug not in MY_ENTRY:
        raise Http404("No application for this award")

    if _own(request):
        entry_id = MY_ENTRY[slug]
        sections = d.entry_answers(entry_id)
    else:
        entry_id = None                      # a new applicant starts with a blank form
        sections = d.blank_answers(slug)

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


@role_required("applicant")
def application_status(request):
    return render(request, "entries/application_status.html", {
        "role": ROLE,
        "application": d.MY_APPLICATIONS[1] if _own(request) else None,
        "timeline": d.APPLICATION_TIMELINE,
    })
