"""
Roadmap 3.7, validation and edge cases: "bad situations show a clear message
instead of crashing". Every web form gets junk (letters where numbers go,
missing fields, unknown ids) and must answer with a page or a redirect,
never a server error (500).
"""
import pytest
from django.urls import reverse

from apps.applications.models import Application
from apps.assignments.models import JudgeAssignment
from apps.awards.models import Award

from .conftest import ACCOUNTS, seeded_client

JUNK = {"section": "abc", "go": "x", "keys": ["nope"], "action": "???", "decision": "maybe", "answer": "perhaps",
        "rows": "lots", "judges": ["abc", "-1", "99999"], "status": "flying", "title": "x" * 500,
        "judges_per_report": "many", "entry_fee": "free", "opens_on": "31/31/2026", "closes_on": "tomorrow",
        "round1": "teleport", "established_year": "nineteen", "gstin": "BAD", "note": "x" * 5000,
        "c-0-round": "abc", "c-0-label": "A", "c-0-weight": "heavy", "q-0-label": "Q", "q-0-type": "video",
        "score_approach": "ten", "reason": ""}


def _no_crash(client, method, url, data=None):
    response = getattr(client, method)(url, data or {})
    assert response.status_code < 500, f"{method.upper()} {url} crashed ({response.status_code})"
    return response


@pytest.mark.django_db
def test_staff_forms_survive_junk(seeded):
    staff = seeded_client("staff")
    award = Award.objects.first()
    report = Application.objects.exclude(status="draft").first()
    for name, args in [("awards:award_new", []), ("awards:award_edit", [award.slug]),
                       ("awards:award_status", [award.slug]), ("awards:award_criteria", [award.slug]),
                       ("awards:award_panel", [award.slug]), ("awards:form_edit", [award.slug]),
                       ("awards:assign", [report.pk]), ("awards:verify_organisation", [1]),
                       ("core:decide_request", ["applicant", 99999]), ("awards:reject_report", [report.pk]),
                       ("core:decide_request", ["score", 99999]), ("awards:settings", [])]:
        _no_crash(staff, "post", reverse(name, args=args), JUNK)
    for name, query in [("awards:entries", {"status": "x", "award": "x", "q": "%' OR 1=1 --"}),
                        ("awards:form_builder", {"version": "abc"})]:
        _no_crash(staff, "get", reverse(name, args=[award.slug] if name == "awards:form_builder" else []), query)


@pytest.mark.django_db
def test_applicant_forms_survive_junk(seeded):
    applicant = seeded_client("applicant")
    app = Application.objects.filter(applicant__email=ACCOUNTS["applicant"]).first()
    _no_crash(applicant, "post", reverse("entries:organisation"), JUNK)
    _no_crash(applicant, "post", reverse("entries:form", args=[app.award.slug]), JUNK)
    _no_crash(applicant, "get", reverse("entries:form", args=[app.award.slug]), {"section": "-5"})
    _no_crash(applicant, "post", reverse("entries:delete_draft", args=[99999]))


@pytest.mark.django_db
def test_judge_forms_survive_junk(seeded):
    judge = seeded_client("judge")
    mine = JudgeAssignment.objects.filter(judge__email=ACCOUNTS["judge"]).first()
    _no_crash(judge, "post", reverse("judging:score", args=[mine.pk]), JUNK)
    _no_crash(judge, "post", reverse("judging:score", args=[mine.pk]), {**JUNK, "action": "submit"})
    _no_crash(judge, "post", reverse("judging:score", args=[mine.pk]), {**JUNK, "action": "change"})
    _no_crash(judge, "post", reverse("judging:respond", args=[mine.pk]), JUNK)


@pytest.mark.django_db
def test_leader_forms_survive_junk(seeded):
    leader = seeded_client("leader")
    report = Application.objects.exclude(status="draft").first()
    _no_crash(leader, "post", reverse("dashboard:decide", args=[report.pk]), JUNK)
    _no_crash(leader, "get", reverse("dashboard:review"), {"status": "x", "award": "<script>"})


@pytest.mark.django_db
def test_bad_values_explain_themselves(seeded):
    """Not just no crash: the person is told what is wrong."""
    from apps.accounts.models import User
    from apps.awards.services import create_award
    staff = seeded_client("staff")
    award = create_award(by=User.objects.get(email=ACCOUNTS["staff"]), name="Fresh Award", rounds=["desk"])
    page = staff.post(reverse("awards:award_criteria", args=[award.slug]),
                      {"rows": "1", "c-0-round": "1", "c-0-label": "A", "c-0-weight": "heavy"}, follow=True)
    assert "must be a whole number" in page.content.decode()
    page = staff.post(reverse("awards:award_new"), {"name": "X", "round1": "desk", "judges_per_report": "many",
                                                    "opens_on": "31/31/2026"}, follow=True).content.decode()
    assert "Judges per report must be a whole number" in page and "use a date like" in page
    page = staff.post(reverse("awards:assign", args=[Application.objects.exclude(status="draft").first().pk]),
                      {"judges": ["abc"]}, follow=True).content.decode()
    assert "Choose at least one judge" in page
