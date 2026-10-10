"""Checks the app starts and every screen loads."""
import pytest
from django.urls import reverse

from apps.core import demo_data

PAGES = [
    "core:home",
    "core:about",
    "core:awards",
    "core:login",
    "entries:dashboard",
    "entries:organisation",
    "entries:form",
    "entries:status",
    "judging:assignments",
    "judging:score",
    "awards:staff_home",
    "awards:settings",
    "awards:form_builder",
    "awards:entries",
    "awards:duplicates",
    "awards:assign",
    "dashboard:overview",
    "dashboard:review",
    "dashboard:results",
]


@pytest.mark.django_db
@pytest.mark.parametrize("name", PAGES)
def test_page_loads(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("slug", [a["slug"] for a in demo_data.AWARDS])
def test_award_detail_loads(client, slug):
    response = client.get(reverse("core:award_detail", args=[slug]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_unknown_award_returns_404(client):
    response = client.get(reverse("core:award_detail", args=["no-such-award"]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_sector_filter_shows_only_that_sector(client):
    response = client.get(reverse("core:awards"), {"sector": "Shop-floor"})
    assert b"Kaizen Competition" in response.content
    assert b"Energy Efficiency Award" not in response.content
