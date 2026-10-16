"""
The brief: one system, two awards that work differently, and the award's team sets the
differences without changing code, on the award's own page (Details and rounds).

Settings are saved by a logged-in staff member into the Award tables, so the public site
and judges (other users) see them too.
"""
import pytest
from django.urls import reverse

from apps.core import demo_data

from .conftest import save_award


@pytest.fixture(autouse=True)
def demo_awards(db):
    """
    The two demo awards exist before staff log in, so the test staff member is on both
    (see conftest). Returns their starting settings, to check that refused changes saved nothing.
    """
    from apps.awards.services import get_or_create_from_demo
    for slug in demo_data.BUILT_AWARDS:
        get_or_create_from_demo(slug)
    return demo_data.award_overrides()


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
def test_the_award_page_changes_the_public_page_for_everyone(staff_client, client):
    save_award(staff_client, "kaizen", round2="live", judges_per_report="5", entry_fee="2000")
    page = client.get(reverse("core:award_detail", args=["kaizen"])).content.decode()   # a visitor, not staff
    assert "Round 2: live presentation" in page
    assert "Round 2: site visit" not in page
    assert "5 jury members read and score" in page
    assert "₹2,000 entry fee" in page


@pytest.mark.django_db
def test_settings_for_one_award_do_not_change_the_other(staff_client, client):
    save_award(staff_client, "kaizen", blind_judging=True, judges_per_report="4")
    be_page = client.get(reverse("core:award_detail", args=["business-excellence"])).content.decode()
    assert "3 jury members read and score" in be_page


@pytest.mark.django_db
@pytest.mark.parametrize("field,value", [
    ("round1", "teleport"),
    ("round2", "teleport"),
    ("judges_per_report", "0"),
    ("judges_per_report", "abc"),
    ("applicant_type", "robot"),
    ("entry_fee", "-5"),
    ("closes_on", "yesterday"),
])
def test_invalid_settings_are_rejected(staff_client, demo_awards, field, value):
    response = save_award(staff_client, "kaizen", **{field: value})
    assert b"Saved Kaizen" not in response.content
    assert demo_data.award_overrides() == demo_awards


@pytest.mark.django_db
def test_settings_are_saved_in_the_award_table_and_audited(staff_client):
    from apps.audit.models import AuditLog
    from apps.awards.models import Award
    save_award(staff_client, "kaizen", judges_per_report="3", round2="live")
    award = Award.objects.get(slug="kaizen")
    assert award.judges_per_report == 3
    assert [r.kind for r in award.rounds.all()] == ["desk", "live"]
    entry = AuditLog.objects.filter(entity="award", entity_id=str(award.pk), action="update").latest("timestamp")
    assert entry.user.email == "staff@awards.example"


def test_there_is_no_separate_award_settings_page():
    from django.urls import NoReverseMatch
    with pytest.raises(NoReverseMatch):
        reverse("awards:settings")


# --- Blind judging only where it can work ----------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("round1,round2", [("site", ""), ("live", ""), ("site", "live"), ("site", "site")])
def test_blind_rejected_when_every_round_is_in_person(staff_client, demo_awards, round1, round2):
    response = save_award(staff_client, "kaizen", round1=round1, round2=round2, blind_judging=True)
    assert b"Blind judging needs a desk review round" in response.content
    assert demo_data.award_overrides() == demo_awards


@pytest.mark.django_db
def test_in_person_award_without_blind_is_accepted(staff_client):
    response = save_award(staff_client, "kaizen", round1="site", round2="", blind_judging=False)
    assert b"Saved Kaizen Competition" in response.content
    kaizen = demo_data.get_award("kaizen")
    assert kaizen["round_types"] == ["site"]
    assert kaizen["blind_possible"] is False


@pytest.mark.django_db
def test_blind_never_on_for_in_person_only_award_even_if_data_says_so():
    # Safety net in get_award: bad stored data can't switch blind on.
    award = demo_data.get_award("5s-workplace")
    assert award["round_types"] == ["site"]
    assert award["blind"] is False


@pytest.mark.django_db
def test_a_round_with_judges_assigned_cannot_be_removed(seeded):
    from apps.accounts.models import User
    from apps.applications.models import Application
    from apps.assignments import services as assignment_services

    from .conftest import ACCOUNTS, seeded_client
    report = Application.objects.get(award__slug="kaizen", applicant__email="ganesh@shriganesh.example")
    judge = User.objects.get(email=ACCOUNTS["judge"])
    round_two = assignment_services.assign(report, judge, by=User.objects.get(email=ACCOUNTS["staff"]), round=2)
    kapoor = seeded_client("judge")
    assert kapoor.get(reverse("judging:score", args=[round_two.pk])).status_code == 200
    response = save_award(seeded_client("staff"), "kaizen", round2="")
    assert b"Round 2 already has judges assigned" in response.content
    assert kapoor.get(reverse("judging:score", args=[round_two.pk])).status_code == 200   # nothing removed
