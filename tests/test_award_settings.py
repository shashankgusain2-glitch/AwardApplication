"""
The brief: one system, two awards that work differently, and staff set
the differences without changing code.
"""
import pytest
from django.urls import reverse

from apps.core import demo_data


def _post(client, **fields):
    data = {
        "slug": "kaizen", "rounds": "1", "judges_per_entry": "2",
        "applicant_type": "Team", "fee_amount": "0", "deadline": "15 Dec 2026",
    }
    data.update(fields)
    return client.post(reverse("awards:settings"), data, follow=True)


def test_the_two_awards_differ_by_default():
    be = demo_data.get_award("business-excellence")
    kz = demo_data.get_award("kaizen")
    assert (be["rounds"], be["blind"], be["judges_per_entry"]) == (2, True, 3)
    assert (kz["rounds"], kz["blind"], kz["judges_per_entry"]) == (1, False, 2)
    assert be["criteria"] != kz["criteria"]
    assert be["eligibility"] != kz["eligibility"]
    assert be["form_sections"] != kz["form_sections"]


@pytest.mark.parametrize("slug", ["business-excellence", "kaizen"])
def test_criteria_weights_add_up_to_100(slug):
    award = demo_data.get_award(slug)
    assert sum(c["weight"] for c in award["criteria"]) == 100
    if award["round2_criteria"]:
        assert sum(c["weight"] for c in award["round2_criteria"]) == 100


@pytest.mark.django_db
def test_saving_settings_changes_public_award_page(client):
    _post(client, rounds="2", judges_per_entry="5", fee_amount="2000")
    page = client.get(reverse("core:award_detail", args=["kaizen"])).content.decode()
    assert "Round 2: live presentation" in page
    assert "5 jury members score" in page
    assert "₹2,000 entry fee" in page


@pytest.mark.django_db
def test_settings_for_one_award_do_not_change_the_other(client):
    _post(client, blind="on", judges_per_entry="4")
    be_page = client.get(reverse("core:award_detail", args=["business-excellence"])).content.decode()
    assert "3 jury members score" in be_page


@pytest.mark.django_db
@pytest.mark.parametrize("field,value", [
    ("rounds", "3"),
    ("judges_per_entry", "0"),
    ("judges_per_entry", "abc"),
    ("applicant_type", "Robot"),
    ("fee_amount", "-5"),
    ("deadline", ""),
])
def test_invalid_settings_are_rejected(client, field, value):
    response = _post(client, **{field: value})
    assert b"Saved" not in response.content
    assert demo_data.award_overrides(response.wsgi_request) == {}


@pytest.mark.django_db
def test_reset_returns_award_to_defaults(client):
    _post(client, judges_per_entry="6")
    _post(client, reset="1")
    page = client.get(reverse("core:award_detail", args=["kaizen"])).content.decode()
    assert "2 jury members score" in page


@pytest.mark.django_db
def test_unknown_award_cannot_be_saved(client):
    response = client.post(reverse("awards:settings"), {"slug": "no-such-award"})
    assert response.status_code == 404
