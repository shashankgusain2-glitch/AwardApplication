"""
Rule 1: if an award uses blind judging, a judge cannot see who applied.

These run against the demo screens, where hiding happens in
demo_data.answers_for_judge before the page is built. A logged-in staff
member changes settings; a different, logged-in judge sees the effect.
"""
import pytest
from django.urls import reverse

BLIND_ENTRY = "A-0042"      # Business Excellence: blind by default
OPEN_ENTRY = "K-0007"       # Kaizen: not blind by default
ORG_NAME = b"Acme Precision"  # both entries come from this organisation


def _score_page(judge_client, entry):
    return judge_client.get(reverse("judging:score", args=[entry]))


def _save_settings(staff_client, slug, **changes):
    settings = {
        "slug": slug, "round1_type": "desk", "round2_type": "site", "judges_per_entry": "2",
        "applicant_type": "Team", "fee_amount": "0", "deadline": "15 Dec 2026",
    }
    settings.update(changes)
    return staff_client.post(reverse("awards:settings"), settings)


@pytest.mark.django_db
def test_blind_award_hides_identifying_answers_from_judge(judge_client):
    response = _score_page(judge_client, BLIND_ENTRY)
    assert response.status_code == 200
    assert ORG_NAME not in response.content
    assert b"Chakan" not in response.content  # location is also identifying


@pytest.mark.django_db
def test_blind_award_hides_uploaded_file_names(judge_client):
    # The file name "acme-strategy-2026.pdf" would reveal the company.
    response = _score_page(judge_client, BLIND_ENTRY)
    assert b"acme-strategy" not in response.content
    assert b"name hidden" in response.content


@pytest.mark.django_db
def test_non_blind_award_shows_organisation_to_judge(judge_client):
    response = _score_page(judge_client, OPEN_ENTRY)
    assert ORG_NAME in response.content


@pytest.mark.django_db
def test_staff_turning_blind_on_hides_names_without_code_change(staff_client, judge_client):
    _save_settings(staff_client, "kaizen", blind="on")
    response = _score_page(judge_client, OPEN_ENTRY)
    assert ORG_NAME not in response.content
    assert b"Line 4 Changeover Crew" not in response.content  # team name is identifying too


@pytest.mark.django_db
def test_staff_turning_blind_off_shows_names(staff_client, judge_client):
    _save_settings(staff_client, "business-excellence", round2_type="live", judges_per_entry="3",
                   applicant_type="Organisation", deadline="30 Nov 2026")  # no "blind" = off
    response = _score_page(judge_client, BLIND_ENTRY)
    assert ORG_NAME in response.content


@pytest.mark.skip(reason="Planned: needs the real judging API")
def test_blind_award_hides_organisation_in_judge_api_response():
    ...


@pytest.mark.django_db
def test_live_round_two_is_not_blind(judge_client):
    # Business Excellence is blind, but Round 2 is a live presentation.
    response = _score_page(judge_client, "A-0029")
    assert b"Vertex Pharma Labs" in response.content
    assert b"Live presentation: not blind" in response.content


@pytest.mark.django_db
def test_site_visit_round_is_not_blind_even_if_award_is_blind(staff_client, judge_client):
    _save_settings(staff_client, "kaizen", blind="on")  # blind applies to Round 1 desk review only
    assert ORG_NAME not in _score_page(judge_client, OPEN_ENTRY).content          # Round 1: hidden
    assert b"Deccan Forge" in _score_page(judge_client, "K-0003").content          # Round 2 site visit: shown
