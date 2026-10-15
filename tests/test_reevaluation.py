"""
Re-evaluation: once the result is out, an applicant may ask once (with a reason), from the
results board or their status page. The award's manager decides in one step (a leader, if
the award has no manager). Approved → the first judges' work is kept as history but stops
counting, the manager chooses new judges (never the same ones; Rule 2 still applies),
leadership decides the result again, and the results board shows the new result.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.applications import services as applications
from apps.assignments import services as assignments
from apps.assignments.models import ConflictOfInterest, JudgeAssignment
from apps.core.services import BusinessRuleError
from apps.dashboard.views import _with_scores
from apps.evaluations import services as evaluations
from apps.evaluations.models import Evaluation
from apps.notifications.models import Notification

from .conftest import login
from .factories import (
    ApplicationFactory,
    AwardFactory,
    JudgeFactory,
    LeaderFactory,
    ManagerFactory,
    StaffFactory,
)

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
    manager = ManagerFactory(awards=[award])
    staff, leader = StaffFactory(), LeaderFactory()
    judges = [JudgeFactory(awards=[award]) for _ in range(4)]
    report = ApplicationFactory(award=award)
    first = [_score(report, judges[0], staff, 3), _score(report, judges[1], staff, 3)]
    report.refresh_from_db()
    applications.change_status(report, by=leader, new_status="rejected")
    return {"report": report, "award": award, "manager": manager, "staff": staff, "leader": leader,
            "judges": judges, "first": first}


@pytest.mark.django_db
def test_applicant_asks_once_and_the_award_manager_is_told(decided):
    report = decided["report"]
    applications.request_reevaluation(report, by=report.applicant, reason="Our energy data was missed.")
    report.refresh_from_db()
    assert (report.reevaluation_status, report.reevaluation_previous_result) == ("requested", "rejected")
    assert report.status == "rejected"                                     # nothing changes until the manager decides
    note = Notification.objects.get(user=decided["manager"], kind=Notification.Kind.REQUEST)
    assert "Re-evaluation" in note.message and "Our energy data was missed." in note.message
    assert note.link == reverse("awards:reevaluations")
    assert Notification.objects.filter(user=decided["staff"], message__contains="the award manager decides").exists()
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
    applications.decide_reevaluation(report, by=decided["manager"], allow=False, note="Scores were consistent.")
    report.refresh_from_db()
    assert (report.status, report.reevaluation_status) == ("rejected", "refused")
    message = Notification.objects.filter(user=report.applicant).latest("created_at").message
    assert "refused" in message and "Scores were consistent." in message
    with pytest.raises(BusinessRuleError, match="already asked"):
        applications.request_reevaluation(report, by=report.applicant, reason="One more try")


@pytest.mark.django_db
def test_only_the_award_manager_decides_in_one_step(decided):
    report, manager = decided["report"], decided["manager"]
    with pytest.raises(BusinessRuleError, match="no re-evaluation request waiting"):
        applications.decide_reevaluation(report, by=manager, allow=True)
    applications.request_reevaluation(report, by=report.applicant, reason="Please check again.")
    other_manager = ManagerFactory(awards=[AwardFactory()])
    for wrong in (report.applicant, decided["staff"], decided["leader"], other_manager):
        with pytest.raises(BusinessRuleError):
            applications.decide_reevaluation(report, by=wrong, allow=True)
    applications.decide_reevaluation(report, by=manager, allow=True, note="New judges will look.")
    report.refresh_from_db()
    assert report.status == "accepted" and report.reevaluation_status == "allowed"
    assert report.requests.get().decided_by == manager


@pytest.mark.django_db
def test_a_leader_decides_when_the_award_has_no_manager(decided):
    award, report = decided["award"], decided["report"]
    award.manager = None
    award.save()
    report.refresh_from_db()
    applications.request_reevaluation(report, by=report.applicant, reason="Please check again.")
    assert Notification.objects.filter(user=decided["leader"], kind=Notification.Kind.REQUEST).exists()
    applications.decide_reevaluation(report, by=decided["leader"], allow=True)
    report.refresh_from_db()
    assert report.status == "accepted"


@pytest.mark.django_db
def test_approved_reevaluation_uses_fresh_judges_and_keeps_the_old_scores_as_history(decided):
    report, staff, judges, first = decided["report"], decided["staff"], decided["judges"], decided["first"]
    applications.request_reevaluation(report, by=report.applicant, reason="Our energy data was missed.")
    applications.decide_reevaluation(report, by=decided["manager"], allow=True)
    report.refresh_from_db()

    assert report.status == "accepted" and report.reevaluation_status == "allowed"
    assert {a.status for a in report.assignments.all()} == {A.SUPERSEDED}
    assert Evaluation.objects.filter(assignment__in=first, status="submitted").count() == 2   # history kept
    assert assignments.judges_still_needed(report) == 2
    assert set(assignments.eligible_judges(report)) == {judges[2], judges[3]}                # never A or B again
    assert evaluations.report_progress(report) == 0
    assert "New judges will score" in Notification.objects.filter(user=report.applicant).latest("created_at").message

    with pytest.raises(BusinessRuleError, match="re-evaluated by other judges"):
        evaluations.request_change(Evaluation.objects.get(assignment=first[0]), judge=judges[0], reason="Fix it")

    _score(report, judges[2], decided["manager"], 8)
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
    applications.decide_reevaluation(report, by=decided["manager"], allow=True)
    assert assignments.eligible_judges(report) == [judges[3]]


def _as(client, user):
    user.set_password("Test-pass-2026!")
    user.save()
    client.post(reverse("accounts:logout"))
    login(client, user.email, "Test-pass-2026!")


@pytest.mark.django_db
def test_the_whole_flow_on_the_web_pages(decided, client):
    report, award, manager, judges = decided["report"], decided["award"], decided["manager"], decided["judges"]
    board = reverse("core:results") + f"?award={award.slug}"

    # The applicant sees their result on the board and asks from there
    _as(client, report.applicant)
    page = client.get(board).content.decode()
    assert "Not successful" in page and "Ask for re-evaluation" in page
    response = client.post(reverse("entries:request_reevaluation", args=[report.pk]),
                           {"reason": "Our data was missed.", "next": board}, follow=True)
    assert "sent to the award manager" in response.content.decode()
    assert "waiting for the award manager" in response.content.decode()

    # Staff see it but can't decide; the manager approves and goes straight to choosing judges
    _as(client, decided["staff"])
    page = client.get(reverse("awards:reevaluations")).content.decode()
    assert "Our data was missed." in page and f"the award manager, {manager.display_name}" in page
    assert "Approve and choose new judges" not in page
    _as(client, manager)
    page = client.get(reverse("awards:reevaluations")).content.decode()
    assert "Waiting for a decision (1)" in page and "Approve and choose new judges" in page
    req = report.requests.get()
    response = client.post(reverse("awards:reevaluation_decide", args=[req.pk]), {"decision": "approve"})
    assert response["Location"] == reverse("awards:assign", args=[report.pk])
    page = client.get(response["Location"]).content.decode()
    offered = [f'name="judges" value="{j.pk}"' in page for j in judges]
    assert offered == [False, False, True, True]                      # fresh judges only
    client.post(reverse("awards:assign", args=[report.pk]), {"judges": [judges[2].pk, judges[3].pk]})
    report.refresh_from_db()
    assert report.status == "assigned"

    # While it is re-judged the board lists it as being re-evaluated
    _as(client, report.applicant)
    page = client.get(board).content.decode()
    assert "Being re-evaluated" in page and "was not successful" in page

    # New judges score it, leadership decides again: the board shows the new result
    for judge, value in ((judges[2], 8), (judges[3], 9)):
        assignment = report.assignments.get(judge=judge)
        assignments.start_review(assignment, judge=judge)
        evaluations.save(assignment, judge=judge, scores={"approach": value, "results": value}, submit=True)
    report.refresh_from_db()
    _as(client, decided["leader"])
    assert "Re-evaluation: new judges" in client.get(reverse("dashboard:results")).content.decode()
    client.post(reverse("dashboard:decide", args=[report.pk]), {"decision": "approve"})
    _as(client, report.applicant)
    page = client.get(board).content.decode()
    assert "Successful" in page and "8.50" in page and "Re-evaluated · was not successful" in page
    assert "Ask for re-evaluation" not in page                           # once only


@pytest.mark.django_db
def test_the_api_endpoints(decided):
    report = decided["report"]
    applicant, staff, manager = APIClient(), APIClient(), APIClient()
    applicant.force_authenticate(report.applicant)
    staff.force_authenticate(decided["staff"])
    manager.force_authenticate(decided["manager"])
    url = f"/api/v1/applications/{report.pk}/"
    assert staff.post(url + "request-reevaluation/", {"reason": "x"}).status_code == 403   # applicants only
    response = applicant.post(url + "request-reevaluation/", {"reason": "Our data was missed."}, format="json")
    assert response.status_code == 200 and response.json()["data"]["reevaluation_status"] == "requested"
    assert applicant.post(url + "decide-reevaluation/", {"allow": True}).status_code == 403
    assert staff.post(url + "decide-reevaluation/", {"allow": True}, format="json").status_code == 400
    response = manager.post(url + "decide-reevaluation/", {"allow": True, "note": "OK"}, format="json")
    data = response.json()["data"]
    assert response.status_code == 200 and data["status"] == "accepted"
    assert data["requests"][0]["status"] == "approved" and data["requests"][0]["decision_note"] == "OK"
