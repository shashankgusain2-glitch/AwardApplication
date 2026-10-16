"""
An award's result (apps/awards/results.py): the award manager decides each scored entry, sends
the award's result, and leadership approves it as a whole (or sends it back). Only then is it
published: the results board, the applicants told, re-evaluation possible.
"""
import pytest
from django.urls import reverse

from apps.applications import services as applications
from apps.assignments import services as assignments
from apps.awards import results
from apps.core.services import BusinessRuleError
from apps.evaluations import services as evaluations
from apps.notifications.models import Notification

from .conftest import login
from .factories import ApplicationFactory, AwardFactory, JudgeFactory, LeaderFactory, ManagerFactory, StaffFactory


def _scored(award, staff, judge, value):
    report = ApplicationFactory(award=award)
    assignment = assignments.assign(report, judge, by=staff)
    evaluations.save(assignment, judge=judge, scores={"approach": value, "results": value}, submit=True)
    report.refresh_from_db()
    return report


@pytest.fixture
def event(db):
    award = AwardFactory(judges_per_report=1)
    manager, staff, leader = ManagerFactory(awards=[award]), StaffFactory(), LeaderFactory()
    judge = JudgeFactory(awards=[award])
    reports = [_scored(award, staff, judge, 9), _scored(award, staff, judge, 5)]
    return {"award": award, "manager": manager, "staff": staff, "leader": leader, "judge": judge, "reports": reports}


def test_the_award_manager_decides_entries_not_staff_or_leaders(event):
    report = event["reports"][0]
    for other in (event["staff"], event["leader"]):
        with pytest.raises(BusinessRuleError, match="decides each entry's result"):
            results.decide_entry(report, by=other, successful=True)
    results.decide_entry(report, by=event["manager"], successful=True)
    assert report.status == "approved" and not report.result_published
    assert not applications.has_result(report)                       # provisional: not out yet


def test_the_result_goes_to_leadership_only_when_every_entry_is_decided(event):
    award, manager = event["award"], event["manager"]
    results.decide_entry(event["reports"][0], by=manager, successful=True)
    with pytest.raises(BusinessRuleError, match="needs a result"):
        results.send_to_leadership(award, by=manager)
    still_judged = ApplicationFactory(award=award)                    # accepted, not judged yet
    results.decide_entry(event["reports"][1], by=manager, successful=False)
    with pytest.raises(BusinessRuleError, match="still with staff or judges"):
        results.send_to_leadership(award, by=manager)
    applications.decline_entry(still_judged, by=event["staff"], note="Not eligible")
    results.send_to_leadership(award, by=manager, note="Two entries")
    award.refresh_from_db()
    assert award.results_status == "submitted"
    assert Notification.objects.filter(user=event["leader"], message__contains="ready for your approval").exists()


def test_nothing_changes_while_it_is_with_leadership_and_a_send_back_reopens_it(event):
    award, manager, leader = event["award"], event["manager"], event["leader"]
    for report, ok in zip(event["reports"], (True, False), strict=True):
        results.decide_entry(report, by=manager, successful=ok)
    results.send_to_leadership(award, by=manager)
    with pytest.raises(BusinessRuleError, match="with leadership"):
        results.decide_entry(event["reports"][1], by=manager, successful=True)
    with pytest.raises(BusinessRuleError, match="Say what needs another look"):
        results.send_back(award, by=leader, note=" ")
    results.send_back(award, by=leader, note="Check the second entry's evidence")
    assert Notification.objects.filter(user=manager, message__contains="sent the award's result back").exists()
    results.decide_entry(event["reports"][1], by=manager, successful=True)   # the manager can change it now
    results.send_to_leadership(award, by=manager)
    award.refresh_from_db()
    assert award.results_status == "submitted"


def test_approving_publishes_the_whole_award_and_tells_each_applicant(event):
    award, manager = event["award"], event["manager"]
    for report, ok in zip(event["reports"], (True, False), strict=True):
        results.decide_entry(report, by=manager, successful=ok)
    results.send_to_leadership(award, by=manager)
    with pytest.raises(BusinessRuleError, match="Only leadership"):
        results.approve(award, by=manager)
    results.approve(award, by=event["leader"])
    for report in event["reports"]:
        report.refresh_from_db()
        assert report.result_published and applications.has_result(report)
        assert Notification.objects.filter(user=report.applicant, message__contains="results are out").exists()
    with pytest.raises(BusinessRuleError, match="already published"):
        results.decide_entry(event["reports"][0], by=manager, successful=False)
    with pytest.raises(BusinessRuleError, match="isn't waiting"):
        results.approve(award, by=event["leader"])


