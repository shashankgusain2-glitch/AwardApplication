import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.accounts.views import SESSION_KEY
from apps.awards.models import Award
from apps.entries.models import Application, Organisation
from apps.judging.services import get_or_create_judge

User = get_user_model()


def verify(client, email):
    """Go through email verification and return the response after the code step."""
    client.post(reverse("accounts:verify_email"), {"email": email})
    code = client.session[SESSION_KEY]["code"]
    return client.post(reverse("accounts:verify_code"), {"code": code})


def make_report(name="Acme Precision", gstin="27ABCDE1234F1Z5", slug="business-excellence",
                status=Application.Status.POOL):
    """A report straight in the database (for staff and judge tests)."""
    owner = User.objects.create(email=f"{gstin}@example.com", username=f"{gstin}@example.com")
    org = Organisation.objects.create(name=name, gstin=gstin, holder_pan="PQRSX6789K", owner=owner)
    award = Award.objects.get(slug=slug)
    return Application.objects.create(organisation=org, award=award, form_version=award.current_form,
                                      answers={"about": "We make parts."}, status=status)


@pytest.fixture
def applicant(client, db):
    """A logged-in applicant with a registered organisation."""
    verify(client, "priya@acme.example")
    user = User.objects.get(email="priya@acme.example")
    Organisation.objects.create(name="Acme Precision", gstin="27ABCDE1234F1Z5", holder_pan="PQRSX6789K", owner=user)
    return user


@pytest.fixture
def staff_client(db):
    staff = Client()
    User.objects.create(email="staff@uec.example", username="staff@uec.example", is_staff=True)
    verify(staff, "staff@uec.example")
    return staff


@pytest.fixture
def judges(db):
    """Three judges on both events' panels, priority 1, 2, 3."""
    events = list(Award.objects.all())
    return [
        get_or_create_judge("kapoor@j.example", "Kapoor", "Quality", 1, 10, events),
        get_or_create_judge("rao@j.example", "Rao", "Operations", 2, 10, events),
        get_or_create_judge("iyer@j.example", "Iyer", "Finance", 3, 2, events),
    ]


def judge_client(judge):
    c = Client()
    c.force_login(judge.user)
    return c
