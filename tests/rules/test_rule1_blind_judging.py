"""
Rule 1: if an award uses blind judging, a judge cannot see who applied.

These run on the real demo data (seed_data): Business Excellence is blind
(desk review, then a live presentation); Kaizen is not (desk review, then a
site visit). A logged-in staff member changes the award's own page; a different,
logged-in judge sees the effect on the real scoring page.
"""
import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.applications.models import Application
from apps.assignments import services as assignment_services
from apps.assignments.models import JudgeAssignment

from ..conftest import ACCOUNTS, save_award, seeded_client

ORG_NAME = "Acme Precision"   # Priya's organisation


def _assignment(award, applicant="priya@acme.example", round=1):
    return JudgeAssignment.objects.get(judge__email=ACCOUNTS["judge"], report__applicant__email=applicant,
                                       report__award__slug=award, round=round)


def _score_page(client, assignment):
    response = client.get(reverse("judging:score", args=[assignment.pk]))
    assert response.status_code == 200
    return response.content.decode()




def _round_two(award, applicant):
    """Put judge Kapoor on Round 2 of this applicant's report (staff assign it)."""
    report = Application.objects.get(award__slug=award, applicant__email=applicant)
    report.status = Application.Status.IN_REVIEW
    report.save(update_fields=["status"])
    staff = User.objects.get(email=ACCOUNTS["staff"])
    return assignment_services.assign(report, User.objects.get(email=ACCOUNTS["judge"]), by=staff, round=2)


@pytest.mark.django_db
def test_blind_award_hides_identifying_answers_title_and_applicant(seeded):
    page = _score_page(seeded_client("judge"), _assignment("business-excellence"))
    assert ORG_NAME not in page                                  # name, title, applicant
    assert "Hidden for blind judging" in page
    assert "Sample answer to" in page                            # the rest of the entry is shown


@pytest.mark.django_db
def test_blind_award_hides_uploaded_file_names(seeded):
    page = _score_page(seeded_client("judge"), _assignment("business-excellence"))
    assert "acme-precision" not in page                          # seed file names start with the organisation
    assert "name hidden for blind judging" in page


@pytest.mark.django_db
def test_non_blind_award_shows_organisation_to_judge(seeded):
    page = _score_page(seeded_client("judge"), _assignment("kaizen"))
    assert ORG_NAME in page
    assert "acme-precision" in page                              # file names are shown too


@pytest.mark.django_db
def test_blind_hiding_also_applies_to_the_api(seeded):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(User.objects.get(email=ACCOUNTS["judge"]))
    row = client.get(f"/api/v1/assignments/{_assignment('business-excellence').pk}/").json()["data"]
    assert ORG_NAME not in str(row)
    assert row["report"]["applicant"] is None and row["report"]["title"] is None


@pytest.mark.django_db
def test_manager_turning_blind_on_hides_names_without_code_change(seeded):
    save_award(seeded_client("manager"), "kaizen", blind_judging=True)
    page = _score_page(seeded_client("judge"), _assignment("kaizen"))
    assert ORG_NAME not in page
    assert "Kaizen Team" not in page                             # the team name is identifying too


@pytest.mark.django_db
def test_manager_turning_blind_off_shows_names(seeded):
    save_award(seeded_client("manager"), "business-excellence", blind_judging=False)
    page = _score_page(seeded_client("judge"), _assignment("business-excellence"))
    assert ORG_NAME in page


@pytest.mark.django_db
def test_live_round_two_is_not_blind(seeded):
    # Business Excellence is blind, but Round 2 is a live presentation: the jury meets the team.
    assignment = _round_two("business-excellence", "vikram@vertexpharma.example")
    page = _score_page(seeded_client("judge"), assignment)
    assert "Vertex Pharma Labs" in page
    assert "Live presentation: not blind" in page


@pytest.mark.django_db
def test_site_visit_round_is_not_blind_even_if_award_is_blind(seeded):
    manager, judge = seeded_client("manager"), seeded_client("judge")
    save_award(manager, "kaizen", blind_judging=True)             # blind applies to Round 1 desk review only
    round_two = _round_two("kaizen", "ganesh@shriganesh.example")
    assert ORG_NAME not in _score_page(judge, _assignment("kaizen"))               # Round 1: hidden
    assert "Shri Ganesh Polymers" in _score_page(judge, round_two)                  # Round 2 site visit: shown
