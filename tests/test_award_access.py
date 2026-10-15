"""
Who works on which award: leaders see and create every award; each award has one
award manager; staff only see the awards they are allocated to. Pages, services,
the API, files, requests and notifications all follow apps/awards/access.py.
"""
import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import services as account_services
from apps.accounts.models import User
from apps.applications import services as applications
from apps.assignments import services as assignments
from apps.awards import services as award_services
from apps.awards.access import awards_for
from apps.core import approvals
from apps.core.services import BusinessRuleError
from apps.notifications.models import Notification

from .factories import (
    ApplicantProfileFactory,
    ApplicationFactory,
    AwardFactory,
    JudgeFactory,
    LeaderFactory,
    ManagerFactory,
    StaffFactory,
)


def web(user):
    """A browser session logged in as this user (with the role in the session, like the login page does)."""
    client = Client()
    client.force_login(user)
    session = client.session
    session["role"] = user.role
    session.save()
    return client


@pytest.fixture
def two(db):
    """Two awards, each with its own manager and staff member, and one submitted report each."""
    alpha, beta = AwardFactory(name="Alpha Award", staff=[]), AwardFactory(name="Beta Award", staff=[])
    m_alpha, m_beta = ManagerFactory(awards=[alpha]), ManagerFactory(awards=[beta])
    s_alpha, s_beta = StaffFactory(awards=[alpha]), StaffFactory(awards=[beta])
    r_alpha, r_beta = ApplicationFactory(award=alpha), ApplicationFactory(award=beta)
    return {"alpha": alpha, "beta": beta, "m_alpha": m_alpha, "m_beta": m_beta, "s_alpha": s_alpha,
            "s_beta": s_beta, "r_alpha": r_alpha, "r_beta": r_beta, "leader": LeaderFactory()}


# --- Who sees what --------------------------------------------------------------------

@pytest.mark.django_db
def test_each_role_sees_only_its_awards(two):
    assert list(awards_for(two["s_alpha"])) == [two["alpha"]]
    assert list(awards_for(two["m_beta"])) == [two["beta"]]
    assert set(awards_for(two["leader"])) == {two["alpha"], two["beta"]}
    assert list(awards_for(StaffFactory(awards=[]))) == []
    assert list(applications.visible_to(two["s_alpha"])) == [two["r_alpha"]]
    assert list(applications.visible_to(two["m_beta"])) == [two["r_beta"]]
    assert set(applications.visible_to(two["leader"])) == {two["r_alpha"], two["r_beta"]}


@pytest.mark.django_db
def test_staff_pages_show_only_their_awards(two):
    staff = web(two["s_alpha"])
    for name in ("awards:staff_home", "awards:award_list", "awards:entries", "awards:assign"):
        page = staff.get(reverse(name)).content.decode()
        assert "Beta Award" not in page and two["r_beta"].reference not in page, name
    assert "Alpha Award" in staff.get(reverse("awards:award_list")).content.decode()
    for name in ("awards:award_edit", "awards:award_criteria", "awards:award_panel", "awards:form_edit",
                 "awards:form_builder"):
        assert staff.get(reverse(name, args=[two["beta"].slug])).status_code == 404, name
        assert staff.get(reverse(name, args=[two["alpha"].slug])).status_code == 200, name
    assert staff.get(reverse("awards:assign", args=[two["r_beta"].pk])).status_code == 404
    response = staff.post(reverse("awards:award_status", args=[two["beta"].slug]), {"status": "closed"})
    assert response.status_code == 404


@pytest.mark.django_db
def test_managers_run_only_the_awards_they_manage(two):
    manager = web(two["m_alpha"])
    assert manager.get(reverse("awards:award_edit", args=[two["alpha"].slug])).status_code == 200
    assert manager.get(reverse("awards:award_edit", args=[two["beta"].slug])).status_code == 404
    assert manager.get(reverse("awards:award_team", args=[two["beta"].slug])).status_code == 404
    page = manager.get(reverse("awards:staff_home")).content.decode()
    assert "Alpha Award" in page and "Beta Award" not in page


