"""
R2 document upload: applicants attach PDF/JPG/PNG evidence (up to 10 MB) to
file questions; only the owner, staff, leaders and the assigned judges can
download it; blind rounds give judges a neutral file name.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.applications import services
from apps.applications.models import Attachment
from apps.assignments import services as assignment_services
from apps.awards.models import FormVersion

from .conftest import PASSWORD
from .factories import (
    QUESTIONS,
    ApplicantProfileFactory,
    AwardFactory,
    JudgeFactory,
    LeaderFactory,
    StaffFactory,
)

PDF = b"%PDF-1.4\n% test file\n"


def pdf(name="acme-strategy.pdf", body=PDF):
    return SimpleUploadedFile(name, body, content_type="application/pdf")


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path   # uploaded files go to a temporary folder


@pytest.fixture
def setup(db):
    """An award whose current form (v2) has a required file question; one applicant's draft."""
    award = AwardFactory()
    questions = QUESTIONS + [{"key": "evidence", "label": "Evidence (PDF)", "type": "file", "required": True,
                              "identifying": False, "section": "Evidence"}]
    FormVersion.objects.create(award=award, version=2, questions=questions, published_at=timezone.now())
    applicant = ApplicantProfileFactory().user
    draft = services.create_draft(applicant=applicant, award=award, title="Entry")
    return {"award": award, "applicant": applicant, "draft": draft}


def web(user):
    c = Client()
    c.force_login(user)
    session = c.session
    session["role"] = user.role
    session.save()
    return c


