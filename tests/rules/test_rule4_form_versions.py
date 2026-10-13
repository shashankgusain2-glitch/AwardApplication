"""Rule 4: an award can change its questions; old applications still open correctly."""
import pytest
from django.urls import reverse

from apps.awards.models import Award, FormVersion
from apps.entries.models import Application


@pytest.fixture
def old_application(client, applicant):
    """A submitted Kaizen application on form version 1."""
    client.post(reverse("entries:start", args=["kaizen"]))
    app = Application.objects.get()
    client.post(reverse("entries:application", args=[app.pk]), {
        "team": "Line 4 Crew", "members": "4", "problem": "Slow changeover",
        "change": "Shadow board", "result": "48 to 19 minutes", "action": "submit",
    })
    return app


def _publish_v2():
    award = Award.objects.get(slug="kaizen")
    return FormVersion.objects.create(award=award, number=2, questions=[
        {"key": "team", "label": "Team name", "type": "text", "required": True},
        {"key": "saving", "label": "Money saved per year (₹)", "type": "number", "required": True},
    ])


@pytest.mark.django_db
def test_new_applications_use_the_newest_form(old_application):
    v2 = _publish_v2()
    assert Award.objects.get(slug="kaizen").current_form == v2


@pytest.mark.django_db
def test_old_application_keeps_its_form_version(old_application):
    _publish_v2()
    old_application.refresh_from_db()
    assert old_application.form_version.number == 1


@pytest.mark.django_db
def test_old_application_opens_with_its_own_questions_and_answers(client, old_application):
    _publish_v2()
    page = client.get(reverse("entries:application", args=[old_application.pk])).content.decode()
    assert "What was the problem?" in page          # v1 question, removed in v2
    assert "Slow changeover" in page                # its answer still shows
    assert "Money saved per year" not in page       # v2 question doesn't appear


@pytest.mark.skip(reason="Planned: block editing a published form (needs the form editor)")
def test_published_form_version_cannot_be_edited():
    ...
