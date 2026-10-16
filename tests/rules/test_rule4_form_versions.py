"""
Rule 4: last year's applications still open correctly after questions change.

Staff edit questions in the form builder and the award manager publishes them as a NEW version.
The old version never changes, and applications keep the version they
were started on.
"""
import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.applications.models import Application
from apps.awards.models import FormVersion

from ..conftest import ACCOUNTS, seeded_client


def _editor_post(award, change):
    """The form-builder POST for the award's current questions, after `change(rows)` edits them."""
    rows = [dict(q) for q in award.current_form.questions]
    change(rows)
    data = {"rows": str(len(rows))}
    for n, q in enumerate(rows):
        data.update({f"q-{n}-key": q.get("key", ""), f"q-{n}-label": q.get("label", ""),
                     f"q-{n}-type": q.get("type", "text"), f"q-{n}-section": q.get("section", ""),
                     f"q-{n}-subsection": q.get("subsection", "")})
        for flag in ("required", "identifying", "remove"):
            if q.get(flag):
                data[f"q-{n}-{flag}"] = "on"
    return data


def _publish(award, change):
    """Staff send the new questions; the award manager approves (publishes) them."""
    staff = seeded_client("staff")
    response = staff.post(reverse("awards:form_edit", args=[award.slug]), _editor_post(award, change))
    if response.status_code == 302:
        seeded_client("manager").post(reverse("awards:form_review", args=[award.slug]), {"decision": "approve"})
    return response


@pytest.mark.django_db
def test_published_form_version_cannot_be_edited(seeded):
    version = FormVersion.objects.get(award__slug="kaizen", version=1)
    version.questions = []
    with pytest.raises(ValidationError):
        version.save()


@pytest.mark.django_db
def test_editing_questions_creates_new_version(seeded):
    application = Application.objects.filter(award__slug="kaizen").first()
    award = application.award
    before = list(award.current_form.questions)

    def change(rows):
        rows[3]["label"] = "What problem did you solve, and how did you measure it?"
        rows.append({"label": "What would you do next?", "type": "textarea", "section": "Next steps",
                     "required": True})

    assert _publish(award, change).status_code == 302
    award.refresh_from_db()
    assert award.current_form.version == 2
    assert award.current_form.questions[3]["label"].startswith("What problem did you solve")
    assert award.current_form.questions[-1]["key"] == "what_would_you_do_next"
    assert FormVersion.objects.get(award=award, version=1).questions == before          # untouched


@pytest.mark.django_db
def test_old_application_renders_with_its_own_form_version(seeded):
    award = Application.objects.get(applicant__email=ACCOUNTS["applicant"], award__slug="kaizen").award
    _publish(award, lambda rows: rows.append({"label": "A brand new question", "type": "text", "section": "New"}))
    page = seeded_client("applicant").get(reverse("entries:form", args=["kaizen"]), {"section": "99"})
    assert "Form version 1" in page.content.decode()
    assert "A brand new question" not in page.content.decode()


@pytest.mark.django_db
def test_removed_question_still_shows_on_old_application(seeded):
    application = Application.objects.get(applicant__email=ACCOUNTS["applicant"], award__slug="kaizen")
    removed = application.form_version.questions[3]

    def change(rows):
        rows[3]["remove"] = True
    _publish(application.award, change)
    application.award.refresh_from_db()
    assert removed["key"] not in {q["key"] for q in application.award.current_form.questions}

    section = [q.get("section") for q in application.form_version.questions]
    n = list(dict.fromkeys(section)).index(removed["section"]) + 1
    page = seeded_client("applicant").get(reverse("entries:form", args=["kaizen"]), {"section": n})
    assert removed["label"] in page.content.decode()


@pytest.mark.django_db
def test_new_applications_use_the_new_version(seeded):
    award = Application.objects.filter(award__slug="kaizen").first().award
    _publish(award, lambda rows: rows.append({"label": "Extra question", "type": "text", "section": "New"}))
    from django.test import Client
    c = Client()
    c.post(reverse("accounts:signup"), {"full_name": "New Co", "email": "newco@example.com",
                                        "password1": "Strong-pass-2026!x", "password2": "Strong-pass-2026!x"})
    c.post(reverse("entries:form", args=["kaizen"]), {"action": "start", "title": "New entry"})
    assert Application.objects.get(applicant__email="newco@example.com").form_version.version == 2


@pytest.mark.django_db
def test_editor_rejects_a_question_without_text_and_only_staff_can_publish(seeded):
    award = Application.objects.filter(award__slug="kaizen").first().award

    def change(rows):
        rows[0]["label"] = ""
    response = _publish(award, change)
    assert response.status_code == 200 and "needs a question text" in response.content.decode()
    assert FormVersion.objects.filter(award=award).count() == 1

    judge = seeded_client("judge")
    assert judge.post(reverse("awards:form_edit", args=[award.slug]), {"rows": "0"}).status_code == 403


@pytest.mark.django_db
def test_staff_add_many_questions_and_subcategories_in_one_version(seeded):
    award = Application.objects.filter(award__slug="kaizen").first().award
    old_count = len(award.current_form.questions)

    def change(rows):
        for n in range(1, 6):   # more than the old three blank rows
            rows.append({"label": f"Safety question {n}", "type": "text", "section": "Safety",
                         "subsection": "Before the change" if n <= 3 else "After the change"})
    assert _publish(award, change).status_code == 302
    award.refresh_from_db()
    new = award.current_form.questions[old_count:]
    assert [q["subsection"] for q in new] == ["Before the change"] * 3 + ["After the change"] * 2
    assert {q["section"] for q in new} == {"Safety"}

    editor = seeded_client("staff").get(reverse("awards:form_edit", args=[award.slug])).content.decode()
    assert 'value="Safety"' in editor and 'value="After the change"' in editor

    builder = seeded_client("staff").get(reverse("awards:form_builder", args=[award.slug])).content.decode()
    assert "Before the change" in builder and "After the change" in builder


@pytest.mark.django_db
def test_version_without_subcategories_still_opens_after_they_are_added(seeded):
    application = Application.objects.get(applicant__email=ACCOUNTS["applicant"], award__slug="kaizen")
    first = application.form_version.questions[0]

    def change(rows):
        rows[0]["subsection"] = "A brand new subcategory"
    _publish(application.award, change)
    application.refresh_from_db()
    assert application.form_version.version == 1 and "subsection" not in application.form_version.questions[0]

    page = seeded_client("applicant").get(reverse("entries:form", args=["kaizen"]), {"section": 1}).content.decode()
    assert first["label"] in page and "A brand new subcategory" not in page
