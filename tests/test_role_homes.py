"""
Roadmap step 3.3, Authentication and roles, on real data:
"Login and logout work, and each role sees only its own pages."

Each role logs in through the real login page and lands on its own home
page, which shows only that user's real data from the database. Other
roles' pages give 403, and nobody but an admin can open /admin/.
"""
import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import ApplicantProfile, JudgeProfile, User
from apps.applications.models import Application
from apps.assignments import services as assignment_services
from apps.assignments.models import JudgeAssignment

from .conftest import ACCOUNTS, login, make_user
from .factories import ApplicantProfileFactory, ApplicationFactory, AwardFactory, StaffFactory

HOMES = {"applicant": "entries:dashboard", "staff": "awards:staff_home",
         "judge": "judging:assignments", "leader": "dashboard:overview"}


@pytest.fixture
def real(applicant_client, judge_client, judge2_client):
    """
    Real records: the logged-in demo applicant (Priya) owns report A; another
    applicant owns report B. Judge Kapoor is assigned A, judge Rao is assigned B.
    The award is blind, so judges must not see who applied.
    """
    award = AwardFactory(name="Business Excellence Award", blind_judging=True)
    staff = StaffFactory()
    priya = User.objects.get(email=ACCOUNTS["applicant"])        # made by the login fixtures
    ApplicantProfile.objects.filter(user=priya).delete()          # replace the login fixture's test organisation
    ApplicantProfileFactory(user=priya, organisation_name="Acme Precision Pvt Ltd")
    report_a = ApplicationFactory(applicant=priya, award=award, reference="BEA-2026-AAAAAA",
                                  content={"org": "Acme Precision Pvt Ltd", "city": "Pune", "story": "Less waste."})
    report_b = ApplicationFactory(award=award, reference="BEA-2026-BBBBBB")
    kapoor = User.objects.get(email=ACCOUNTS["judge"])
    rao = User.objects.get(email=ACCOUNTS["judge2"])
    for judge in (kapoor, rao):
        JudgeProfile.objects.create(user=judge).awards.set([award])
    a_kapoor = assignment_services.assign(report_a, kapoor, by=staff)
    a_rao = assignment_services.assign(report_b, rao, by=staff)
    return {"award": award, "report_a": report_a, "report_b": report_b, "a_kapoor": a_kapoor, "a_rao": a_rao}


def client_for(email):
    c = Client()
    assert login(c, email).status_code == 302
    return c


# --- Login lands each role on its own home -----------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("role", ["applicant", "staff", "judge", "leader"])
def test_login_lands_on_own_home_and_logout_ends_access(role):
    email = f"{role}@example.com"
    make_user(email, role)
    c = Client()
    response = login(c, email)
    assert response["Location"] == reverse(HOMES[role])
    assert c.get(reverse(HOMES[role])).status_code == 200
    c.post(reverse("accounts:logout"))
    after = c.get(reverse(HOMES[role]))
    assert after.status_code == 302 and after["Location"].startswith(reverse("accounts:login"))


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["applicant", "staff", "judge", "leader"])
def test_each_role_gets_403_on_the_other_homes(role):
    make_user(f"{role}@example.com", role)
    c = client_for(f"{role}@example.com")
    for other, home in HOMES.items():
        if other != role:
            assert c.get(reverse(home)).status_code == 403, f"{role} opened {other}'s home"


# --- Admin pages: admins only -------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("role", ["applicant", "staff", "judge", "leader"])
def test_normal_users_cannot_open_admin_pages(role):
    make_user(f"{role}@example.com", role)
    c = client_for(f"{role}@example.com")
    response = c.get("/admin/")
    assert response.status_code == 302 and "/admin/login/" in response["Location"]


@pytest.mark.django_db
def test_admin_can_open_admin_pages():
    User.objects.create_superuser(email="admin@example.com", password="Test-pass-2026!")
    c = Client()
    c.post("/admin/login/", {"username": "admin@example.com", "password": "Test-pass-2026!"})
    assert c.get("/admin/").status_code == 200


# --- Real data: each user sees only their own ---------------------------------

@pytest.mark.django_db
def test_applicant_home_shows_only_their_own_real_applications(real, applicant_client):
    page = applicant_client.get(reverse("entries:dashboard")).content.decode()
    assert "BEA-2026-AAAAAA" in page
    assert "BEA-2026-BBBBBB" not in page
    assert "Acme Precision Pvt Ltd" in page                      # their organisation


@pytest.mark.django_db
def test_new_applicant_home_is_empty(real):
    c = Client()
    c.post(reverse("accounts:signup"), {"full_name": "New Person", "email": "new@example.com",
                                        "password1": "Strong-pass-123", "password2": "Strong-pass-123",
                                        "organisation_name": "New Person Co", "gstin": "29QWERT1234Y1Z9",
                                        "holder_pan": "QWERT1234Y"})
    page = c.get(reverse("entries:dashboard")).content.decode()
    assert "You have no applications yet" in page
    assert "BEA-2026" not in page
    assert "New Person Co" in page                               # the organisation given at sign-up
    assert "Staff are verifying your organisation" in page


