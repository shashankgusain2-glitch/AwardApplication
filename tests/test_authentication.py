"""
Authentication and role-based access control.

Covers: one login form (the account role decides where you go), applicant sign-up,
hashed passwords, session with user id + role, logout, redirects for
logged-out users, 403 for the wrong role, applicants and judges seeing
only their own data, and forgot password.
"""
import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client
from django.urls import reverse

from .conftest import ACCOUNTS, PASSWORD, login, make_user

ROLES = ["applicant", "staff", "judge", "leader"]
HOME = {"applicant": "entries:dashboard", "staff": "awards:staff_home",
        "judge": "judging:assignments", "leader": "dashboard:overview"}


def _signup(client, **overrides):
    data = {"full_name": "Asha Rao", "email": "asha@newco.example",
            "password1": "Strong-pass-123", "password2": "Strong-pass-123"}
    data.update(overrides)
    return client.post(reverse("accounts:signup"), data)


# --- Passwords -------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.real_hashing
def test_passwords_are_hashed_never_plain_text():
    user = make_user("x@example.com", "applicant")
    assert PASSWORD not in user.password
    assert user.password.startswith("pbkdf2_sha256$")
    assert user.check_password(PASSWORD)


# --- One login form; the account's role decides where you go ----------------

@pytest.mark.django_db
@pytest.mark.parametrize("role", ROLES)
def test_one_login_sends_each_role_to_its_own_area(client, role):
    make_user(f"{role}@example.com", role)
    response = login(client, f"{role}@example.com")
    assert response.status_code == 302
    assert response["Location"] == reverse(HOME[role])


@pytest.mark.django_db
@pytest.mark.parametrize("sent_role", ["staff", "judge", "leader"])
def test_role_sent_with_the_login_form_is_ignored(client, sent_role):
    # The role comes from the account, never from the person logging in.
    make_user("a@example.com", "applicant")
    response = client.post(reverse("accounts:login"),
                           {"email": "a@example.com", "password": PASSWORD, "role": sent_role})
    assert response["Location"] == reverse(HOME["applicant"])
    assert client.session["role"] == "applicant"


@pytest.mark.django_db
def test_wrong_password_and_unknown_email_give_the_same_message(client):
    make_user("a@example.com", "applicant")
    wrong = login(client, "a@example.com", password="nope-nope-1")
    unknown = login(client, "nobody@example.com")
    for response in (wrong, unknown):
        assert b"Incorrect email or password." in response.content
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_email_is_not_case_sensitive(client):
    make_user("Mixed@Example.com", "applicant")
    assert login(client, "mixed@example.com").status_code == 302


@pytest.mark.django_db
def test_inactive_account_cannot_log_in(client):
    make_user("gone@example.com", "staff", is_active=False)
    assert login(client, "gone@example.com").status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
@pytest.mark.parametrize("missing", ["email", "password"])
def test_empty_fields_are_rejected(client, missing):
    data = {"email": "a@example.com", "password": PASSWORD}
    data[missing] = ""
    response = client.post(reverse("accounts:login"), data)
    assert response.status_code == 200
    assert b"This field is required" in response.content


@pytest.mark.django_db
def test_session_holds_user_id_and_role(client):
    user = make_user("j@example.com", "judge")
    login(client, "j@example.com")
    assert client.session["_auth_user_id"] == str(user.pk)
    assert client.session["role"] == "judge"


@pytest.mark.django_db
def test_login_page_is_one_form_with_signup_reset_and_password_toggle(client):
    page = client.get(reverse("accounts:login")).content.decode()
    assert page.count('name="password"') == 1            # one form, no role tabs
    assert 'role="tablist"' not in page
    assert "Sign up to apply" in page
    assert "Forgot password?" in page
    assert "data-toggle-password" in page                # show/hide password button
    assert "data-loading-text" in page                   # loading state


@pytest.mark.django_db
def test_next_page_is_honoured_but_only_on_this_site(client):
    make_user("s@example.com", "staff")
    ok = client.post(reverse("accounts:login"), {"email": "s@example.com", "password": PASSWORD,
                                                 "next": "/staff/settings/"})
    assert ok["Location"] == "/staff/settings/"
    other = Client()
    evil = other.post(reverse("accounts:login"), {"email": "s@example.com", "password": PASSWORD,
                                                  "next": "https://evil.example/"})
    assert evil["Location"] == reverse("awards:staff_home")


# --- Sign up (applicants only) ---------------------------------------------

@pytest.mark.django_db
@pytest.mark.real_hashing
def test_applicant_can_sign_up_and_is_logged_in(client):
    response = _signup(client)
    assert response["Location"] == reverse("entries:dashboard")
    user = get_user_model().objects.get(email="asha@newco.example")
    assert user.role == "applicant"
    assert user.password.startswith("pbkdf2_sha256$")
    assert client.session["role"] == "applicant"


@pytest.mark.django_db
def test_signup_always_creates_an_applicant_even_if_role_is_sent(client):
    _signup(client, role="leader")
    assert get_user_model().objects.get(email="asha@newco.example").role == "applicant"


