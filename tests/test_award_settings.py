"""
The brief: one system, two awards that work differently, and staff set
the differences without changing code.

Settings are saved by a logged-in staff member and stored in the database,
so the public site and judges (other users) see them too.
"""
import pytest
from django.urls import reverse

from apps.core import demo_data


def _post(staff_client, **fields):
    data = {
        "slug": "kaizen", "round1_type": "desk", "round2_type": "site", "judges_per_entry": "2",
        "applicant_type": "Team", "fee_amount": "0", "deadline": "15 Dec 2026",
    }
    data.update(fields)
    return staff_client.post(reverse("awards:settings"), data, follow=True)


def test_the_two_awards_differ_by_default():
    be = demo_data.BUSINESS_EXCELLENCE
    kz = demo_data.KAIZEN
    assert (be["round_types"], be["blind"], be["judges_per_entry"]) == (["desk", "live"], True, 3)
    assert (kz["round_types"], kz["blind"], kz["judges_per_entry"]) == (["desk", "site"], False, 2)
    assert be["criteria"] != kz["criteria"]
    assert be["eligibility"] != kz["eligibility"]
    assert be["form_sections"] != kz["form_sections"]


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["business-excellence", "kaizen"])
def test_criteria_weights_add_up_to_100(slug):
    award = demo_data.get_award(slug)
    assert sum(c["weight"] for c in award["criteria"]) == 100
    if award["round2_criteria"]:
        assert sum(c["weight"] for c in award["round2_criteria"]) == 100


@pytest.mark.django_db
def test_staff_settings_change_the_public_page_for_everyone(staff_client, client):
    _post(staff_client, round2_type="live", judges_per_entry="5", fee_amount="2000")
    page = client.get(reverse("core:award_detail", args=["kaizen"])).content.decode()   # a visitor, not staff
    assert "Round 2: live presentation" in page
    assert "Round 2: site visit" not in page
    assert "5 jury members read and score" in page
    assert "₹2,000 entry fee" in page


@pytest.mark.django_db
def test_settings_for_one_award_do_not_change_the_other(staff_client, client):
    from apps.awards.services import get_or_create_from_demo
    get_or_create_from_demo("business-excellence")
    _post(staff_client, blind="on", judges_per_entry="4")
    be_page = client.get(reverse("core:award_detail", args=["business-excellence"])).content.decode()
    assert "3 jury members read and score" in be_page


@pytest.mark.django_db
@pytest.mark.parametrize("field,value", [
    ("round1_type", "teleport"),
    ("round2_type", "teleport"),
    ("judges_per_entry", "0"),
    ("judges_per_entry", "abc"),
    ("applicant_type", "Robot"),
    ("fee_amount", "-5"),
    ("deadline", ""),
])
def test_invalid_settings_are_rejected(staff_client, field, value):
    response = _post(staff_client, **{field: value})
    assert b"Saved" not in response.content
    assert demo_data.award_overrides() == {}


@pytest.mark.django_db
def test_reset_returns_award_to_defaults(staff_client, client):
    _post(staff_client, judges_per_entry="6")
    _post(staff_client, reset="1")
    page = client.get(reverse("core:award_detail", args=["kaizen"])).content.decode()
    assert "2 jury members read and score" in page


@pytest.mark.django_db
def test_unknown_award_cannot_be_saved(staff_client):
    response = staff_client.post(reverse("awards:settings"), {"slug": "no-such-award"})
    assert response.status_code == 404


@pytest.mark.django_db
def test_settings_are_saved_in_the_award_table_and_audited(staff_client):
    from apps.audit.models import AuditLog
    from apps.awards.models import Award
    _post(staff_client, judges_per_entry="3", round2_type="live")
    award = Award.objects.get(slug="kaizen")
    assert award.judges_per_report == 3
    assert [r.kind for r in award.rounds.all()] == ["desk", "live"]
    entry = AuditLog.objects.get(entity="award", entity_id=str(award.pk))
    assert entry.user.email == "staff@awards.example"


# --- Blind judging only where it can work ----------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("round1,round2", [("site", "none"), ("live", "none"), ("site", "live"), ("site", "site")])
def test_blind_rejected_when_every_round_is_in_person(staff_client, round1, round2):
    response = _post(staff_client, round1_type=round1, round2_type=round2, blind="on")
    assert b"Blind judging isn&#x27;t possible" in response.content
    assert demo_data.award_overrides() == {}


@pytest.mark.django_db
def test_in_person_award_without_blind_is_accepted(staff_client):
    response = _post(staff_client, round1_type="site", round2_type="none")
    assert b"Saved Kaizen Competition" in response.content
    kaizen = demo_data.get_award("kaizen")
    assert kaizen["round_types"] == ["site"]
    assert kaizen["blind_possible"] is False


@pytest.mark.django_db
def test_settings_page_disables_blind_switch_for_in_person_award(staff_client):
    _post(staff_client, round1_type="site", round2_type="none")
    page = staff_client.get(reverse("awards:settings")).content.decode()
    kaizen_form = page.split('value="kaizen"')[1]
    blind_input = kaizen_form.split('name="blind"')[1].split(">")[0]
    assert "disabled" in blind_input


@pytest.mark.django_db
def test_blind_never_on_for_in_person_only_award_even_if_data_says_so():
    # Safety net in get_award: bad stored data can't switch blind on.
    award = demo_data.get_award("5s-workplace")
    assert award["round_types"] == ["site"]
    assert award["blind"] is False


@pytest.mark.django_db
def test_removing_round_two_closes_the_round_two_scoring_page(seeded):
    from apps.accounts.models import User
    from apps.applications.models import Application
    from apps.assignments import services as assignment_services

    from .conftest import ACCOUNTS, seeded_client
    report = Application.objects.get(award__slug="kaizen", applicant__email="ganesh@shriganesh.example")
    judge = User.objects.get(email=ACCOUNTS["judge"])
    round_two = assignment_services.assign(report, judge, by=User.objects.get(email=ACCOUNTS["staff"]), round=2)
    kapoor = seeded_client("judge")
    assert kapoor.get(reverse("judging:score", args=[round_two.pk])).status_code == 200
    _post(seeded_client("staff"), round2_type="none")
    assert kapoor.get(reverse("judging:score", args=[round_two.pk])).status_code == 404