def api(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


# --- Uploading -------------------------------------------------------------------

@pytest.mark.django_db
def test_applicant_uploads_a_pdf_from_the_form(setup):
    url = reverse("entries:form", args=[setup["award"].slug])
    web(setup["applicant"]).post(url, {"section": "2", "keys": ["evidence"], "f_evidence": pdf(), "go": "2"})
    attachment = Attachment.objects.get(application=setup["draft"])
    assert attachment.original_name == "acme-strategy.pdf" and attachment.content_type == "application/pdf"
    setup["draft"].refresh_from_db()
    assert setup["draft"].content["evidence"] == "acme-strategy.pdf"      # the required question is answered


@pytest.mark.django_db
@pytest.mark.parametrize("upload,message", [
    (SimpleUploadedFile("tool.exe", b"MZ...", content_type="application/octet-stream"), "PDF, JPG or PNG"),
    (SimpleUploadedFile("fake.pdf", b"MZ not really a pdf", content_type="application/pdf"), "really a PDF"),
    (SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf"), "empty"),
])
def test_bad_files_are_refused_with_a_clear_message(setup, upload, message):
    response = web(setup["applicant"]).post(reverse("entries:form", args=[setup["award"].slug]),
                                            {"section": "2", "f_evidence": upload}, follow=True)
    assert message in response.content.decode()
    assert not Attachment.objects.exists()


@pytest.mark.django_db
def test_files_over_10_mb_are_refused(setup):
    big = pdf(body=PDF + b"0" * (10 * 1024 * 1024))
    response = api(setup["applicant"]).post(f"/api/v1/applications/{setup['draft'].pk}/attachments/",
                                            {"question_key": "evidence", "file": big}, format="multipart")
    assert response.status_code == 400 and "10 MB" in response.json()["message"]


@pytest.mark.django_db
def test_uploading_again_replaces_the_file(setup):
    from apps.applications import files
    first = files.attach(setup["draft"], by=setup["applicant"], question_key="evidence", upload=pdf("one.pdf"))
    files.attach(setup["draft"], by=setup["applicant"], question_key="evidence", upload=pdf("two.pdf"))
    assert list(Attachment.objects.values_list("original_name", flat=True)) == ["two.pdf"]
    assert not first.file.storage.exists(first.file.name)                 # the old file is deleted too


@pytest.mark.django_db
def test_only_file_questions_take_files_and_only_while_editable(setup):
    client = api(setup["applicant"])
    url = f"/api/v1/applications/{setup['draft'].pk}/attachments/"
    assert client.post(url, {"question_key": "story", "file": pdf()}, format="multipart").status_code == 400
    assert client.post(url, {"question_key": "evidence", "file": pdf()}, format="multipart").status_code == 201
    setup["draft"].refresh_from_db()   # the upload changed it in the database
    services.update(setup["draft"], by=setup["applicant"], content={"org": "X", "city": "Y", "story": "Z"})
    services.submit(setup["draft"], by=setup["applicant"])
    response = client.post(url, {"question_key": "evidence", "file": pdf()}, format="multipart")
    assert response.status_code == 400 and "submitted" in response.json()["message"]


@pytest.mark.django_db
def test_other_roles_and_applicants_cannot_upload(setup):
    url = f"/api/v1/applications/{setup['draft'].pk}/attachments/"
    assert api(StaffFactory()).post(url, {"question_key": "evidence", "file": pdf()},
                                    format="multipart").status_code == 403
    other = ApplicantProfileFactory().user
    assert api(other).post(url, {"question_key": "evidence", "file": pdf()}, format="multipart").status_code == 404


# --- Downloading -------------------------------------------------------------------

@pytest.fixture
def submitted(setup):
    """The draft with a file, submitted, and assigned to judge A (judge B is on the panel but not assigned)."""
    from apps.applications import files
    attachment = files.attach(setup["draft"], by=setup["applicant"], question_key="evidence", upload=pdf())
    services.update(setup["draft"], by=setup["applicant"], content={"org": "X", "city": "Y", "story": "Z"})
    services.submit(setup["draft"], by=setup["applicant"])
    judge_a, judge_b = JudgeFactory(awards=[setup["award"]]), JudgeFactory(awards=[setup["award"]])
    assignment = assignment_services.assign(setup["draft"], judge_a, by=StaffFactory())
    return {**setup, "attachment": attachment, "judge_a": judge_a, "judge_b": judge_b, "assignment": assignment}


def _download(client, attachment):
    return client.get(reverse("applications:download", args=[attachment.pk]))


@pytest.mark.django_db
def test_owner_staff_leader_and_assigned_judge_can_download(submitted):
    a = submitted["attachment"]
    for user in (submitted["applicant"], StaffFactory(), LeaderFactory(), submitted["judge_a"]):
        response = _download(web(user), a)
        assert response.status_code == 200, user.role
        assert b"".join(response.streaming_content) == PDF


@pytest.mark.django_db
def test_everyone_else_gets_404(submitted):
    a = submitted["attachment"]
    assert _download(web(ApplicantProfileFactory().user), a).status_code == 404     # another applicant
    assert _download(web(submitted["judge_b"]), a).status_code == 404               # judge not assigned
    assignment_services.decline(submitted["assignment"], judge=submitted["judge_a"])
    assert _download(web(submitted["judge_a"]), a).status_code == 404               # declined: no access
    assert _download(Client(), a).status_code == 302                                 # logged out → login


@pytest.mark.django_db
def test_blind_round_gives_judges_a_neutral_file_name(submitted):
    award = submitted["award"]
    award.blind_judging = True
    award.save()
    response = _download(web(submitted["judge_a"]), submitted["attachment"])
    assert "acme" not in response["Content-Disposition"]
    assert f"{submitted['draft'].reference}-evidence.pdf" in response["Content-Disposition"]
    staff = _download(web(StaffFactory()), submitted["attachment"])
    assert "acme-strategy.pdf" in staff["Content-Disposition"]                       # staff see the real name


@pytest.mark.django_db
def test_judge_grading_page_links_the_file(submitted):
    page = web(submitted["judge_a"]).get(reverse("judging:score", args=[submitted["assignment"].pk]))
    assert reverse("applications:download", args=[submitted["attachment"].pk]) in page.content.decode()


@pytest.mark.django_db
def test_api_upload_and_download(setup):
    client = api(setup["applicant"])
    response = client.post(f"/api/v1/applications/{setup['draft'].pk}/attachments/",
                           {"question_key": "evidence", "file": pdf()}, format="multipart")
    assert response.status_code == 201
    data = response.json()["data"]
    assert "file" not in data                                                       # no raw storage path
    download = client.get(data["download_url"])
    assert download.status_code == 200 and b"".join(download.streaming_content) == PDF
    assert api(ApplicantProfileFactory().user).get(data["download_url"]).status_code == 404


@pytest.mark.django_db
def test_web_login_still_needed(setup):
    c = Client()
    c.post(reverse("accounts:login"), {"email": setup["applicant"].email, "password": PASSWORD})
    assert c.get(reverse("entries:form", args=[setup["award"].slug])).status_code == 200
