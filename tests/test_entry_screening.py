"""
Staff check every submitted entry: Accept sends it on to judges, Decline tells the
applicant why. And while judges work, the applicant sees how far judging has got.
"""
import pytest
from django.test import Client
from django.urls import reverse

from apps.applications import services as applications
from apps.applications.models import Application
from apps.assignments import services as assignments
from apps.core.services import BusinessRuleError
from apps.notifications.models import Notification

from .conftest import login as web_login
from .factories import ApplicantProfileFactory, ApplicationFactory, AwardFactory, JudgeFactory, StaffFactory

S = Application.Status


@pytest.fixture
def entry(db):
    award = AwardFactory(judges_per_report=3)
    staff = StaffFactory()
    judges = [JudgeFactory(awards=[award]) for _ in range(3)]
    report = ApplicationFactory(award=award, status=S.SUBMITTED)
    return {"award": award, "staff": staff, "judges": judges, "report": report}


def login(user):
    client = Client()
    assert web_login(client, user.email).status_code == 302, "test login failed"
    return client


def test_a_submitted_entry_cannot_go_to_judges_before_staff_accept_it(entry):
    with pytest.raises(BusinessRuleError, match="Accept this entry first"):
        assignments.assign(entry["report"], entry["judges"][0], by=entry["staff"])


def test_accepting_tells_the_applicant_and_opens_judging(entry):
    applications.accept_entry(entry["report"], by=entry["staff"])
    assert entry["report"].status == S.ACCEPTED
    assert Notification.objects.filter(user=entry["report"].applicant,
                                       message__contains="accepted for judging").exists()
    assignments.assign(entry["report"], entry["judges"][0], by=entry["staff"])
    entry["report"].refresh_from_db()
    assert entry["report"].status == S.ASSIGNED


def test_only_verified_organisations_are_accepted(entry):
    pending = ApplicantProfileFactory(verification_status="pending")
    report = ApplicationFactory(award=entry["award"], applicant=pending.user, status=S.SUBMITTED)
    with pytest.raises(BusinessRuleError, match="Verify the organisation first"):
        applications.accept_entry(report, by=entry["staff"])


def test_declining_needs_a_reason_the_applicant_sees(entry):
    with pytest.raises(BusinessRuleError, match="Give a reason"):
        applications.decline_entry(entry["report"], by=entry["staff"], note=" ")
    applications.decline_entry(entry["report"], by=entry["staff"], note="Plant opened after the cut-off date")
    assert entry["report"].status == S.REJECTED
    note = Notification.objects.filter(user=entry["report"].applicant).latest("created_at")
    assert "Plant opened after the cut-off date" in note.message


def test_an_accepted_entry_can_still_be_declined_before_judges_get_it(entry):
    applications.accept_entry(entry["report"], by=entry["staff"])
    applications.decline_entry(entry["report"], by=entry["staff"], note="Found to be a duplicate entry")
    assert entry["report"].status == S.REJECTED


def test_staff_off_the_award_cannot_accept(entry):
    outsider = StaffFactory(awards=[])
    with pytest.raises(BusinessRuleError):
        applications.accept_entry(entry["report"], by=outsider)
    assert login(outsider).post(reverse("awards:accept_report", args=[entry["report"].pk])).status_code == 404


def test_entries_page_accept_and_decline_buttons(entry):
    client = login(entry["staff"])
    page = client.get(reverse("awards:entries")).content.decode()
    assert ">Accept</button>" in page and "Decline entry" in page

    client.post(reverse("awards:accept_report", args=[entry["report"].pk]))
    entry["report"].refresh_from_db()
    assert entry["report"].status == S.ACCEPTED

    client.post(reverse("awards:reject_report", args=[entry["report"].pk]), {"note": ""})
    entry["report"].refresh_from_db()
    assert entry["report"].status == S.ACCEPTED            # no reason: refused


def test_applicant_sees_accepted_on_their_timeline(entry):
    applications.accept_entry(entry["report"], by=entry["staff"])
    page = login(entry["report"].applicant).get(reverse("entries:status")).content.decode()
    assert "Accepted for judging" in page


def test_applicant_sees_judging_progress_counts_only(entry):
    report = entry["report"]
    applications.accept_entry(report, by=entry["staff"])
    made = [assignments.assign(report, j, by=entry["staff"]) for j in entry["judges"]]
    assignments.start_review(made[0], judge=entry["judges"][0])

    client = login(report.applicant)
    home = client.get(reverse("entries:dashboard")).content.decode()
    assert "0 of 3 judges finished" in home and "1 reviewing now" in home and "2 not started yet" in home
    status = client.get(reverse("entries:status")).content.decode()
    assert "1 reviewing now" in status
    for judge in entry["judges"]:                          # never who the judges are
        assert judge.display_name not in home and judge.email not in home


def test_staff_accept_and_decline_through_the_api(entry):
    from rest_framework.test import APIClient
    api = APIClient()
    api.force_authenticate(entry["staff"])
    url = f"/api/v1/applications/{entry['report'].pk}/change-status/"
    response = api.post(url, {"status": "accepted"}, format="json")
    assert response.status_code == 200 and response.json()["data"]["status"] == "accepted"
    assert api.post(url, {"status": "rejected"}, format="json").status_code == 400          # needs a reason
    response = api.post(url, {"status": "rejected", "note": "Not eligible"}, format="json")
    assert response.status_code == 200 and response.json()["data"]["status"] == "rejected"
