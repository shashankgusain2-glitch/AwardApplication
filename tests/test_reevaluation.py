"""
Re-evaluation: once the result is out, an applicant may ask once (with a reason); every staff
member is notified; staff confirm or refuse. Confirmed → the first judges' work is kept as
history but stops counting, new judges (never the same ones, Rule 2 still applies) score it
again, and leadership decides again.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications import services as applications
from apps.assignments import services as assignments
from apps.assignments.models import ConflictOfInterest, JudgeAssignment
from apps.core.services import BusinessRuleError
from apps.dashboard.views import _with_scores
from apps.evaluations import services as evaluations
from apps.evaluations.models import Evaluation
from apps.notifications.models import Notification

from .conftest import login
from .factories import ApplicationFactory, AwardFactory, JudgeFactory, LeaderFactory, StaffFactory

A = JudgeAssignment.Status


def _score(report, judge, staff, value):
    assignment = assignments.assign(report, judge, by=staff)
    assignments.start_review(assignment, judge=judge)
    evaluations.save(assignment, judge=judge, scores={"approach": value, "results": value}, submit=True)
    return assignment


@pytest.fixture
def decided():
    """A report scored 3/10 by judges A and B, then rejected by leadership. Judges C and D are free."""
    award = AwardFactory(judges_per_report=2)
    staff, leader = StaffFactory(), LeaderFactory()
    judges = [JudgeFactory(awards=[award]) for _ in range(4)]
    report = ApplicationFactory(award=award)
    first = [_score(report, judges[0], staff, 3), _score(report, judges[1], staff, 3)]
    report.refresh_from_db()
    applications.change_status(report, by=leader, new_status="rejected")
    return {"report": report, "staff": staff, "leader": leader, "judges": judges, "first": first}


@pytest.mark.django_db
def test_applicant_asks_once_after_the_result_and_every_staff_member_is_told(decided):
    report, staff = decided["report"], decided["staff"]
    other_staff = StaffFactory()
    applications.request_reevaluation(report, by=report.applicant, reason="Our energy data was missed.")
    report.refresh_from_db()
    assert (report.reevaluation_status, report.reevaluation_previous_result) == ("requested", "rejected")
    assert report.status == "rejected"                                     # nothing changes until staff decide
    for person in (staff, other_staff):
        note = Notification.objects.get(user=person, kind=Notification.Kind.REQUEST)
        assert "Re-evaluation" in note.message and "Our energy data was missed." in note.message
    with pytest.raises(BusinessRuleError, match="already asked"):
        applications.request_reevaluation(report, by=report.applicant, reason="Again")


@pytest.mark.django_db
def test_cannot_ask_before_the_result_without_a_reason_or_for_someone_else(decided):
    scored = ApplicationFactory(award=decided["report"].award, status="scored")
    with pytest.raises(BusinessRuleError, match="once the result is out"):
        applications.request_reevaluation(scored, by=scored.applicant, reason="Too early")
    with pytest.raises(BusinessRuleError, match="Tell us why"):
        applications.request_reevaluation(decided["report"], by=decided["report"].applicant, reason="  ")
    with pytest.raises(BusinessRuleError, match="your own application"):
        applications.request_reevaluation(decided["report"], by=scored.applicant, reason="Not mine")


@pytest.mark.django_db
def test_refused_request_keeps_the_result_and_tells_the_applicant(decided):
    report = decided["report"]
    applications.request_reevaluation(report, by=report.applicant, reason="Please check again.")
    applications.decide_reevaluation(report, by=decided["staff"], allow=False, note="Scores were consistent.")
    report.refresh_from_db()
    assert (report.status, report.reevaluation_status) == ("rejected", "refused")
    message = Notification.objects.filter(user=report.applicant).latest("created_at").message
    assert "refused" in message and "Scores were consistent." in message
    with pytest.raises(BusinessRuleError, match="already asked"):
        applications.request_reevaluation(report, by=report.applicant, reason="One more try")


@pytest.mark.django_db
def test_staff_check_first_then_a_leader_confirms_and_nobody_skips_a_step(decided):
    report, staff, leader = decided["report"], decided["staff"], decided["leader"]
    with pytest.raises(BusinessRuleError, match="no re-evaluation request waiting"):
        applications.decide_reevaluation(report, by=staff, allow=True)
    applications.request_reevaluation(report, by=report.applicant, reason="Please check again.")
    for wrong in (report.applicant, leader):                         # only staff take the first step
        with pytest.raises(BusinessRuleError, match="staff check this request first"):
            applications.decide_reevaluation(report, by=wrong, allow=True)
    applications.decide_reevaluation(report, by=staff, allow=True, note="Looks fair.")
    report.refresh_from_db()
    assert report.status == "rejected"                               # nothing happens yet
    assert report.requests.get().status == "staff_approved"
    with pytest.raises(BusinessRuleError, match="needs a leader to confirm"):
        applications.decide_reevaluation(report, by=StaffFactory(), allow=True)
    applications.decide_reevaluation(report, by=leader, allow=True)
    report.refresh_from_db()
    assert report.status == "submitted" and report.reevaluation_status == "allowed"


@pytest.mark.django_db
def test_confirmed_reevaluation_uses_fresh_judges_and_keeps_the_old_scores_as_history(decided):
    report, staff, judges, first = decided["report"], decided["staff"], decided["judges"], decided["first"]
    applications.request_reevaluation(report, by=report.applicant, reason="Our energy data was missed.")
    applications.decide_reevaluation(report, by=staff, allow=True, note="New judges will look.")
    applications.decide_reevaluation(report, by=decided["leader"], allow=True)
    report.refresh_from_db()

    assert report.status == "submitted" and report.reevaluation_status == "allowed"
    assert {a.status for a in report.assignments.all()} == {A.SUPERSEDED}
    assert Evaluation.objects.filter(assignment__in=first, status="submitted").count() == 2   # history kept
    assert assignments.judges_still_needed(report) == 2
    assert set(assignments.eligible_judges(report)) == {judges[2], judges[3]}                # never A or B again
    assert evaluations.report_progress(report) == 0
    assert "New judges will score" in Notification.objects.filter(user=report.applicant).latest("created_at").message

    with pytest.raises(BusinessRuleError, match="re-evaluated by other judges"):
        evaluations.request_change(Evaluation.objects.get(assignment=first[0]), judge=judges[0], reason="Fix it")

    _score(report, judges[2], staff, 8)
    _score(report, judges[3], staff, 9)
    report.refresh_from_db()
    assert report.status == "scored" and evaluations.report_progress(report) == 100
    row = _with_scores(type(report).objects.filter(pk=report.pk)).get()
    assert (row.judged, float(row.average)) == (2, 8.5)                  # the old 3/10 scores don't count
    applications.change_status(report, by=decided["leader"], new_status="approved")
    report.refresh_from_db()
    assert report.status == "approved"
    assert not applications.can_request_reevaluation(report)            # once only


@pytest.mark.django_db
def test_conflicts_still_apply_to_the_new_judges(decided):
    report, judges = decided["report"], decided["judges"]
    ConflictOfInterest.objects.create(judge=judges[2], applicant_profile=report.applicant.applicant_profile,
                                      reason="Former employee")
    applications.request_reevaluation(report, by=report.applicant, reason="Please check again.")
    applications.decide_reevaluation(report, by=decided["staff"], allow=True)
    applications.decide_reevaluation(report, by=decided["leader"], allow=True)
    assert assignments.eligible_judges(report) == [judges[3]]


def _as(client, user):
    user.set_password("Test-pass-2026!")
    user.save()
    client.post(reverse("accounts:logout"))
    login(client, user.email)


@pytest.mark.django_db
def test_the_whole_flow_on_the_web_pages(decided, client):
    report = decided["report"]
    _as(client, report.applicant)
    assert "Ask for a re-evaluation" in client.get(reverse("entries:status")).content.decode()
    client.post(reverse("entries:request_reevaluation", args=[report.pk]), {"reason": "Our data was missed."})
    page = client.get(reverse("entries:status")).content.decode()
    assert "Re-evaluate the result · Waiting for staff" in page

    _as(client, decided["staff"])
    assert "1 request waiting for staff" in client.get(reverse("awards:staff_home")).content.decode()
    entries = client.get(reverse("awards:entries")).content.decode()
    assert "Requests waiting for staff (1)" in entries and "Our data was missed." in entries
    req = report.requests.get()
    url = reverse("core:decide_request", args=["applicant", req.pk])
    response = client.post(url, {"decision": "approve", "note": "Fair point."}, follow=True)
    assert "passed to leadership to confirm" in response.content.decode()
    report.refresh_from_db()
    assert report.status == "rejected"                                  # not yet: leadership must confirm

    _as(client, decided["leader"])
    assert "1 request waiting for your confirmation" in client.get(reverse("dashboard:overview")).content.decode()
    waiting = client.get(reverse("dashboard:requests")).content.decode()
    assert "Waiting for you (1)" in waiting and "Fair point." in waiting
    response = client.post(url, {"decision": "approve"}, follow=True)
    assert "confirmed: it takes effect now" in response.content.decode()
    report.refresh_from_db()
    assert report.status == "submitted"

    _as(client, report.applicant)
    assert "Re-evaluate the result · Approved" in client.get(reverse("entries:status")).content.decode()
    _as(client, decided["staff"])
    assert report.reference in client.get(reverse("awards:assign")).content.decode()


@pytest.mark.django_db
def test_the_api_endpoints(decided):
    report = decided["report"]
    applicant, staff, leader = APIClient(), APIClient(), APIClient()
    applicant.force_authenticate(report.applicant)
    staff.force_authenticate(decided["staff"])
    leader.force_authenticate(decided["leader"])
    url = f"/api/v1/applications/{report.pk}/"
    assert staff.post(url + "request-reevaluation/", {"reason": "x"}).status_code == 403   # applicants only
    response = applicant.post(url + "request-reevaluation/", {"reason": "Our data was missed."}, format="json")
    assert response.status_code == 200 and response.json()["data"]["reevaluation_status"] == "requested"
    assert applicant.post(url + "decide-reevaluation/", {"allow": True}).status_code == 403
    response = staff.post(url + "decide-reevaluation/", {"allow": True, "note": "OK"}, format="json")
    data = response.json()["data"]
    assert response.status_code == 200 and data["status"] == "rejected"
    assert data["requests"][0]["status"] == "staff_approved" and data["requests"][0]["staff_note"] == "OK"
    response = leader.post(url + "decide-reevaluation/", {"allow": True}, format="json")
    assert response.status_code == 200 and response.json()["data"]["status"] == "submitted"
    assert User.objects.filter(pk=report.applicant.pk).exists()
