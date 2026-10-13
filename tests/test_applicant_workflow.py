"""
The applicant workflow from the 12 Oct meeting:

  verify email → register organisation (GSTIN + PAN) → choose event
  → fill form (save midway) → submit → see status
  → request edit → staff confirm → edit and resubmit
"""
import pytest
from django.urls import reverse

from apps.accounts.views import SESSION_KEY
from apps.awards.models import Award
from apps.entries.models import Application, Organisation

from .conftest import verify

BE_ANSWERS = {
    "about": "We make precision auto parts.",
    "employees": "640",
    "achievement": "Cut defects by half.",
    "results": "Defects 2% to 1%.",
    "contact": "Priya, 98000 00000",
}


def _start(client, slug="business-excellence"):
    client.post(reverse("entries:start", args=[slug]))
    return Application.objects.get(award__slug=slug)


# --- Email verification ------------------------------------------------------

@pytest.mark.django_db
def test_new_user_is_sent_to_register_after_verifying(client):
    response = verify(client, "new@example.com")
    assert response["Location"] == reverse("entries:register")


@pytest.mark.django_db
def test_wrong_code_does_not_log_in(client):
    client.post(reverse("accounts:verify_email"), {"email": "x@example.com"})
    real = client.session[SESSION_KEY]["code"]
    wrong = "000000" if real != "000000" else "111111"
    response = client.post(reverse("accounts:verify_code"), {"code": wrong})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_too_many_wrong_codes_starts_over(client):
    client.post(reverse("accounts:verify_email"), {"email": "x@example.com"})
    real = client.session[SESSION_KEY]["code"]
    wrong = "000000" if real != "000000" else "111111"
    for _ in range(6):
        response = client.post(reverse("accounts:verify_code"), {"code": wrong})
    assert response["Location"] == reverse("accounts:verify_email")
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_expired_code_is_rejected(client):
    client.post(reverse("accounts:verify_email"), {"email": "x@example.com"})
    session = client.session
    pending = session[SESSION_KEY]
    pending["expires"] = 0
    session[SESSION_KEY] = pending
    session.save()
    response = client.post(reverse("accounts:verify_code"), {"code": pending["code"]})
    assert response["Location"] == reverse("accounts:verify_email")
    assert "_auth_user_id" not in client.session


# --- Organisation registration ---------------------------------------------

@pytest.mark.django_db
def test_register_with_valid_gstin_and_pan(client):
    verify(client, "a@example.com")
    response = client.post(reverse("entries:register"),
                           {"name": "Acme", "gstin": "27abcde1234f1z5", "holder_pan": "pqrsx6789k"})
    assert response["Location"] == reverse("entries:events")
    org = Organisation.objects.get()
    assert (org.gstin, org.holder_pan) == ("27ABCDE1234F1Z5", "PQRSX6789K")  # cleaned to upper case


@pytest.mark.django_db
@pytest.mark.parametrize("gstin,pan", [
    ("27ABCDE1234F1Z", "PQRSX6789K"),   # GSTIN too short
    ("ABCDE1234F1Z527", "PQRSX6789K"),  # GSTIN wrong shape
    ("27ABCDE1234F1Z5", "PQRS6789K"),   # PAN too short
    ("27ABCDE1234F1Z5", "1234567890"),  # PAN wrong shape
])
def test_register_rejects_bad_ids(client, gstin, pan):
    verify(client, "a@example.com")
    client.post(reverse("entries:register"), {"name": "Acme", "gstin": gstin, "holder_pan": pan})
    assert not Organisation.objects.exists()


@pytest.mark.django_db
def test_same_gstin_cannot_be_registered_twice(client, applicant):
    from django.test import Client
    other = Client()
    verify(other, "impostor@example.com")
    other.post(reverse("entries:register"), {"name": "Fake Acme", "gstin": "27ABCDE1234F1Z5", "holder_pan": "ZZZZZ9999Z"})
    assert Organisation.objects.count() == 1


# --- Events and form --------------------------------------------------------

@pytest.mark.django_db
def test_events_page_shows_only_two_events(client, applicant):
    page = client.get(reverse("entries:events")).content.decode()
    assert page.count("<h2") == 2
    assert "Business Excellence Award" in page and "Kaizen Competition" in page


@pytest.mark.django_db
def test_each_event_has_its_own_simple_form(client, applicant):
    be = client.get(reverse("entries:application", args=[_start(client, "business-excellence").pk])).content.decode()
    kz = client.get(reverse("entries:application", args=[_start(client, "kaizen").pk])).content.decode()
    assert "Number of employees" in be and "Number of employees" not in kz
    assert "Team name" in kz and "Team name" not in be


@pytest.mark.django_db
def test_one_report_per_organisation_per_event(client, applicant):
    _start(client)
    _start(client)
    assert Application.objects.count() == 1


@pytest.mark.django_db
def test_save_midway_keeps_answers_without_submitting(client, applicant):
    app = _start(client)
    client.post(reverse("entries:application", args=[app.pk]), {"about": "Half done", "action": "save"})
    app.refresh_from_db()
    assert app.answers == {"about": "Half done"}
    assert app.status == Application.Status.DRAFT


