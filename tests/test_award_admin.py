"""
R1 award administration: staff create and run any award without code.

Done when (FUTURE_GOALS_AND_DEPLOYMENT.md): "Staff create a third award end
to end in the browser". The first test does that through the web pages on
the seed data: create → form → criteria → panel → open → an applicant
applies → staff assign → judges score → a leader approves.
"""
import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.applications.models import Application
from apps.assignments.models import JudgeAssignment
from apps.awards import services as award_services
from apps.awards.models import Award

from .conftest import ACCOUNTS, seeded_client
from .factories import AwardFactory, JudgeFactory, StaffFactory

AWARD = {"name": "Energy Efficiency Award", "sector": "Energy", "summary": "Plants that cut energy use.",
         "opens_on": "2026-11-01", "closes_on": "2026-12-31", "applicant_type": "unit",
         "judges_per_report": "2", "entry_fee": "0", "round1": "desk", "round2": "site", "blind_judging": "on"}


def _criteria_post(rows):
    data = {"rows": str(len(rows))}
    for n, (round_number, label, weight) in enumerate(rows):
        data.update({f"c-{n}-round": str(round_number), f"c-{n}-key": "", f"c-{n}-label": label,
                     f"c-{n}-weight": str(weight)})
    return data


@pytest.mark.django_db
def test_staff_set_up_a_third_award_and_it_runs_end_to_end(seeded):
    staff = seeded_client("staff")

    # 1. Create
    response = staff.post(reverse("awards:award_new"), AWARD)
    award = Award.objects.get(name="Energy Efficiency Award")
    assert response["Location"] == reverse("awards:award_edit", args=[award.slug])
    assert award.status == "upcoming" and [r.kind for r in award.rounds.all()] == ["desk", "site"]
    assert award.blind_judging and award.applicant_type == "unit"

    # It can't open yet, and the page says why
    staff.post(reverse("awards:award_status", args=[award.slug]), {"status": "open"})
    award.refresh_from_db()
    assert award.status == "upcoming"
    page = staff.get(reverse("awards:award_edit", args=[award.slug])).content.decode()
    assert "Publish the application form" in page and "Choose at least one judge" in page

    # 2. Form  3. Criteria (both rounds = 100)  4. Panel
    staff.post(reverse("awards:form_edit", args=[award.slug]), {
        "rows": "2",
        "q-0-key": "", "q-0-label": "Plant name", "q-0-type": "text", "q-0-section": "About",
        "q-0-required": "on", "q-0-identifying": "on",
        "q-1-key": "", "q-1-label": "How much energy did you save?", "q-1-type": "textarea",
        "q-1-section": "Results", "q-1-required": "on"})
    staff.post(reverse("awards:award_criteria", args=[award.slug]),
               _criteria_post([(1, "Savings achieved", 60), (1, "Method", 40), (2, "On-site evidence", 100)]))
    kapoor, iyer = User.objects.get(email=ACCOUNTS["judge"]), User.objects.get(email="iyer@judges.example")
    staff.post(reverse("awards:award_panel", args=[award.slug]), {"judges": [kapoor.pk, iyer.pk]})

    # Open it
    staff.post(reverse("awards:award_status", args=[award.slug]), {"status": "open"})
    award.refresh_from_db()
    assert award.status == "open" and award.current_form.version == 1

    # An applicant sees it, applies and submits
    applicant = seeded_client("applicant")
    assert "Energy Efficiency Award" in applicant.get(reverse("entries:dashboard")).content.decode()
    url = reverse("entries:form", args=[award.slug])
    applicant.post(url, {"action": "start", "title": "Boiler upgrade"})
    keys = [q["key"] for q in award.current_form.questions]
    applicant.post(url, {"section": "1", "keys": [keys[0]], f"q_{keys[0]}": "Plant 4", "go": "2"})
    applicant.post(url, {"section": "2", "keys": [keys[1]], f"q_{keys[1]}": "18% less gas", "action": "submit"})
    report = Application.objects.get(award=award)
    assert report.status == "submitted"

    # Staff assign; the panel's two judges are offered (Rao isn't on the panel)
    page = staff.get(reverse("awards:assign", args=[report.pk])).content.decode()
    assert kapoor.display_name in page and "Prof. N. Rao" not in page
    staff.post(reverse("awards:assign", args=[report.pk]), {"action": "auto"})
    assert JudgeAssignment.objects.filter(report=report).count() == 2

    # Judges grade with the new criteria; the blind desk round hides the plant name
    for key, judge in (("judge", kapoor), (None, iyer)):
        client = seeded_client(key) if key else Client()
        if not key:
            client.force_login(judge)
            session = client.session
            session["role"] = "judge"
            session.save()
        assignment = JudgeAssignment.objects.get(report=report, judge=judge)
        page = client.get(reverse("judging:score", args=[assignment.pk])).content.decode()
        assert "Plant 4" not in page and "Savings achieved" in page
        client.post(reverse("judging:score", args=[assignment.pk]),
                    {"action": "submit", "score_savings-achieved": "8", "score_method": "7"})
    report.refresh_from_db()
    assert report.status == "scored"

    # A leader approves; the overview lists the new award
    leader = seeded_client("leader")
    leader.post(reverse("dashboard:decide", args=[report.pk]), {"decision": "approve"})
    report.refresh_from_db()
    assert report.status == "approved"
    assert "Energy Efficiency Award" in leader.get(reverse("dashboard:overview")).content.decode()


