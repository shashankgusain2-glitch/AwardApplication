"""Checks the app starts and the home page loads."""
import pytest


@pytest.mark.django_db
def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Awards Platform" in response.content
