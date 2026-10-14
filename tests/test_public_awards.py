"""
The public award pages and the applicant's award list come from the real Award
tables: an award staff create shows up on the website, and applicants can
apply to it once it is open.
"""
from datetime import date

import pytest
from django.urls import reverse

from apps.awards.models import Award

from .factories import AwardFactory


@pytest.mark.django_db
def test_a_new_award_shows_on_the_public_pages(client):
    award = AwardFactory(name="Water Saving Award", sector="Sustainability", summary="Plants that save water.",
                         entry_fee=5000, closes_on=date(2027, 3, 31))
    listing = client.get(reverse("core:awards")).content.decode()
    assert "Water Saving Award" in listing and "Sustainability" in listing

    page = client.get(reverse("core:award_detail", args=[award.slug])).content.decode()
    assert "Plants that save water." in page and "₹5,000 entry fee" in page and "31 Mar 2027" in page
    assert "Approach" in page and "Results" in page                       # its own criteria
    assert reverse("entries:form", args=[award.slug]) in page              # Apply now goes to its form

    sector = client.get(reverse("core:awards"), {"sector": "Sustainability"}).content.decode()
    assert "Water Saving Award" in sector


@pytest.mark.django_db
def test_sample_awards_that_are_not_in_the_database_are_gone(client):
    AwardFactory(name="Water Saving Award")
    listing = client.get(reverse("core:awards")).content.decode()
    assert "Energy Efficiency Award" not in listing and "5S Workplace Competition" not in listing
    assert client.get(reverse("core:award_detail", args=["energy-efficiency"])).status_code == 404


@pytest.mark.django_db
def test_deleted_awards_are_not_shown(client):
    award = AwardFactory(name="Old Award")
    award.delete()
    assert "Old Award" not in client.get(reverse("core:awards")).content.decode()


@pytest.mark.django_db
def test_an_upcoming_award_is_listed_but_cannot_be_applied_to_yet(client, applicant_client):
    award = AwardFactory(name="Future Award", status=Award.Status.UPCOMING, opens_on=date(2027, 1, 15))
    page = client.get(reverse("core:award_detail", args=[award.slug])).content.decode()
    assert "Opens 15 Jan 2027" in page and "Apply now" not in page

    pick = applicant_client.get(reverse("entries:form")).content.decode()
    assert "Opening soon" in pick and "Future Award" in pick

    response = applicant_client.get(reverse("entries:form", args=[award.slug]), follow=True)
    assert "isn&#x27;t open for applications. It opens on 15 Jan 2027" in response.content.decode()


@pytest.mark.django_db
def test_applicant_can_start_an_application_for_a_new_open_award(applicant_client):
    award = AwardFactory(name="Water Saving Award")
    assert "Water Saving Award" in applicant_client.get(reverse("entries:form")).content.decode()
    applicant_client.post(reverse("entries:form", args=[award.slug]), {"action": "start", "title": "Our entry"})
    assert award.applications.count() == 1


@pytest.mark.django_db
def test_apply_now_sends_a_visitor_to_log_in_and_back(client):
    award = AwardFactory()
    response = client.get(reverse("entries:form", args=[award.slug]))
    assert response.status_code == 302 and "next=" in response["Location"] and award.slug in response["Location"]
