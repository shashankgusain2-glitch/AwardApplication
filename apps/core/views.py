from django.http import Http404
from django.shortcuts import render

from . import demo_data as d


def home(request):
    featured = [a for a in d.AWARDS if a["status"] in ("Open", "Closing soon")][:3]
    return render(request, "core/home.html", {
        "stats": d.STATS,
        "featured": featured,
        "steps": d.HOW_IT_WORKS,
        "promises": d.TRUST_PROMISES,
        "winners": d.PAST_WINNERS,
        "sectors": d.SECTORS,
    })


def about(request):
    return render(request, "core/about.html", {
        "stats": d.STATS,
        "promises": d.TRUST_PROMISES,
    })


def award_list(request):
    sector = request.GET.get("sector", "")
    awards = [a for a in d.AWARDS if not sector or a["sector"] == sector]
    return render(request, "core/awards.html", {
        "awards": awards,
        "sectors": d.SECTORS,
        "active_sector": sector,
    })


def award_detail(request, slug):
    award = d.get_award(slug)
    if award is None:
        raise Http404("Award not found")
    return render(request, "core/award_detail.html", {
        "award": award,
        "details": d.award_details(award),
    })


def login(request):
    return render(request, "core/login.html", {"roles": d.ROLE_LABELS})