@pytest.mark.django_db
def test_applicant_home_shows_verification_status(real, applicant_client):
    profile = ApplicantProfile.objects.get(user__email=ACCOUNTS["applicant"])
    profile.verification_status = "pending"
    profile.save()
    page = applicant_client.get(reverse("entries:dashboard")).content.decode()
    assert "Staff are verifying your organisation" in page


@pytest.mark.django_db
def test_judge_home_shows_only_their_own_assignments_with_blind_applied(real, judge_client, judge2_client):
    kapoor = judge_client.get(reverse("judging:assignments")).content.decode()
    rao = judge2_client.get(reverse("judging:assignments")).content.decode()
    assert "BEA-2026-AAAAAA" in kapoor and "BEA-2026-BBBBBB" not in kapoor
    assert "BEA-2026-BBBBBB" in rao and "BEA-2026-AAAAAA" not in rao
    assert "Acme Precision" not in kapoor                        # blind award: identity hidden
    assert "Hidden for blind judging" in kapoor


@pytest.mark.django_db
def test_judge_home_shows_applicant_when_award_is_not_blind(real, judge_client):
    real["award"].blind_judging = False
    real["award"].save()
    page = judge_client.get(reverse("judging:assignments")).content.decode()
    assert "Hidden for blind judging" not in page


@pytest.mark.django_db
def test_judge_accepts_and_declines_from_home(real, judge_client, judge2_client):
    judge_client.post(reverse("judging:respond", args=[real["a_kapoor"].pk]), {"answer": "accept"})
    real["a_kapoor"].refresh_from_db()
    assert real["a_kapoor"].status == JudgeAssignment.Status.IN_REVIEW

    judge2_client.post(reverse("judging:respond", args=[real["a_rao"].pk]), {"answer": "decline"})
    real["report_b"].refresh_from_db()
    assert real["report_b"].status == Application.Status.ACCEPTED        # back to the pool


@pytest.mark.django_db
def test_judge_cannot_answer_another_judges_assignment(real, judge_client):
    response = judge_client.post(reverse("judging:respond", args=[real["a_rao"].pk]), {"answer": "decline"})
    assert response.status_code == 404
    real["a_rao"].refresh_from_db()
    assert real["a_rao"].status == JudgeAssignment.Status.PENDING


@pytest.mark.django_db
def test_staff_home_shows_real_work(real, staff_client):
    waiting = ApplicantProfileFactory(organisation_name="Waiting Org", verification_status="pending")
    ApplicationFactory(award=real["award"], applicant=waiting.user, status="draft")   # applied to this award
    unassigned = ApplicationFactory(award=real["award"], reference="BEA-2026-CCCCCC")
    page = staff_client.get(reverse("awards:staff_home")).content.decode()
    assert "Waiting Org" in page                                  # organisation to verify
    assert unassigned.reference in page                           # submitted, no judges yet
    assert real["report_a"].reference in page                     # 1 of 2 judges: still needs one
    assert "Business Excellence Award" in page


@pytest.mark.django_db
def test_leader_home_shows_whole_event_counts(real, leader_client):
    response = leader_client.get(reverse("dashboard:overview"))
    assert response.context["total"] == 2
    assert response.context["evaluating"] == 2
    row = response.context["awards"][0]
    assert row["award"].name == "Business Excellence Award" and row["evaluations_total"] == 2


# --- Sessions -------------------------------------------------------------------

@pytest.mark.django_db
def test_deactivated_user_is_logged_out_on_next_request(staff_client):
    User.objects.filter(email=ACCOUNTS["staff"]).update(is_active=False)
    response = staff_client.get(reverse("awards:staff_home"))
    assert response.status_code == 302 and response["Location"].startswith(reverse("accounts:login"))


@pytest.mark.django_db
def test_seeded_judge_sees_only_their_seeded_assignments():
    """With the full seed data: every judge's home lists exactly their own assignments."""
    from django.core.management import call_command

    call_command("seed_data", verbosity=0, stdout=open("/dev/null", "w"))
    for judge in User.objects.filter(role="judge"):
        c = Client()
        c.force_login(judge)
        session = c.session
        session["role"] = "judge"
        session.save()
        page = c.get(reverse("judging:assignments")).content.decode()
        mine = set(JudgeAssignment.objects.filter(judge=judge).values_list("report__reference", flat=True))
        others = set(JudgeAssignment.objects.exclude(judge=judge).values_list("report__reference", flat=True)) - mine
        assert all(ref in page for ref in mine)
        assert not any(ref in page for ref in others)
