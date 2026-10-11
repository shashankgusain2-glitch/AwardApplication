"""
Rule 1: if an award uses blind judging, a judge cannot see who applied.

These run against the demo screens, where hiding happens in
demo_data.answers_for_judge before the page is built. They will move to
the real models when the judging tables exist.
"""
import pytest
from django.urls import reverse

BLIND_ENTRY = "A-0042"      # Business Excellence: blind by default
OPEN_ENTRY = "K-0007"       # Kaizen: not blind by default
ORG_NAME = b"Acme Precision"  # both entries come from this organisation


def _score_page(client, entry):
    return client.get(reverse("judging:score", args=[entry]))


def _save_settings(client, slug, **changes):
    settings = {
        "slug": slug, "rounds": "1", "judges_per_entry": "2",
        "applicant_type": "Team", "fee_amount": "0", "deadline": "15 Dec 2026",
    }
    settings.update(changes)
    return client.post(reverse("awards:settings"), settings)


@pytest.mark.django_db
def test_blind_award_hides_identifying_answers_from_judge(client):
    response = _score_page(client, BLIND_ENTRY)
    assert response.status_code == 200
    assert ORG_NAME not in response.content
    assert b"Chakan" not in response.content  # location is also identifying


@pytest.mark.django_db
def test_blind_award_hides_uploaded_file_names(client):
    # The file name "acme-strategy-2026.pdf" would reveal the company.
    response = _score_page(client, BLIND_ENTRY)
    assert b"acme-strategy" not in response.content
    assert b"name hidden" in response.content


@pytest.mark.django_db
def test_non_blind_award_shows_organisation_to_judge(client):
    response = _score_page(client, OPEN_ENTRY)
    assert ORG_NAME in response.content


@pytest.mark.django_db
def test_assignment_list_hides_applicant_only_for_blind_awards(client):
    content = client.get(reverse("judging:assignments")).content.decode()
    blind_card = content.split("Entry A-0042")[1].split("Entry ")[0]
    open_card = content.split("Entry K-0007")[1].split("Entry ")[0]
    assert "Acme" not in blind_card
    assert "Acme" in open_card


@pytest.mark.django_db
def test_staff_turning_blind_on_hides_names_without_code_change(client):
    _save_settings(client, "kaizen", blind="on")
    response = _score_page(client, OPEN_ENTRY)
    assert ORG_NAME not in response.content
    assert b"Line 4 Changeover Crew" not in response.content  # team name is identifying too


@pytest.mark.django_db
def test_staff_turning_blind_off_shows_names(client):
    _save_settings(client, "business-excellence", rounds="2", judges_per_entry="3",
                   applicant_type="Organisation", deadline="30 Nov 2026")  # no "blind" = off
    response = _score_page(client, BLIND_ENTRY)
    assert ORG_NAME in response.content


@pytest.mark.skip(reason="Planned: needs the real judging API")
def test_blind_award_hides_organisation_in_judge_api_response():
    ...


@pytest.mark.skip(reason="Planned: needs Round 2 assignments")
def test_live_round_two_is_not_blind():
    ...