@pytest.mark.django_db
def test_staff_cannot_assign_judges_or_reject_on_other_awards(two):
    judge = JudgeFactory(awards=[two["beta"]])
    with pytest.raises(BusinessRuleError, match="aren't on the team for Beta Award"):
        assignments.assign(two["r_beta"], judge, by=two["s_alpha"])
    with pytest.raises(BusinessRuleError, match="aren't on the team"):
        applications.change_status(two["r_beta"], by=two["m_alpha"], new_status="rejected")
    assert assignments.assign(two["r_beta"], judge, by=two["s_beta"]).judge == judge


@pytest.mark.django_db
def test_organisations_to_verify_are_only_those_on_their_awards(two):
    pending = ApplicantProfileFactory(organisation_name="Pending Beta Org", verification_status="pending")
    ApplicationFactory(award=two["beta"], applicant=pending.user, status="draft")
    assert "Pending Beta Org" not in web(two["s_alpha"]).get(reverse("awards:entries")).content.decode()
    assert "Pending Beta Org" in web(two["s_beta"]).get(reverse("awards:entries")).content.decode()
    response = web(two["s_alpha"]).post(reverse("awards:verify_organisation", args=[pending.pk]),
                                        {"decision": "approve"})
    assert response.status_code == 404


@pytest.mark.django_db
def test_api_follows_the_same_rules(two):
    api = APIClient()
    api.force_authenticate(two["s_alpha"])
    rows = api.get(reverse("api:application-list")).json()["data"]["results"]
    assert [r["reference"] for r in rows] == [two["r_alpha"].reference]
    assert api.get(reverse("api:application-detail", args=[two["r_beta"].pk])).status_code == 404
    api.force_authenticate(two["m_beta"])
    rows = api.get(reverse("api:application-list")).json()["data"]["results"]
    assert [r["reference"] for r in rows] == [two["r_beta"].reference]
    summary = api.get(reverse("api:dashboard-summary")).json()["data"]
    assert [a["name"] for a in summary["awards"]] == ["Beta Award"]


# --- Requests and notifications go to the award's own team ---------------------------

@pytest.mark.django_db
def test_requests_reach_and_are_decided_by_the_awards_own_team(two):
    report = two["r_alpha"]
    applications.request_edit(report, by=report.applicant, reason="Typo in section 2")
    req = applications.open_request(report, "edit")
    told = set(Notification.objects.filter(kind="request").values_list("user", flat=True))
    assert told == {two["s_alpha"].pk}                               # Alpha's staff only (not Beta's team)

    assert approvals.waiting(approvals.T.WAITING_STAFF, two["s_beta"]) == []
    assert len(approvals.waiting(approvals.T.WAITING_STAFF, two["m_alpha"])) == 1
    with pytest.raises(BusinessRuleError, match="aren't on the team"):
        applications.decide_request(req, by=two["s_beta"], approve=True)
    applications.decide_request(req, by=two["s_alpha"], approve=True)   # Alpha's staff check it
    req.refresh_from_db()
    assert req.status == approvals.T.WAITING_LEADER
    for wrong in (two["m_beta"], two["s_alpha"]):                        # another award's manager, or staff
        with pytest.raises(BusinessRuleError, match="needs the award manager"):
            applications.decide_request(req, by=wrong, approve=True)
    applications.decide_request(req, by=two["m_alpha"], approve=True)   # Alpha's manager confirms
    req.refresh_from_db()
    assert req.status == approvals.T.APPROVED


# --- Creating awards and choosing teams --------------------------------------------------

@pytest.mark.django_db
def test_only_leaders_create_awards(two):
    for person in (two["s_alpha"], two["m_alpha"]):
        with pytest.raises(BusinessRuleError, match="Only a leader"):
            award_services.create_award(by=person, name="Gamma Award", rounds=["desk"])
        assert web(person).get(reverse("dashboard:award_new")).status_code == 403
    leader = web(two["leader"])
    response = leader.post(reverse("dashboard:award_new"), {
        "name": "Gamma Award", "round1": "desk", "judges_per_report": "2", "entry_fee": "0",
        "applicant_type": "organisation", "manager": two["m_beta"].pk})
    gamma = two["beta"].__class__.objects.get(name="Gamma Award")
    assert response["Location"] == reverse("awards:award_team", args=[gamma.slug])
    assert gamma.manager == two["m_beta"]
    assert Notification.objects.filter(user=two["m_beta"], message__contains="Gamma Award").exists()
    page = leader.get(reverse("dashboard:awards")).content.decode()
    assert "Gamma Award" in page and two["m_beta"].display_name in page


