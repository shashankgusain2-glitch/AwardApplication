import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.views import SESSION_KEY
from apps.entries.models import Organisation


def verify(client, email):
    """Go through email verification and return the response after the code step."""
    client.post(reverse("accounts:verify_email"), {"email": email})
    code = client.session[SESSION_KEY]["code"]
    return client.post(reverse("accounts:verify_code"), {"code": code})


@pytest.fixture
def applicant(client, db):
    """A logged-in applicant with a registered organisation."""
    verify(client, "priya@acme.example")
    user = get_user_model().objects.get(email="priya@acme.example")
    Organisation.objects.create(name="Acme Precision", gstin="27ABCDE1234F1Z5", holder_pan="PQRSX6789K", owner=user)
    return user


@pytest.fixture
def staff_client(client, db):
    """A second client logged in as staff."""
    from django.test import Client
    staff = Client()
    get_user_model().objects.create(email="staff@awards.example", username="staff@awards.example", is_staff=True)
    verify(staff, "staff@awards.example")
    return staff