# --- Rules checked by the services ------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("changes,message", [
    ({"name": ""}, "Give the award a name"),
    ({"judges_per_report": 9}, "from 1 to 7"),
    ({"rounds": []}, "at least one judging round"),
    ({"rounds": ["site"], "blind_judging": True}, "needs a desk review round"),
    ({"rounds": ["teleport"]}, "desk review, site visit or live presentation"),
    ({"rounds": ["desk", "site", "live"]}, "at most 2 rounds"),
    ({"entry_fee": -5}, "can't be negative"),
])
def test_bad_award_settings_are_refused(changes, message):
    from datetime import date
    fields = {"name": "X Award", "rounds": ["desk"], "judges_per_report": 2, "blind_judging": False,
              "entry_fee": 0, "opens_on": date(2026, 11, 1), "closes_on": date(2026, 12, 1), **changes}
    with pytest.raises(Exception, match=message):
        award_services.create_award(by=StaffFactory(), **fields)


@pytest.mark.django_db
def test_closing_before_opening_is_refused(staff_client):
    response = staff_client.post(reverse("awards:award_new"), {**AWARD, "closes_on": "2026-10-01"}, follow=True)
    assert "be before the opening date" in response.content.decode()
    assert not Award.objects.filter(name=AWARD["name"]).exists()


@pytest.mark.django_db
def test_award_form_offers_at_most_two_rounds(staff_client):
    page = staff_client.get(reverse("awards:award_new")).content.decode()
    assert 'name="round1"' in page and 'name="round2"' in page and 'name="round3"' not in page
    response = staff_client.post(reverse("awards:award_new"), {**AWARD, "round3": "live"}, follow=True)
    assert "at most 2 rounds" in response.content.decode()
    assert not Award.objects.filter(name=AWARD["name"]).exists()


@pytest.mark.django_db
def test_names_get_unique_web_addresses():
    staff = StaffFactory()
    first = award_services.create_award(by=staff, name="Quality Award", rounds=["desk"])
    second = award_services.create_award(by=staff, name="Quality Award", rounds=["desk"])
    assert (first.slug, second.slug) == ("quality-award", "quality-award-2")


@pytest.mark.django_db
def test_criteria_must_add_up_to_100_per_round():
    award = AwardFactory()
    with pytest.raises(Exception, match="add up to 90"):
        award_services.save_criteria(award, by=StaffFactory(), rows=[{"round_number": 1, "label": "A", "weight": 90}])


@pytest.mark.django_db
def test_criteria_lock_once_judges_have_scored(world_scored):
    with pytest.raises(Exception, match="already scored"):
        award_services.save_criteria(world_scored, by=StaffFactory(),
                                     rows=[{"round_number": 1, "label": "New", "weight": 100}])


@pytest.fixture
def world_scored(db):
    from apps.applications.models import Application  # noqa: F401
    from apps.assignments import services as assignments
    from apps.evaluations import services as evaluations

    from .factories import ApplicationFactory
    award = AwardFactory()
    judge = JudgeFactory(awards=[award])
    assignment = assignments.assign(ApplicationFactory(award=award), judge, by=StaffFactory())
    evaluations.save(assignment, judge=judge, scores={"approach": 6})
    return award


@pytest.mark.django_db
def test_a_round_with_judges_cannot_be_removed(world_scored):
    from apps.assignments import services as assignments

    from .factories import ApplicationFactory
    award = world_scored
    award_services.set_rounds(award, ["desk", "site"])
    award.criteria.create(round_number=2, key="on_site", label="On site", weight=100)
    report = ApplicationFactory(award=award, status="in_review")
    judge = JudgeFactory(awards=[award])
    assignments.assign(report, judge, by=StaffFactory(), round=2)
    with pytest.raises(Exception, match="Round 2 already has judges"):
        award_services.update_award(award, by=StaffFactory(), rounds=["desk"], name=award.name,
                                    judges_per_report=2, blind_judging=False, entry_fee=0)


@pytest.mark.django_db
def test_panel_controls_who_can_be_assigned():
    from .factories import ApplicationFactory
    award = AwardFactory()
    on, off = JudgeFactory(awards=[award]), JudgeFactory(awards=[award])
    award_services.set_panel(award, by=StaffFactory(), judges=[on])
    from apps.assignments.services import eligible_judges
    assert eligible_judges(ApplicationFactory(award=award)) == [on]
    assert off.judge_profile.awards.count() == 0


# --- Who can use these screens ---------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("name", ["awards:award_list", "awards:award_new"])
def test_award_admin_is_staff_only(client_for, name):
    for url_name in ("entries:dashboard", "judging:assignments", "dashboard:overview"):
        assert client_for(url_name).get(reverse(name)).status_code == 403
    assert client_for("awards:staff_home").get(reverse(name)).status_code == 200


@pytest.mark.django_db
def test_award_pages_open_for_the_seeded_awards(seeded):
    staff = seeded_client("staff")
    for award in Award.objects.all():
        for name in ("awards:award_edit", "awards:award_criteria", "awards:award_panel"):
            assert staff.get(reverse(name, args=[award.slug])).status_code == 200, (award.slug, name)
    page = staff.get(reverse("awards:award_list")).content.decode()
    assert "Business Excellence Award" in page and "Kaizen Competition" in page