@pytest.mark.django_db
def test_submit_needs_all_required_answers(client, applicant):
    app = _start(client)
    client.post(reverse("entries:application", args=[app.pk]), {"about": "Only this", "action": "submit"})
    app.refresh_from_db()
    assert app.status == Application.Status.DRAFT


@pytest.mark.django_db
def test_submit_puts_report_in_the_pool_and_locks_it(client, applicant):
    app = _start(client)
    client.post(reverse("entries:application", args=[app.pk]), {**BE_ANSWERS, "action": "submit"})
    app.refresh_from_db()
    assert app.status == Application.Status.SUBMITTED
    assert app.answers["employees"] == 640

    # Locked: trying to change it does nothing.
    client.post(reverse("entries:application", args=[app.pk]), {**BE_ANSWERS, "about": "Changed", "action": "save"})
    app.refresh_from_db()
    assert app.answers["about"] == BE_ANSWERS["about"]


@pytest.mark.django_db
def test_applicant_cannot_open_another_organisations_report(client, applicant):
    from django.contrib.auth import get_user_model
    other_user = get_user_model().objects.create(email="b@example.com", username="b@example.com")
    other_org = Organisation.objects.create(name="Other", gstin="29PQRSX6789K1Z1", holder_pan="PQRSX6789K", owner=other_user)
    award = Award.objects.get(slug="kaizen")
    other_app = Application.objects.create(organisation=other_org, award=award, form_version=award.current_form)
    assert client.get(reverse("entries:application", args=[other_app.pk])).status_code == 404


# --- Edit only after staff confirm, and status ------------------------------

@pytest.mark.django_db
def test_edit_after_submit_needs_staff_approval(client, applicant, staff_client):
    app = _start(client)
    client.post(reverse("entries:application", args=[app.pk]), {**BE_ANSWERS, "action": "submit"})

    client.post(reverse("entries:request_edit", args=[app.pk]), {"reason": "Wrong employee count"})
    app.refresh_from_db()
    assert app.edit_request == Application.EditRequest.REQUESTED
    assert not app.can_edit

    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "approve_edit"})
    app.refresh_from_db()
    assert app.can_edit

    client.post(reverse("entries:application", args=[app.pk]), {**BE_ANSWERS, "employees": "650", "action": "submit"})
    app.refresh_from_db()
    assert app.answers["employees"] == 650
    assert app.edit_request == Application.EditRequest.NONE  # locked again after resubmitting


@pytest.mark.django_db
def test_declined_edit_keeps_report_locked(client, applicant, staff_client):
    app = _start(client)
    client.post(reverse("entries:application", args=[app.pk]), {**BE_ANSWERS, "action": "submit"})
    client.post(reverse("entries:request_edit", args=[app.pk]), {"reason": "Typo"})
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "decline_edit"})
    app.refresh_from_db()
    assert not app.can_edit
    assert app.can_request_edit  # can ask again


@pytest.mark.django_db
def test_staff_confirm_puts_report_in_pool(client, applicant, staff_client):
    app = _start(client)
    client.post(reverse("entries:application", args=[app.pk]), {**BE_ANSWERS, "action": "submit"})
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "confirm"})
    app.refresh_from_db()
    assert app.status == Application.Status.POOL
    page = client.get(reverse("entries:application", args=[app.pk])).content.decode()
    assert "In report pool" in page


@pytest.mark.django_db
def test_staff_reject_tells_applicant(client, applicant, staff_client):
    app = _start(client)
    client.post(reverse("entries:application", args=[app.pk]), {**BE_ANSWERS, "action": "submit"})
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "reject", "reason": "GSTIN not found"})
    app.refresh_from_db()
    assert app.status == Application.Status.REJECTED
    assert "not accepted" in client.get(reverse("entries:application", args=[app.pk])).content.decode()


@pytest.mark.django_db
def test_resubmitting_after_approved_edit_keeps_place_in_queue(client, applicant, staff_client):
    app = _start(client)
    client.post(reverse("entries:application", args=[app.pk]), {**BE_ANSWERS, "action": "submit"})
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "confirm"})
    client.post(reverse("entries:request_edit", args=[app.pk]), {"reason": "Typo"})
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "approve_edit"})
    client.post(reverse("entries:application", args=[app.pk]), {**BE_ANSWERS, "about": "Fixed", "action": "submit"})
    app.refresh_from_db()
    assert app.status == Application.Status.POOL  # not sent back to "staff checking"
    assert app.answers["about"] == "Fixed"


@pytest.mark.django_db
def test_applicant_cannot_use_staff_actions(client, applicant):
    app = _start(client)
    response = client.post(reverse("staff:report_action", args=[app.pk]), {"action": "approve_edit"})
    assert response.status_code == 302  # sent to log in as staff
    app.refresh_from_db()
    assert app.edit_request == Application.EditRequest.NONE
