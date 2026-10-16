"""
The strict split between programme staff and the award manager (apps/awards/access.py):
staff do the work, the manager decides. Neither can do the other's job, in the services
(which the API also uses) and on the pages.

    staff     verify organisations, accept/decline entries, record conflicts, assign judges,
              check requests first, draft the form, pass hard cases up
    manager   set the award up, publish the form, confirm requests, answer escalations,
              decide who handles each entry
"""
import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts import services as account_services
from apps.applications import services as applications
from apps.applications.models import Application
from apps.assignments import services as assignments
from apps.awards import services as award_services
from apps.awards import team_work
from apps.awards.models import Escalation
from apps.core import approvals
from apps.core.services import BusinessRuleError
from apps.notifications.models import Notification

from .factories import (
    ApplicationFactory,
    AwardFactory,
    JudgeFactory,
    ManagerFactory,
    StaffFactory,
)


def web(user):
    client = Client()
    client.force_login(user)
    session = client.session
    session["role"] = user.role
    session.save()
    return client


@pytest.fixture
def team(db):
    award = AwardFactory(name="Alpha Award", staff=[])
    manager = ManagerFactory(awards=[award])
    staff, other = StaffFactory(awards=[award]), StaffFactory(awards=[award])
    return {"award": award, "manager": manager, "staff": staff, "other": other,
            "report": ApplicationFactory(award=award, status=Application.Status.SUBMITTED)}


def _questions(*labels):
    return [{"key": label.lower().replace(" ", "_"), "label": label, "type": "text", "section": "About",
             "required": True} for label in labels]


# --- The manager doesn't do staff work --------------------------------------------------

@pytest.mark.django_db
def test_manager_cannot_screen_entries_or_verify_or_record_conflicts(team):
    manager, report = team["manager"], team["report"]
    with pytest.raises(BusinessRuleError, match="the award manager doesn't"):
        applications.accept_entry(report, by=manager)
    with pytest.raises(BusinessRuleError, match="the award manager doesn't"):
        applications.decline_entry(report, by=manager, note="Ineligible")
    with pytest.raises(BusinessRuleError, match="the award manager doesn't"):
        account_services.verify_organisation(report.applicant.applicant_profile, by=manager, approve=True)
    with pytest.raises(BusinessRuleError, match="the award manager doesn't"):
        assignments.record_conflict(judge=JudgeFactory(awards=[team["award"]]),
                                    profile=report.applicant.applicant_profile, by=manager)
    applications.accept_entry(report, by=team["staff"])            # staff can
    report.refresh_from_db()
    assert report.status == Application.Status.ACCEPTED


@pytest.mark.django_db
def test_manager_never_does_the_staff_check_even_with_no_staff(db):
    award = AwardFactory(staff=[])
    manager = ManagerFactory(awards=[award])
    report = ApplicationFactory(award=award)
    applications.request_edit(report, by=report.applicant, reason="Typo in section 2")
    req = applications.open_request(report, "edit")
    assert not approvals.can_check(manager, req)
    with pytest.raises(BusinessRuleError, match="Programme staff check this request first"):
        applications.decide_request(req, by=manager, approve=True)


@pytest.mark.django_db
def test_manager_pages_hide_staff_actions(team):
    manager = web(team["manager"])
    for name, args in (("awards:verify_organisation", [team["report"].applicant.applicant_profile.pk]),
                       ("awards:accept_report", [team["report"].pk]), ("awards:reject_report", [team["report"].pk]),
                       ("awards:assign", [team["report"].pk]), ("awards:form_edit", [team["award"].slug])):
        assert manager.post(reverse(name, args=args)).status_code == 403, name
    page = manager.get(reverse("awards:entries")).content.decode()
    assert reverse("awards:accept_report", args=[team["report"].pk]) not in page
    assert "Organisations to verify" not in page
    assert reverse("awards:allocate_entry", args=[team["report"].pk]) in page     # the manager allocates


# --- Staff don't set the award up --------------------------------------------------------

