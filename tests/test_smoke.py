"""The public pages load, and private pages send you to email verification."""
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_shows_the_two_events(client):
    page = client.get(reverse("core:home")).content.decode()
    assert "Business Excellence Award" in page
    assert "Kaizen Competition" in page


@pytest.mark.django_db
def test_verify_email_page_loads(client):
    assert client.get(reverse("accounts:verify_email")).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["entries:events", "entries:register", "entries:staff"])
def test_private_pages_need_verification(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 302
    assert reverse("accounts:verify_email") in response["Location"]
