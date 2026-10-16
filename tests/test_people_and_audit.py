"""
R5 account and admin tools: leaders add staff, judges and leaders from the
portal (each gets a set-your-password email), deactivate and reactivate
them, and read the audit log. No /admin/ needed for daily work.
"""
import re

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import JudgeProfile, User
from apps.audit.models import AuditLog

from .factories import LeaderFactory, StaffFactory


@pytest.fixture
def saved(django_capture_on_commit_callbacks):
    """`with saved():` runs the block, then the after-save callbacks (the emails)."""
    return lambda: django_capture_on_commit_callbacks(execute=True)


def leader_client(leader=None):
    leader = leader or LeaderFactory()
    c = Client()
    c.force_login(leader)
    session = c.session
    session["role"] = "leader"
    session.save()
    return c, leader


NEW_JUDGE = {"name": "Dr. S. Menon", "email": "Menon@Judges.Example", "role": "judge",
             "expertise": "Energy", "priority": "2", "max_open_assignments": "6"}


@pytest.mark.django_db
def test_leader_adds_a_judge_who_sets_a_password_and_lands_on_their_reports(saved, mailoutbox):
    client, _ = leader_client()
    with saved():
        response = client.post(reverse("dashboard:people"), NEW_JUDGE)
    assert response.status_code == 302
    judge = User.objects.get(email="menon@judges.example")
    assert judge.role == "judge" and not judge.has_usable_password()
    profile = JudgeProfile.objects.get(user=judge)
    assert (profile.expertise, profile.priority, profile.max_open_assignments) == ("Energy", 2, 6)

    # The invite email holds a one-time set-your-password link
    assert len(mailoutbox) == 1 and mailoutbox[0].to == ["menon@judges.example"]
    link = re.search(r"http://localhost:8000(/password-reset/\S+/)", mailoutbox[0].body).group(1)
    judge_browser = Client()
    form = judge_browser.get(link, follow=True)
    set_password_url = form.redirect_chain[-1][0] if form.redirect_chain else link
    new_password = "Strong-judge-pass-2026"
    judge_browser.post(set_password_url, {"new_password1": new_password, "new_password2": new_password})
    judge.refresh_from_db()
    assert judge.has_usable_password()

    # They log in and go straight to their assigned reports
    response = judge_browser.post(reverse("accounts:login"), {"email": "menon@judges.example",
                                                              "password": "Strong-judge-pass-2026"})
    assert response["Location"] == reverse("judging:assignments")
    assert AuditLog.objects.filter(entity="user", entity_id=str(judge.pk), action="create").exists()


@pytest.mark.django_db
@pytest.mark.parametrize("changes,message", [
    ({"role": "applicant"}, "Applicants sign up themselves"),
    ({"role": "superuser"}, "Applicants sign up themselves"),
    ({"email": "not-an-email"}, "valid email"),
    ({"name": ""}, "name"),
])
def test_bad_new_person_is_refused_with_a_message(changes, message):
    client, _ = leader_client()
    response = client.post(reverse("dashboard:people"), {**NEW_JUDGE, **changes}, follow=True)
    assert message in response.content.decode()
    assert not User.objects.filter(role="judge").exists()


@pytest.mark.django_db
def test_an_email_can_only_be_used_once():
    client, leader = leader_client()
    response = client.post(reverse("dashboard:people"), {**NEW_JUDGE, "email": leader.email}, follow=True)
    assert "already exists" in response.content.decode()


@pytest.mark.django_db
def test_deactivate_reactivate_and_resend_invite(saved, mailoutbox):
    client, _ = leader_client()
    staff = StaffFactory()
    url = reverse("dashboard:person_action", args=[staff.pk])
    client.post(url, {"action": "deactivate"})
    staff.refresh_from_db()
    assert not staff.is_active
    response = client.post(url, {"action": "invite"}, follow=True)
    assert "deactivated" in response.content.decode()                # no invite to a deactivated account
    client.post(url, {"action": "activate"})
    with saved():
        client.post(url, {"action": "invite"})
    staff.refresh_from_db()
    assert staff.is_active and mailoutbox[-1].to == [staff.email]


@pytest.mark.django_db
def test_leader_cannot_deactivate_themselves():
    client, leader = leader_client()
    response = client.post(reverse("dashboard:person_action", args=[leader.pk]), {"action": "deactivate"},
                           follow=True)
    leader.refresh_from_db()
    assert leader.is_active and "your own account" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["dashboard:people"])
def test_only_leaders_open_people(client_for, name):
    for page in ("entries:dashboard", "judging:assignments", "awards:staff_home"):
        assert client_for(page).get(reverse(name)).status_code == 403
    assert client_for("dashboard:overview").get(reverse(name)).status_code == 200


@pytest.mark.django_db
def test_leaders_have_no_audit_log_page_but_actions_are_still_recorded(saved):
    from django.urls import NoReverseMatch

    from apps.audit.models import AuditLog
    with pytest.raises(NoReverseMatch):
        reverse("dashboard:audit")
    client, leader = leader_client()
    assert "Audit log" not in client.get(reverse("dashboard:overview")).content.decode()
    with saved():
        client.post(reverse("dashboard:people"), NEW_JUDGE)
    assert AuditLog.objects.filter(user=leader, action="create").exists()   # still written (read in /admin/)


@pytest.mark.django_db
def test_api_created_account_without_password_gets_an_invite(saved, mailoutbox):
    api = APIClient()
    api.force_authenticate(LeaderFactory())
    with saved():
        response = api.post("/api/v1/users/", {"email": "new.staff@awards.example", "name": "New Staff",
                                               "role": "staff"}, format="json")
    assert response.status_code == 201
    assert mailoutbox and mailoutbox[-1].to == ["new.staff@awards.example"]


@pytest.mark.django_db
def test_invite_link_shown_on_screen_only_when_switched_on(settings):
    client, _ = leader_client()
    settings.SHOW_INVITE_LINKS = False
    page = client.post(reverse("dashboard:people"), NEW_JUDGE, follow=True).content.decode()
    assert "/password-reset/" not in page

    settings.SHOW_INVITE_LINKS = True
    page = client.post(reverse("dashboard:people"), {**NEW_JUDGE, "email": "second@judges.example"},
                       follow=True).content.decode()
    assert "send second@judges.example this one-time link yourself" in page and "/password-reset/" in page
