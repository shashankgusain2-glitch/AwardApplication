"""
Shared test helpers: one logged-in client per role.

Clients log in through the real login page, so every test
also goes through the role check and the session that stores the role.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

PASSWORD = "Test-pass-2026!"

# Matches the demo data: Priya owns the sample applications, Kapoor has most
# assignments, Rao has one (K-0012).
ACCOUNTS = {
    "applicant": "priya@acme.example",
    "staff": "staff@awards.example",
    "judge": "kapoor@judges.example",
    "judge2": "rao@judges.example",
    "leader": "leader@awards.example",
}

# Which role can open which part of the site.
APP_ROLE = {"entries": "applicant", "judging": "judge", "awards": "staff", "dashboard": "leader"}


def make_user(email, role, password=PASSWORD, **extra):
    User = get_user_model()
    user = User(email=email, role=role, **extra)
    user.set_password(password)
    user.save()
    return user


def login(client, email, password=PASSWORD):
    return client.post(reverse("accounts:login"), {"email": email, "password": password})


def logged_in(key):
    role = "judge" if key == "judge2" else key
    make_user(ACCOUNTS[key], role)
    c = Client()
    response = login(c, ACCOUNTS[key])
    assert response.status_code == 302, "test login failed"
    return c


@pytest.fixture
def applicant_client(db):
    return logged_in("applicant")


@pytest.fixture
def staff_client(db):
    return logged_in("staff")


@pytest.fixture
def judge_client(db):
    return logged_in("judge")


@pytest.fixture
def judge2_client(db):
    return logged_in("judge2")


@pytest.fixture
def leader_client(db):
    return logged_in("leader")


@pytest.fixture
def client_for(db):
    """client_for("entries:dashboard") → a client logged in with the role that page needs."""
    made = {}

    def get(url_name):
        app = url_name.split(":")[0]
        role = APP_ROLE.get(app)
        if role is None:
            return Client()                      # public page
        if role not in made:
            made[role] = logged_in(role)
        return made[role]
    return get


@pytest.fixture(autouse=True)
def fast_password_hashing(settings, request):
    """
    Real hashing (PBKDF2, 1 million rounds) makes every test login slow.
    Tests use a fast hasher, except tests marked @pytest.mark.real_hashing.
    """
    if "real_hashing" in request.keywords:
        settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
    else:
        settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def seeded(db, monkeypatch):
    """The full demo data (python manage.py seed_data); every demo account uses the test PASSWORD."""
    from io import StringIO

    from django.core.management import call_command
    monkeypatch.setenv("DEMO_PASSWORD", PASSWORD)
    call_command("seed_data", stdout=StringIO())


def seeded_client(key):
    """A client logged in (through the real login page) as one of the seeded demo accounts."""
    c = Client()
    assert login(c, ACCOUNTS[key]).status_code == 302, f"demo login failed for {key}"
    return c