@pytest.mark.django_db
@pytest.mark.parametrize("overrides,message", [
    ({"password2": "Different-123"}, b"don&#x27;t match"),
    ({"password1": "123", "password2": "123"}, b"too short"),
    ({"password1": "password123", "password2": "password123"}, b"too common"),
    ({"email": "not-an-email"}, b"Enter a valid email"),
    ({"full_name": ""}, b"This field is required"),
])
def test_signup_validation(client, overrides, message):
    response = _signup(client, **overrides)
    assert response.status_code == 200
    assert message in response.content
    assert not get_user_model().objects.filter(email="asha@newco.example").exists()


@pytest.mark.django_db
def test_signup_rejects_existing_email_in_any_case(client):
    make_user("asha@newco.example", "applicant")
    response = _signup(client, email="ASHA@newco.example")
    assert b"already exists" in response.content


# --- Logout ----------------------------------------------------------------

@pytest.mark.django_db
def test_logout_ends_the_session(applicant_client):
    response = applicant_client.post(reverse("accounts:logout"))
    assert response["Location"] == reverse("core:home")
    assert "_auth_user_id" not in applicant_client.session
    assert applicant_client.get(reverse("entries:dashboard")).status_code == 302


@pytest.mark.django_db
def test_logout_needs_post(applicant_client):
    assert applicant_client.get(reverse("accounts:logout")).status_code == 405


# --- Route protection (RBAC) ------------------------------------------------

PROTECTED = [
    ("entries:dashboard", "applicant"), ("entries:organisation", "applicant"),
    ("entries:form", "applicant"), ("entries:status", "applicant"),
    ("judging:assignments", "judge"), ("judging:score", "judge"),
    ("awards:staff_home", "staff"), ("awards:settings", "staff"), ("awards:form_builder", "staff"),
    ("awards:entries", "staff"), ("awards:duplicates", "staff"), ("awards:assign", "staff"),
    ("dashboard:overview", "leader"), ("dashboard:review", "leader"), ("dashboard:results", "leader"),
]


@pytest.mark.django_db
@pytest.mark.parametrize("name,role", PROTECTED)
def test_logged_out_users_are_sent_to_login(client, name, role):
    response = client.get(reverse(name))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:login"))
    assert "next=" in response["Location"]


WRONG_ROLE = [(name, role, as_role) for name, role in PROTECTED for as_role in ROLES if as_role != role]


@pytest.mark.django_db
@pytest.mark.parametrize("name,role,as_role", WRONG_ROLE)
def test_other_roles_get_403_access_denied(name, role, as_role):
    c = Client()
    make_user(f"{as_role}@example.com", as_role)
    login(c, f"{as_role}@example.com")
    response = c.get(reverse(name))
    assert response.status_code == 403
    assert b"Access Denied" in response.content


@pytest.mark.django_db
def test_changed_role_in_session_logs_the_user_out(staff_client):
    session = staff_client.session
    session["role"] = "leader"         # tampered or stale session
    session.save()
    response = staff_client.get(reverse("awards:staff_home"))
    assert response.status_code == 302
    assert "_auth_user_id" not in staff_client.session


# --- Users only see their own data -----------------------------------------


@pytest.mark.django_db
def test_judge_cannot_open_another_judges_report(seeded):
    from apps.assignments.models import JudgeAssignment

    from .conftest import seeded_client
    kapoor, rao = seeded_client("judge"), seeded_client("judge2")
    mine = JudgeAssignment.objects.filter(judge__email=ACCOUNTS["judge"]).first()
    theirs = JudgeAssignment.objects.filter(judge__email=ACCOUNTS["judge2"]).first()
    assert kapoor.get(reverse("judging:score", args=[mine.pk])).status_code == 200
    assert kapoor.get(reverse("judging:score", args=[theirs.pk])).status_code == 404   # not even admitted to exist
    assert rao.get(reverse("judging:score", args=[mine.pk])).status_code == 404
    assert rao.get(reverse("judging:score", args=[theirs.pk])).status_code == 200


# --- Forgot password -------------------------------------------------------

@pytest.mark.django_db
def test_forgot_password_sends_a_link_that_sets_a_new_password(client):
    make_user("p@example.com", "applicant")
    response = client.post(reverse("accounts:password_reset"), {"email": "p@example.com"})
    assert response["Location"] == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 1
    link = re.search(r"https?://[^/]+(/password-reset/\S+/)", mail.outbox[0].body).group(1)

    form_page = client.get(link, follow=True)               # Django swaps the token for a session
    assert b"Set a new password" in form_page.content
    client.post(form_page.redirect_chain[-1][0] if form_page.redirect_chain else link,
                {"new_password1": "Brand-new-pass-9", "new_password2": "Brand-new-pass-9"})
    assert get_user_model().objects.get(email="p@example.com").check_password("Brand-new-pass-9")


@pytest.mark.django_db
def test_forgot_password_does_not_reveal_unknown_emails(client):
    response = client.post(reverse("accounts:password_reset"), {"email": "nobody@example.com"})
    assert response["Location"] == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_demo_accounts_seed_creates_every_role():
    from django.core.management import call_command
    call_command("seed_demo", verbosity=0)
    roles = set(get_user_model().objects.filter(email__in=ACCOUNTS.values()).values_list("role", flat=True))
    assert roles == {"applicant", "staff", "judge", "leader"}
