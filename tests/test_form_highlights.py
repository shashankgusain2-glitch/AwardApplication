"""
Applicants see exactly which answers are missing or wrong: the question is outlined in red
with the reason under it, its section is flagged in the side menu, and a summary at the top
links to every section that needs fixing.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.applications.models import Application
from apps.awards.models import FormVersion

from .factories import AwardFactory

QUESTIONS = [
    {"key": "team", "label": "Team names", "type": "text", "required": True, "section": "Team"},
    {"key": "city", "label": "City", "type": "text", "required": False, "section": "Team"},
    {"key": "story", "label": "What did you improve?", "type": "textarea", "required": True, "section": "Story"},
    {"key": "proof", "label": "Proof (PDF)", "type": "file", "required": False, "section": "Story"},
]


@pytest.fixture
def award():
    award = AwardFactory()
    FormVersion.objects.create(award=award, version=2, questions=QUESTIONS, published_at=timezone.now())
    return award


def _start(client, award):
    client.post(reverse("entries:form", args=[award.slug]), {"action": "start", "title": "Our entry"})
    return Application.objects.get(award=award)


def _post(client, award, section, action=None, **answers):
    data = {"section": section, "keys": list(answers)}
    data.update({f"q_{k}": v for k, v in answers.items()})
    if action:
        data["action"] = action
    else:
        data["go"] = section
    return client.post(reverse("entries:form", args=[award.slug]), data, follow=True)


@pytest.mark.django_db
def test_empty_fields_are_not_red_before_the_applicant_tries_to_submit(applicant_client, award):
    _start(applicant_client, award)
    page = applicant_client.get(reverse("entries:form", args=[award.slug])).content.decode()
    assert "field-invalid" not in page and "need your attention" not in page


@pytest.mark.django_db
def test_failed_submit_highlights_each_missing_question_and_its_section(applicant_client, award):
    _start(applicant_client, award)
    _post(applicant_client, award, "1", team="Asha, Ravi")
    response = _post(applicant_client, award, "2", action="submit")
    page = response.content.decode()

    assert response.redirect_chain[-1][0].endswith("?section=2")         # the first section with a problem
    assert "1 required question still needs an answer" in page
    assert '<div class="card field field-invalid">' in page
    assert 'id="q-story" name="q_story" aria-invalid="true" aria-describedby="err-story"' in page
    assert "⚠ This question is required" in page
    assert "⚠ 1 to fix" in page                                          # flagged in the side menu
    assert 'href="?section=2">Story (1)</a>' in page                    # summary links to the section
    assert Application.objects.get(award=award).status == "draft"


@pytest.mark.django_db
def test_highlight_goes_away_once_answered_and_the_form_then_submits(applicant_client, award):
    application = _start(applicant_client, award)
    _post(applicant_client, award, "1", action="submit")
    page = _post(applicant_client, award, "1", team="Asha").content.decode()
    assert 'id="q-team" name="q_team" type="text" aria-invalid' not in page   # answered: no longer red
    assert "⚠ 1 to fix" in page                                                # Story still needs work

    _post(applicant_client, award, "2", story="We cut scrap by 30%.")
    response = _post(applicant_client, award, "2", action="submit", story="We cut scrap by 30%.")
    application.refresh_from_db()
    assert application.status == "submitted"
    assert "field-invalid" not in response.content.decode()


@pytest.mark.django_db
def test_a_wrong_file_is_highlighted_and_the_other_answers_are_still_saved(applicant_client, award):
    application = _start(applicant_client, award)
    fake = SimpleUploadedFile("proof.pdf", b"this is not really a pdf", content_type="application/pdf")
    response = applicant_client.post(reverse("entries:form", args=[award.slug]),
                                     {"section": "2", "go": "3", "keys": ["story"], "q_story": "We cut scrap.",
                                      "f_proof": fake}, follow=True)
    page = response.content.decode()
    assert response.redirect_chain[-1][0].endswith("?section=2")         # stays on the page with the problem
    assert "a file couldn&#x27;t be uploaded" in page
    assert 'name="f_proof" type="file" aria-invalid="true"' in page
    assert "isn&#x27;t really a PDF file" in page
    application.refresh_from_db()
    assert application.content["story"] == "We cut scrap."
    assert not application.attachments.exists()


@pytest.mark.django_db
def test_wrong_organisation_details_are_highlighted(applicant_client):
    response = applicant_client.post(reverse("entries:organisation"),
                                     {"organisation_name": "", "gstin": "NOT-A-GSTIN"}, follow=True)
    page = response.content.decode()
    assert '<div class="field field-invalid">' in page
    assert 'id="f-gstin" name="gstin" aria-invalid="true"' in page
    assert 'id="f-organisation_name" name="organisation_name" type="text" value="" aria-invalid="true"' in page
