"""
Replacing a judge who isn't responding, from the staff Assign judges page.

A judge who is assigned but never accepts or scores holds up the award's result,
so programme staff can give the assignment to another eligible judge. The old
assignment is kept as declined, the change is audited and both judges are told.
The award manager can't do it (the strict split: staff do the work).
"""
import pytest
from django.test import Client
from django.urls import reverse

from apps.assignments import services as assignments
from apps.assignments.models import JudgeAssignment
from apps.audit.models import AuditLog
from apps.notifications.models import Notification

from .factories import ApplicationFactory, AwardFactory, JudgeFactory, ManagerFactory, StaffFactory

A = JudgeAssignment.Status


def web(user):
    client = Client()
    client.force_login(user)
    session = client.session
    session["role"] = user.role
    session.save()
    return client


@pytest.fixture
def case(db):
    """A report with one silent judge; a free judge and a conflicted judge are on the panel."""
    award = AwardFactory(judges_per_report=1, staff=[])
    staff = StaffFactory(awards=[award])
    manager = ManagerFactory(awards=[award])
    report = ApplicationFactory(award=award)
    silent, free, conflicted = (JudgeFactory(awards=[award]) for _ in range(3))
    assignments.record_conflict(judge=conflicted, profile=report.applicant.applicant_profile, by=staff)
    assignment = assignments.assign(report, silent, by=staff)
    return {"award": award, "staff": staff, "manager": manager, "report": report, "assignment": assignment,
            "silent": silent, "free": free, "conflicted": conflicted}


def _replace(client, case, judge, reason=""):
    url = reverse("awards:replace_judge", args=[case["report"].pk, case["assignment"].pk])
    return client.post(url, {"judge": judge.pk, "reason": reason}, follow=True)


@pytest.mark.django_db
def test_page_lists_assignments_and_offers_only_eligible_replacements(case):
    page = web(case["staff"]).get(reverse("awards:assign", args=[case["report"].pk])).content.decode()
    assert "Replace judge" in page and "Pending" in page
    assert reverse("awards:replace_judge", args=[case["report"].pk, case["assignment"].pk]) in page
    assert f'value="{case["free"].pk}"' in page
    assert f'value="{case["conflicted"].pk}"' not in page        # conflicts are never offered
    assert f'<option value="{case["silent"].pk}"' not in page    # nor the judge already on it


@pytest.mark.django_db
def test_staff_replace_a_pending_judge(case):
    response = _replace(web(case["staff"]), case, case["free"], reason="Not responding")
    assert "replaces" in response.content.decode()
    case["assignment"].refresh_from_db()
    assert case["assignment"].status == A.DECLINED                # kept for history
    new = JudgeAssignment.objects.get(report=case["report"], judge=case["free"])
    assert new.status == A.PENDING and new.round == case["assignment"].round

    log = AuditLog.objects.get(action="reassign", entity_id=str(new.pk))
    assert log.user == case["staff"]
    assert log.changes == {"from": case["silent"].email, "to": case["free"].email, "reason": "Not responding"}

    assert Notification.objects.filter(user=case["free"], kind="assignment",
                                       message__startswith="New report to judge").exists()
    assert Notification.objects.filter(user=case["silent"], message__contains="withdrawn").exists()


@pytest.mark.django_db
def test_in_review_judge_can_be_replaced(case):
    assignments.start_review(case["assignment"], judge=case["silent"])
    _replace(web(case["staff"]), case, case["free"])
    assert JudgeAssignment.objects.filter(report=case["report"], judge=case["free"], status=A.PENDING).exists()


@pytest.mark.django_db
def test_completed_assignment_cannot_be_replaced(case):
    JudgeAssignment.objects.filter(pk=case["assignment"].pk).update(status=A.COMPLETED)
    response = _replace(web(case["staff"]), case, case["free"])
    assert "can&#x27;t be reassigned" in response.content.decode()
    assert not JudgeAssignment.objects.filter(judge=case["free"]).exists()
    page = web(case["staff"]).get(reverse("awards:assign", args=[case["report"].pk])).content.decode()
    assert "Replace judge" not in page


@pytest.mark.django_db
def test_conflicted_judge_cannot_be_chosen(case):
    response = _replace(web(case["staff"]), case, case["conflicted"])
    assert "conflict" in response.content.decode()
    case["assignment"].refresh_from_db()
    assert case["assignment"].status == A.PENDING                 # nothing changed
    assert not JudgeAssignment.objects.filter(judge=case["conflicted"]).exists()
    assert not AuditLog.objects.filter(action="reassign").exists()


@pytest.mark.django_db
def test_wrong_roles_are_refused(case):
    assert _replace(web(case["manager"]), case, case["free"]).status_code == 403
    assert _replace(web(case["silent"]), case, case["free"]).status_code == 403
    with pytest.raises(assignments.BusinessRuleError, match="award managers don't"):
        assignments.reassign(case["assignment"], case["free"], by=case["manager"])
    case["assignment"].refresh_from_db()
    assert case["assignment"].status == A.PENDING
    assert not JudgeAssignment.objects.filter(judge=case["free"]).exists()


@pytest.mark.django_db
def test_staff_off_the_award_cannot_replace(case):
    outsider = StaffFactory(awards=[AwardFactory()])
    assert _replace(web(outsider), case, case["free"]).status_code == 404
    with pytest.raises(assignments.BusinessRuleError):
        assignments.reassign(case["assignment"], case["free"], by=outsider)