@pytest.mark.django_db
def test_staff_cannot_set_the_award_up(team):
    award, staff = team["award"], team["staff"]
    with pytest.raises(BusinessRuleError, match="programme staff don't"):
        award_services.set_status(award, by=staff, status="closed")
    with pytest.raises(BusinessRuleError, match="programme staff don't"):
        award_services.set_panel(award, by=staff, judges=[])
    with pytest.raises(BusinessRuleError, match="programme staff don't"):
        award_services.save_criteria(award, by=staff, rows=[{"round_number": 1, "label": "A", "weight": 100}])
    client = web(staff)
    for name in ("awards:award_edit", "awards:award_criteria", "awards:award_panel", "awards:award_status"):
        assert client.post(reverse(name, args=[award.slug])).status_code == 403, name
    award_services.set_status(award, by=team["manager"], status="closed")        # the manager can
    award.refresh_from_db()
    assert award.status == "closed"


@pytest.mark.django_db
def test_another_awards_manager_cannot_set_it_up(team):
    with pytest.raises(BusinessRuleError, match="sets up Alpha Award"):
        award_services.set_status(team["award"], by=ManagerFactory(), status="closed")


# --- Form: staff draft, the manager publishes --------------------------------------------

@pytest.mark.django_db
def test_form_draft_is_not_used_until_the_manager_publishes_it(team):
    award, staff, manager = team["award"], team["staff"], team["manager"]
    draft = team_work.save_form_draft(award, _questions("Plant name", "Savings"), by=staff)
    award.refresh_from_db()
    assert award.current_form.version == 1 and draft.version == 2 and draft.waiting_for_manager
    assert Notification.objects.filter(user=manager, message__contains="form version 2").exists()
    again = team_work.save_form_draft(award, _questions("Plant name", "Savings", "Method"), by=staff)
    assert again.pk == draft.pk and len(again.questions) == 3                    # one draft, replaced

    with pytest.raises(BusinessRuleError, match="award manager"):
        team_work.review_form_draft(again, by=staff, approve=True)
    with pytest.raises(BusinessRuleError, match="Say what needs changing"):
        team_work.review_form_draft(again, by=manager, approve=False)
    team_work.review_form_draft(again, by=manager, approve=True)
    assert award.current_form.version == 2 and len(award.current_form.questions) == 3
    assert Notification.objects.filter(user=staff, message__contains="approved and published").exists()


@pytest.mark.django_db
def test_manager_sends_the_form_back_and_staff_change_it(team):
    award, staff, manager = team["award"], team["staff"], team["manager"]
    draft = team_work.save_form_draft(award, _questions("Plant name"), by=staff)
    team_work.review_form_draft(draft, by=manager, approve=False, note="Ask for the savings too")
    draft.refresh_from_db()
    assert not draft.waiting_for_manager and not draft.is_published
    page = web(staff).get(reverse("awards:form_builder", args=[award.slug])).content.decode()
    assert "Ask for the savings too" in page
    with pytest.raises(BusinessRuleError, match="isn't waiting"):
        team_work.review_form_draft(draft, by=manager, approve=True)
    resent = team_work.save_form_draft(award, _questions("Plant name", "Savings"), by=staff)
    assert resent.pk == draft.pk and resent.waiting_for_manager and resent.review_note == ""


@pytest.mark.django_db
def test_form_approval_through_the_pages(team):
    award = team["award"]
    staff, manager = web(team["staff"]), web(team["manager"])
    staff.post(reverse("awards:form_edit", args=[award.slug]), {
        "rows": "1", "q-0-key": "", "q-0-label": "Plant name", "q-0-type": "text", "q-0-section": "About"})
    assert award.current_form.version == 1
    page = manager.get(reverse("awards:form_builder", args=[award.slug])).content.decode()
    assert "Approve and publish version 2" in page and "Plant name" in page
    manager.post(reverse("awards:form_review", args=[award.slug]), {"decision": "approve"})
    assert award.current_form.version == 2


@pytest.mark.django_db
def test_award_without_a_manager_staff_publish_directly(db):
    award = AwardFactory(staff=[])
    staff = StaffFactory(awards=[award])
    version = team_work.save_form_draft(award, _questions("Plant name"), by=staff)
    assert version.is_published and award.current_form == version


# --- Escalations: staff ask, the manager answers -----------------------------------------

@pytest.mark.django_db
def test_staff_escalate_and_the_manager_answers(team):
    award, staff, manager, report = team["award"], team["staff"], team["manager"], team["report"]
    with pytest.raises(BusinessRuleError, match="Programme staff"):
        team_work.escalate(award, by=manager, question="?")
    case = team_work.escalate(award, by=staff, question="GSTIN looks reused. Verify?", application=report)
    assert Notification.objects.filter(user=manager, message__contains="needs your decision").exists()
    with pytest.raises(BusinessRuleError, match="award manager"):
        team_work.answer_escalation(case, by=team["other"], answer="Yes")
    team_work.answer_escalation(case, by=manager, answer="Ask the applicant for the GST certificate first.")
    case.refresh_from_db()
    assert case.status == Escalation.Status.ANSWERED
    assert Notification.objects.filter(user=staff, message__contains="GST certificate").exists()
    with pytest.raises(BusinessRuleError, match="already been answered"):
        team_work.answer_escalation(case, by=manager, answer="Again")