@pytest.mark.django_db
def test_manager_chooses_staff_but_not_the_manager(two):
    newcomer = StaffFactory(awards=[])
    manager = web(two["m_alpha"])
    manager.post(reverse("awards:award_team", args=[two["alpha"].slug]),
                 {"staff": [two["s_alpha"].pk, newcomer.pk], "manager": two["m_beta"].pk})
    two["alpha"].refresh_from_db()
    assert set(two["alpha"].staff.all()) == {two["s_alpha"], newcomer}
    assert two["alpha"].manager == two["m_alpha"]                      # unchanged: only a leader picks it
    assert Notification.objects.filter(user=newcomer, message__contains="Alpha Award").exists()
    with pytest.raises(BusinessRuleError, match="Only a leader can choose"):
        award_services.set_team(two["alpha"], by=two["m_alpha"], staff=[], manager=two["m_beta"],
                                change_manager=True)
    with pytest.raises(BusinessRuleError, match="Only active programme staff"):
        award_services.set_team(two["alpha"], by=two["m_alpha"], staff=[JudgeFactory()])
    with pytest.raises(BusinessRuleError, match="Only a leader or this award's manager"):
        award_services.set_team(two["beta"], by=two["m_alpha"], staff=[])


@pytest.mark.django_db
def test_leader_moves_an_award_to_another_manager(two):
    web(two["leader"]).post(reverse("awards:award_team", args=[two["alpha"].slug]),
                            {"staff": [two["s_alpha"].pk], "manager": two["m_beta"].pk})
    two["alpha"].refresh_from_db()
    assert two["alpha"].manager == two["m_beta"]
    assert web(two["m_alpha"]).get(reverse("awards:award_edit", args=[two["alpha"].slug])).status_code == 404
    assert set(awards_for(two["m_beta"])) == {two["alpha"], two["beta"]}


@pytest.mark.django_db
def test_manager_invites_new_staff_onto_the_team_only(two, settings):
    settings.SHOW_INVITE_LINKS = False
    web(two["m_alpha"]).post(reverse("awards:award_team", args=[two["alpha"].slug]),
                             {"action": "invite", "name": "New Person", "email": "new.person@example.com"})
    person = User.objects.get(email="new.person@example.com")
    assert person.role == User.Role.STAFF and list(awards_for(person)) == [two["alpha"]]
    with pytest.raises(BusinessRuleError, match="Only a leader can create accounts"):
        account_services.create_account(created_by=two["m_alpha"], email="j@example.com", name="J",
                                        role=User.Role.JUDGE)


@pytest.mark.django_db
def test_leaders_add_award_managers_on_the_people_page(two, settings):
    settings.SHOW_INVITE_LINKS = False
    page = web(two["leader"]).get(reverse("dashboard:people")).content.decode()
    assert 'value="manager"' in page and "Alpha Award" in page
    web(two["leader"]).post(reverse("dashboard:people"),
                            {"role": "manager", "name": "Meera Manager", "email": "meera@example.com"})
    assert User.objects.get(email="meera@example.com").role == User.Role.MANAGER


@pytest.mark.django_db
def test_manager_lands_on_the_staff_portal_with_a_team_step(two):
    from .conftest import login
    two["m_alpha"].set_password("Test-pass-2026!")
    two["m_alpha"].save()
    client = Client()
    response = login(client, two["m_alpha"].email)
    assert response["Location"] == reverse("awards:staff_home")
    page = client.get(reverse("awards:award_edit", args=[two["alpha"].slug])).content.decode()
    assert reverse("awards:award_team", args=[two["alpha"].slug]) in page
    staff_page = web(two["s_alpha"]).get(reverse("awards:award_edit", args=[two["alpha"].slug])).content.decode()
    assert reverse("awards:award_team", args=[two["alpha"].slug]) not in staff_page
    assert web(two["s_alpha"]).get(reverse("awards:award_team", args=[two["alpha"].slug])).status_code == 403
