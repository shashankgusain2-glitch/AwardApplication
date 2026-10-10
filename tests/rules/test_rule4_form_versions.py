"""Rule 4: last year's applications still open correctly after questions change."""
import pytest

pytestmark = pytest.mark.skip(reason="Not built yet - see docs/testing.md")


def test_published_form_version_cannot_be_edited():
    ...


def test_editing_questions_creates_new_version():
    ...


def test_old_application_renders_with_its_own_form_version():
    ...


def test_removed_question_still_shows_on_old_application():
    ...
