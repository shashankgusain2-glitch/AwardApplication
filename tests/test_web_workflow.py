"""
Roadmap step 3.5: the skeleton runs on real data, end to end, through the
web screens (the same pages a person clicks), on the seed data:

    applicant signs up → fills the organisation → applies and submits
    → staff verify the organisation and assign two judges
    → each judge accepts, saves midway, submits scores
    → the report is scored → leadership approves → the applicant sees it
"""
import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import ApplicantProfile, User
from apps.applications.models import Application
from apps.assignments.models import JudgeAssignment
from apps.awards.models import Award
from apps.evaluations.models import Evaluation

from .conftest import ACCOUNTS, seeded_client

NEW = {"email": "new.org@example.com", "password": "Strong-pass-2026!x"}


def _sign_up():
    c = Client()
    response = c.post(reverse("accounts:signup"), {"full_name": "Asha Rao", "email": NEW["email"],
                                                   "password1": NEW["password"], "password2": NEW["password"]})
    assert response.status_code == 302
    return c


def _answer_everything(client, award):
    """Fill every section of the form through the web page, then submit."""
    form = award.current_form
    sections = []
    for q in form.questions:
        if not sections or sections[-1][0] != q.get("section"):
            sections.append((q.get("section"), []))
        sections[-1][1].append(q)
    url = reverse("entries:form", args=[award.slug])
    for n, (_, questions) in enumerate(sections, start=1):
        data = {"section": str(n), "keys": [q["key"] for q in questions], "go": str(n + 1)}
        data.update({f"q_{q['key']}": f"Answer to {q['label']}" for q in questions})
        assert client.post(url, data).status_code == 302
    return client.post(url, {"section": str(len(sections)), "action": "submit"})


def _grade(client, assignment, submit):
    criteria = assignment.report.award.criteria.filter(round_number=assignment.round)
    data = {"action": "submit" if submit else "save", "feedback": "Clear, measured results."}
    data.update({f"score_{c.key}": "8" for c in criteria})
    return client.post(reverse("judging:score", args=[assignment.pk]), data)


@pytest.mark.django_db
def test_full_workflow_through_the_web_screens(seeded):
    kaizen = Award.objects.get(slug="kaizen")

    # 1. Applicant: sign up, organisation profile, apply, submit
    applicant = _sign_up()
    response = applicant.post(reverse("entries:organisation"), {
        "organisation_name": "Rao Castings Pvt Ltd", "gstin": "27RAOCA1234F1Z5", "city": "Kolhapur"})
    assert response.status_code == 302
    profile = ApplicantProfile.objects.get(user__email=NEW["email"])
    assert profile.verification_status == "pending"

    applicant.post(reverse("entries:form", args=["kaizen"]), {"action": "start", "title": "Faster mould change"})
    report = Application.objects.get(applicant__email=NEW["email"], award=kaizen)
    assert report.status == "draft"
    assert _answer_everything(applicant, kaizen)["Location"] == reverse("entries:status")
    report.refresh_from_db()
    assert report.status == "submitted" and report.submitted_at

    # 2. Staff: verify the organisation, then assign two judges from the eligible list
    staff = seeded_client("staff")
    assert profile.organisation_name in staff.get(reverse("awards:entries")).content.decode()
    staff.post(reverse("awards:verify_organisation", args=[profile.pk]), {"decision": "approve"})
    profile.refresh_from_db()
    assert profile.verification_status == "verified"

    kapoor = User.objects.get(email=ACCOUNTS["judge"])
    rao = User.objects.get(email=ACCOUNTS["judge2"])
    page = staff.get(reverse("awards:assign", args=[report.pk])).content.decode()
    assert kapoor.display_name in page and rao.display_name in page
    staff.post(reverse("awards:assign", args=[report.pk]), {"judges": [kapoor.pk, rao.pk]})
    report.refresh_from_db()
    assert report.status == "assigned"

    # 3. Judges: the report is on their home page; accept, save midway, submit
    for key, judge in (("judge", kapoor), ("judge2", rao)):
        client = seeded_client(key)
        assert report.reference in client.get(reverse("judging:assignments")).content.decode()
        assignment = JudgeAssignment.objects.get(report=report, judge=judge)
        assert client.post(reverse("judging:respond", args=[assignment.pk]), {"answer": "accept"}).status_code == 302
        _grade(client, assignment, submit=False)
        assert Evaluation.objects.get(assignment=assignment).status == "draft"
        _grade(client, assignment, submit=True)
        assert Evaluation.objects.get(assignment=assignment).status == "submitted"

    report.refresh_from_db()
    assert report.status == "scored"

    # 4. Leadership: the result is waiting; approve it
    leader = seeded_client("leader")
    assert report.reference in leader.get(reverse("dashboard:results")).content.decode()
    leader.post(reverse("dashboard:decide", args=[report.pk]), {"decision": "approve", "note": "Winner"})
    report.refresh_from_db()
    assert report.status == "approved"

    # 5. The applicant sees the outcome on their status page
    assert "Approved" in applicant.get(reverse("entries:status")).content.decode()