@pytest.mark.django_db
def test_escalations_through_the_pages(team):
    award, report = team["award"], team["report"]
    staff, manager = web(team["staff"]), web(team["manager"])
    staff.post(reverse("awards:escalations"), {"award": award.pk, "application": report.pk,
                                               "question": "Applicant disputes the decline", "next": "/staff/entries/"})
    case = Escalation.objects.get()
    assert manager.post(reverse("awards:escalations"), {"award": award.pk, "question": "x"}).status_code == 403
    page = manager.get(reverse("awards:escalations")).content.decode()
    assert "Applicant disputes the decline" in page and report.reference in page
    assert staff.post(reverse("awards:escalation_answer", args=[case.pk]), {"answer": "x"}).status_code == 403
    manager.post(reverse("awards:escalation_answer", args=[case.pk]), {"answer": "Keep it declined."})
    assert "Keep it declined." in staff.get(reverse("awards:escalations")).content.decode()
    # junk never crashes
    assert staff.post(reverse("awards:escalations"), {"award": "abc", "question": "x"}).status_code == 404


@pytest.mark.django_db
def test_no_escalation_without_a_manager(db):
    award = AwardFactory(staff=[])
    with pytest.raises(BusinessRuleError, match="no award manager"):
        team_work.escalate(award, by=StaffFactory(awards=[award]), question="Who decides?")


# --- Allocation: the manager gives entries to staff --------------------------------------

@pytest.mark.django_db
def test_manager_allocates_entries_and_sees_the_workload(team):
    award, staff, manager, report = team["award"], team["staff"], team["manager"], team["report"]
    second = ApplicationFactory(award=award)
    assert team_work.workload(award)["unallocated"] == 2
    with pytest.raises(BusinessRuleError, match="award manager"):
        team_work.allocate(report, by=staff, staff_member=staff)
    with pytest.raises(BusinessRuleError, match="isn't on the Alpha Award staff"):
        team_work.allocate(report, by=manager, staff_member=StaffFactory(awards=[]))
    team_work.allocate(report, by=manager, staff_member=staff)
    assert Notification.objects.filter(user=staff, message__contains="gave this entry to you").exists()
    load = team_work.workload(award)
    assert {r["user"].pk: r["open"] for r in load["rows"]} == {staff.pk: 1, team["other"].pk: 0}
    assert load["unallocated"] == 1
    mine = web(staff).get(reverse("awards:entries") + "?mine=1").content.decode()
    assert report.reference in mine and second.reference not in mine
    team_work.allocate(report, by=manager, staff_member=None)                       # back to anyone
    assert team_work.workload(award)["unallocated"] == 2


@pytest.mark.django_db
def test_allocation_through_the_pages(team):
    report, staff = team["report"], team["staff"]
    manager = web(team["manager"])
    manager.post(reverse("awards:allocate_entry", args=[report.pk]), {"staff": staff.pk, "next": "/staff/entries/"})
    report.refresh_from_db()
    assert report.handled_by == staff
    home = manager.get(reverse("awards:staff_home")).content.decode()
    assert "Your team's workload" in home and f"{staff.display_name}: 1" in home
    assert web(staff).post(reverse("awards:allocate_entry", args=[report.pk]), {"staff": staff.pk}).status_code == 403
    assert manager.post(reverse("awards:allocate_entry", args=[report.pk]), {"staff": "abc"}).status_code == 302


@pytest.mark.django_db
def test_each_role_has_its_own_home_and_menu(team):
    staff_home = web(team["staff"]).get(reverse("awards:staff_home")).content.decode()
    manager_home = web(team["manager"]).get(reverse("awards:staff_home")).content.decode()
    assert "Entries given to you" in staff_home and "Your team&#x27;s workload" not in staff_home
    assert "Your team" in manager_home and "Organisations waiting for verification" not in manager_home
    assert "Ask the manager" in staff_home and "Escalations" in manager_home
    assert reverse("awards:duplicates") not in manager_home
