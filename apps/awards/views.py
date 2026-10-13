"""Programme staff screens (sample data until the awards models are built)."""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.permissions import role_required
from apps.awards import services as award_services
from apps.core import demo_data as d
from apps.core import overview
from apps.core.services import BusinessRuleError

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
def form_builder(request, slug="business-excellence"):
    award = d.get_award(slug, request)
    if award is None or slug not in d.BUILT_AWARDS:
        raise Http404("Award not found")
    return render(request, "awards/form_builder.html", {
        "role": ROLE,
        "award": award,
        "awards": d.built_awards(request),
    })


@role_required("staff")
def entries(request):
    return render(request, "awards/entries.html", {
        "role": ROLE,
        "entries": d.STAFF_ENTRIES,
    })


@role_required("staff")
def duplicates(request):
    return render(request, "awards/duplicates.html", {
        "role": ROLE,
        "duplicates": d.DUPLICATES,
    })


@role_required("staff")
def assign(request):
    award = d.get_award("business-excellence", request)
    return render(request, "awards/assign.html", {
        "role": ROLE,
        "entry": d.STAFF_ENTRIES[3],
        "award": award,
        "judges": d.JUDGE_POOL,
        "needed": award["judges_per_entry"],
    })