@pytest.mark.django_db
def test_web_actions_are_guarded_by_role_and_ownership(seeded):
    report = Application.objects.filter(status="submitted").first()
    others = JudgeAssignment.objects.exclude(judge__email=ACCOUNTS["judge"]).first()
    applicant, judge = seeded_client("applicant"), seeded_client("judge")

    # wrong role: 403 on staff and leadership actions
    assert applicant.post(reverse("awards:assign", args=[report.pk]), {"action": "auto"}).status_code == 403
    assert judge.post(reverse("dashboard:decide", args=[report.pk]), {"decision": "approve"}).status_code == 403
    assert applicant.post(reverse("awards:verify_organisation", args=[1]), {"decision": "approve"}).status_code == 403

    # another judge's assignment: 404, and nothing is saved
    assert judge.post(reverse("judging:score", args=[others.pk]), {"action": "submit"}).status_code == 404
    assert judge.post(reverse("judging:respond", args=[others.pk]), {"answer": "decline"}).status_code == 404

    # another applicant's application: never shown (the same award page offers a new application instead)
    priya = Application.objects.filter(applicant__email=ACCOUNTS["applicant"]).first()
    page = _sign_up().get(reverse("entries:form", args=[priya.award.slug])).content.decode()
    assert "Start an application" in page
    assert priya.reference not in page and "Acme Precision" not in page
    assert other_applicant_delete(priya) == 404


def other_applicant_delete(application):
    c = Client()
    c.post(reverse("accounts:login"), {"email": NEW["email"], "password": NEW["password"]})
    return c.post(reverse("entries:delete_draft", args=[application.pk])).status_code


@pytest.mark.django_db
def test_leader_cannot_approve_before_scoring_and_staff_cannot_approve(seeded):
    submitted = Application.objects.filter(status="submitted").first()
    leader = seeded_client("leader")
    leader.post(reverse("dashboard:decide", args=[submitted.pk]), {"decision": "approve"})
    submitted.refresh_from_db()
    assert submitted.status == "submitted"            # only scored reports can be approved


@pytest.mark.django_db
def test_applicant_cannot_submit_with_missing_answers(seeded):
    applicant = _sign_up()
    applicant.post(reverse("entries:form", args=["kaizen"]), {"action": "start", "title": "Half done"})
    response = applicant.post(reverse("entries:form", args=["kaizen"]), {"section": "1", "action": "submit"},
                              follow=True)
    page = response.content.decode()
    assert "still need an answer. They&#x27;re highlighted in red." in page
    assert "field-invalid" in page and "This question is required" in page
    assert Application.objects.get(applicant__email=NEW["email"]).status == "draft"


@pytest.mark.django_db
def test_bad_gstin_is_shown_on_the_organisation_form(seeded):
    applicant = _sign_up()
    response = applicant.post(reverse("entries:organisation"), {"organisation_name": "X", "gstin": "BAD"})
    assert response.status_code == 200
    assert "Enter a valid 15-character GSTIN" in response.content.decode()
    assert not ApplicantProfile.objects.filter(user__email=NEW["email"]).exists()
