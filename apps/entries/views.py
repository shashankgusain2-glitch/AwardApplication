"""Applicant screens (sample data until the entries models are built)."""
from django.shortcuts import render

from apps.core import demo_data as d

ROLE = "applicant"


def dashboard(request):
    open_awards = [a for a in d.AWARDS if a["status"] in ("Open", "Closing soon")]
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


def application_form(request):
    sections = d.FORM_SECTIONS
    done = sum(s["done"] for s in sections)
    total = sum(s["total"] for s in sections)
    return render(request, "entries/application_form.html", {
        "role": ROLE,
        "award": d.get_award("business-excellence"),
        "sections": sections,
        "current": sections[1],
        "progress": round(done * 100 / total),
    })


def application_status(request):
    return render(request, "entries/application_status.html", {
        "role": ROLE,
        "application": d.MY_APPLICATIONS[1],
        "timeline": d.APPLICATION_TIMELINE,
    })
