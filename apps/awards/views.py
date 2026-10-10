"""Programme staff screens (sample data until the awards models are built)."""
from django.shortcuts import render

from apps.core import demo_data as d

ROLE = "staff"


def _two_awards():
    return [d.get_award("business-excellence"), d.get_award("kaizen")]


def staff_home(request):
    return render(request, "awards/staff_home.html", {
        "role": ROLE,
        "awards": _two_awards(),
        "entries": d.STAFF_ENTRIES,
        "duplicates": d.DUPLICATES,
    })


def settings(request):
    return render(request, "awards/settings.html", {
        "role": ROLE,
        "awards": _two_awards(),
    })


def form_builder(request):
    return render(request, "awards/form_builder.html", {
        "role": ROLE,
        "award": d.get_award("business-excellence"),
        "questions": d.FORM_QUESTIONS,
        "versions": d.FORM_VERSIONS,
    })


def entries(request):
    return render(request, "awards/entries.html", {
        "role": ROLE,
        "entries": d.STAFF_ENTRIES,
    })


def duplicates(request):
    return render(request, "awards/duplicates.html", {
        "role": ROLE,
        "duplicates": d.DUPLICATES,
    })


def assign(request):
    return render(request, "awards/assign.html", {
        "role": ROLE,
        "entry": d.STAFF_ENTRIES[3],
        "judges": d.JUDGE_POOL,
    })
