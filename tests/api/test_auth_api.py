"""/api/v1/auth/: login (JWT with role claim), wrong role rejected, refresh, logout, register."""
import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.audit.models import AuditLog

from ..factories import PASSWORD, JudgeFactory, UserFactory

LOGIN = "/api/v1/auth/login/"


@pytest.mark.django_db
def test_login_returns_tokens_with_role_in_claims(api):
    judge = JudgeFactory()
    r = api.post(LOGIN, {"email": judge.email, "password": PASSWORD}, format="json")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True and body["errors"] is None
    claims = AccessToken(body["data"]["access"])
    assert claims["role"] == "judge" and claims["email"] == judge.email
    assert int(claims["user_id"]) == judge.id
    assert body["data"]["user"]["role"] == "judge"
    assert AuditLog.objects.filter(action="login", user=judge).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("sent_role", ["applicant", "staff", "leader"])
def test_wrong_role_login_is_rejected_on_the_backend(api, sent_role):
    judge = JudgeFactory()
    r = api.post(LOGIN, {"email": judge.email, "password": PASSWORD, "role": sent_role}, format="json")
    assert r.status_code == 401
    assert r.json()["success"] is False
    assert "access" not in str(r.json())


@pytest.mark.django_db
def test_matching_role_login_works(api):
    judge = JudgeFactory()
    r = api.post(LOGIN, {"email": judge.email, "password": PASSWORD, "role": "judge"}, format="json")
    assert r.status_code == 200


@pytest.mark.django_db
def test_wrong_password_gives_consistent_error(api):
    user = UserFactory()
    r = api.post(LOGIN, {"email": user.email, "password": "nope"}, format="json")
    assert r.status_code == 401
    body = r.json()
    assert body == {"success": False, "data": None, "message": "Incorrect email or password.", "errors": None}
    assert not AuditLog.objects.filter(action="login").exists()


@pytest.mark.django_db
def test_refresh_and_logout_blacklists_the_refresh_token(api):
    user = UserFactory()
    tokens = api.post(LOGIN, {"email": user.email, "password": PASSWORD}, format="json").json()["data"]
    refreshed = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["data"]["refresh"]

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.json()['data']['access']}")
    assert api.post("/api/v1/auth/logout/", {"refresh": new_refresh}, format="json").status_code == 200
    again = api.post("/api/v1/auth/refresh/", {"refresh": new_refresh}, format="json")
    assert again.status_code == 401


@pytest.mark.django_db
def test_register_creates_an_applicant_even_if_another_role_is_sent(api):
    r = api.post("/api/v1/auth/register/", {"email": "new@example.com", "name": "New Person",
                                            "password": "Strong-pass-123", "role": "leader",
                                            "organisation_name": "New Co", "gstin": "29qwert1234y1z9",
                                            "holder_pan": "QWERT1234Y"}, format="json")
    assert r.status_code == 201
    user = User.objects.get(email="new@example.com")
    assert user.role == "applicant"
    assert user.applicant_profile.organisation_name == "New Co"
    assert user.applicant_profile.gstin == "29QWERT1234Y1Z9"         # cleaned to upper case
    assert user.applicant_profile.holder_pan == "QWERT1234Y"
    assert AccessToken(r.json()["data"]["access"])["role"] == "applicant"


@pytest.mark.django_db
@pytest.mark.parametrize("payload,field", [
    ({"email": "taken@example.com"}, "email"),
    ({"password": "123"}, "password"),
    ({"email": "bad"}, "email"),
])
def test_register_validation(api, payload, field):
    UserFactory(email="taken@example.com")
    data = {"email": "x@example.com", "name": "X", "password": "Strong-pass-123", **payload}
    r = api.post("/api/v1/auth/register/", data, format="json")
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False
    assert field in str(body["errors"]) or field in body["message"].lower() or body["errors"]


@pytest.mark.django_db
def test_api_needs_a_token(api):
    r = api.get("/api/v1/applications/")
    assert r.status_code == 401
    assert r.json()["success"] is False


@pytest.mark.django_db
def test_jwt_works_on_protected_endpoint(api):
    user = UserFactory()
    access = api.post(LOGIN, {"email": user.email, "password": PASSWORD}, format="json").json()["data"]["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    r = api.get("/api/v1/users/me/")
    assert r.status_code == 200 and r.json()["data"]["email"] == user.email


@pytest.mark.django_db
def test_repeated_logins_are_rate_limited(api, monkeypatch):
    """Brute-force protection: the login endpoint is limited (10/minute by default)."""
    from django.core.cache import cache
    from rest_framework.throttling import ScopedRateThrottle
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"login": "3/minute"})
    cache.clear()
    codes = [api.post(LOGIN, {"email": "x@example.com", "password": "wrong"}, format="json").status_code
             for _ in range(4)]
    assert codes == [401, 401, 401, 429]
    cache.clear()
