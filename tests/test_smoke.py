"""Checks the app starts and every screen loads."""
import pytest
from django.urls import reverse

from apps.core import demo_data

PAGES = [
    "core:home",
    "core:about",
    "core:awards",
    "accounts:login",
    "accounts:signup",
    "accounts:password_reset",
    "entries:dashboard",
    "entries:organisation",
    "entries:form",
    "entries:status",
    "judging:assignments",
    "awards:staff_home",
    "awards:form_builder",
    "awards:entries",
    "awards:duplicates",
    "awards:assign",
    "dashboard:overview",
    "dashboard:results",
]


@pytest.mark.django_db
@pytest.mark.parametrize("name", PAGES)
def test_page_loads(client_for, name):
    client = client_for(name)
    response = client.get(reverse(name))
    assert response.status_code == 200


@pytest.mark.django_db
def test_award_detail_loads_for_every_award(client, seeded):
    from apps.awards.models import Award
    for slug in Award.objects.values_list("slug", flat=True):
        assert client.get(reverse("core:award_detail", args=[slug])).status_code == 200


# --- The skeleton on real data (roadmap step 3.5) ------------------------------------

@pytest.mark.django_db
def test_every_screen_opens_for_every_role_on_the_seed_data(seeded):
    """Each role's menu pages and every detail page they can reach, on the real demo data."""
    from apps.applications.models import Application
    from apps.assignments.models import JudgeAssignment
    from apps.awards.models import Award

    from .conftest import ACCOUNTS, seeded_client

    for key, role in (("applicant", "applicant"), ("staff", "staff"), ("judge", "judge"), ("leader", "leader")):
        client = seeded_client(key)
        for _, url_name in demo_data.PORTAL_NAV[role]:
            assert client.get(reverse(url_name), follow=True).status_code == 200, f"{role}: {url_name}"

    applicant = seeded_client("applicant")
    for app in Application.objects.filter(applicant__email=ACCOUNTS["applicant"]):
        for section in ("1", "2", "3", "99", "abc"):
            url = reverse("entries:form", args=[app.award.slug])
            assert applicant.get(url, {"section": section}).status_code == 200

    judge = seeded_client("judge")
    for assignment in JudgeAssignment.objects.filter(judge__email=ACCOUNTS["judge"]):
        assert judge.get(reverse("judging:score", args=[assignment.pk])).status_code == 200

    staff = seeded_client("staff")
    for app in Application.objects.exclude(status="draft"):
        assert staff.get(reverse("awards:assign", args=[app.pk])).status_code == 200
    for award in Award.objects.all():
        assert staff.get(reverse("awards:form_builder", args=[award.slug]), {"version": "1"}).status_code == 200
    assert staff.get(reverse("awards:entries"), {"status": "submitted", "q": "Polymers"}).status_code == 200



@pytest.mark.django_db
def test_screens_show_the_seed_data_not_samples(seeded):
    from .conftest import seeded_client
    entries = seeded_client("staff").get(reverse("awards:entries")).content.decode()
    assert "Shri Ganesh Polymers Ltd" in entries and "Northstar Auto Components" in entries
    results = seeded_client("leader").get(reverse("dashboard:results")).content.decode()
    assert "Kaizen Competition" in results and "Business Excellence Award" in results
    status = seeded_client("applicant").get(reverse("entries:status")).content.decode()
    assert "Business Excellence Award" in status and "Kaizen Competition" in status


@pytest.mark.django_db
def test_new_applicant_screens_have_empty_states(client_for):
    applicant = client_for("entries:dashboard")
    for name in ("entries:dashboard", "entries:organisation", "entries:form", "entries:status"):
        assert applicant.get(reverse(name)).status_code == 200


@pytest.mark.django_db
def test_unknown_assignment_and_award_return_404(seeded):
    from .conftest import seeded_client
    assert seeded_client("judge").get(reverse("judging:score", args=[999999])).status_code == 404
    assert seeded_client("applicant").get(reverse("entries:form", args=["no-such-award"])).status_code == 404


@pytest.mark.django_db
def test_kaizen_shows_its_own_criteria(client, seeded):
    page = client.get(reverse("core:award_detail", args=["kaizen"])).content.decode()
    assert "Root cause found" in page
    assert "Leadership and strategy" not in page


@pytest.mark.django_db
def test_unknown_award_returns_404(client):
    response = client.get(reverse("core:award_detail", args=["no-such-award"]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_sector_filter_shows_only_that_sector(client, seeded):
    response = client.get(reverse("core:awards"), {"sector": "Shop-floor"})
    assert b"Kaizen Competition" in response.content
    assert b"Energy Efficiency Award" not in response.content