def test_the_leader_and_manager_pages(event, client):
    award, manager, leader = event["award"], event["manager"], event["leader"]
    for user in (manager, leader):
        user.set_password("Test-pass-2026!")
        user.save()
    login(client, manager.email, "Test-pass-2026!")
    page = client.get(reverse("awards:prepare_results") + f"?award={award.slug}").content.decode()
    assert "Scored entries to decide (2)" in page and ">Successful</button>" in page
    for report, decision in zip(event["reports"], ("successful", "not"), strict=True):
        client.post(reverse("awards:decide_result", args=[report.pk]), {"decision": decision})
    client.post(reverse("awards:send_results", args=[award.slug]), {"note": "All decided"})

    client.post(reverse("accounts:logout"))
    login(client, leader.email, "Test-pass-2026!")
    overview = client.get(reverse("dashboard:overview")).content.decode()
    assert "1 award result waiting for your approval" in overview
    page = client.get(reverse("dashboard:results")).content.decode()
    assert "Waiting for your approval (1)" in page and "All decided" in page and "1</strong>" in page
    assert reverse("awards:decide_result", args=[event["reports"][0].pk]) not in page   # no per-entry buttons
    client.post(reverse("dashboard:decide_award", args=[award.slug]), {"decision": "approve"})
    award.refresh_from_db()
    assert award.results_status == "approved"
    board = client.get(reverse("core:results") + f"?award={award.slug}").content.decode()
    assert event["reports"][0].reference in board and event["reports"][1].reference in board


def test_leaders_no_longer_have_request_or_reevaluation_pages(event, client):
    from django.urls import NoReverseMatch
    with pytest.raises(NoReverseMatch):
        reverse("dashboard:requests")
    leader = event["leader"]
    leader.set_password("Test-pass-2026!")
    leader.save()
    login(client, leader.email, "Test-pass-2026!")
    assert client.get(reverse("awards:reevaluations")).status_code == 403
    menu = client.get(reverse("dashboard:overview")).content.decode()
    for gone in ("Requests to confirm", "Re-evaluations", "Audit log", "Duplicate review"):
        assert gone not in menu


def test_a_leader_can_publish_decided_entries_while_others_are_still_pending(event):
    award, manager, leader = event["award"], event["manager"], event["leader"]
    with pytest.raises(BusinessRuleError, match="no decided entry"):
        results.publish_now(award, by=leader)
    results.decide_entry(event["reports"][0], by=manager, successful=True)      # the other is scored, undecided
    with_judges = ApplicationFactory(award=award)                               # still with staff or judges
    for other in (manager, event["staff"]):
        with pytest.raises(BusinessRuleError, match="Only leadership"):
            results.publish_now(award, by=other)

    newly = results.publish_now(award, by=leader, note="Don't wait for the late judge")
    assert [r.pk for r in newly] == [event["reports"][0].pk]
    published, undecided = event["reports"]
    published.refresh_from_db(), undecided.refresh_from_db(), with_judges.refresh_from_db()
    assert published.result_published and applications.has_result(published)
    assert not undecided.result_published and not with_judges.result_published
    assert Notification.objects.filter(user=published.applicant, message__contains="results are out").exists()
    assert not Notification.objects.filter(user=undecided.applicant, message__contains="results are out").exists()
    assert Notification.objects.filter(user=manager, message__contains="2 other entries are still in progress").exists()
    award.refresh_from_db()
    assert award.results_status == "approved"
    from apps.audit.models import AuditLog
    log = AuditLog.objects.filter(action="status_change", entity_id=str(award.pk)).latest("timestamp")
    assert log.changes["early"] is True and log.changes["still_pending"] == 2 and log.changes["published"] == 1

    results.decide_entry(undecided, by=manager, successful=False)               # decided later: publish again
    assert [r.pk for r in results.publish_now(award, by=leader)] == [undecided.pk]


def test_the_leader_page_offers_publish_now(event, client):
    award, manager, leader = event["award"], event["manager"], event["leader"]
    results.decide_entry(event["reports"][0], by=manager, successful=True)
    leader.set_password("Test-pass-2026!")
    leader.save()
    login(client, leader.email, "Test-pass-2026!")
    page = client.get(reverse("dashboard:results")).content.decode()
    assert "Publish 1 decided" in page
    response = client.post(reverse("dashboard:decide_award", args=[award.slug]), {"decision": "publish_now"},
                           follow=True)
    assert "1 decided entry published" in response.content.decode()
    event["reports"][0].refresh_from_db()
    assert event["reports"][0].result_published
    manager_client = client.__class__()
    manager.set_password("Test-pass-2026!")
    manager.save()
    login(manager_client, manager.email, "Test-pass-2026!")
    assert manager_client.post(reverse("dashboard:decide_award", args=[award.slug]),
                               {"decision": "publish_now"}).status_code == 403
