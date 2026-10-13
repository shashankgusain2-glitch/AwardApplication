"""Rule 1: if an award uses blind judging, a judge cannot see who applied.

Planned: the judge workflow is not built yet (current focus is the applicant workflow).
"""
import pytest

pytestmark = pytest.mark.skip(reason="Planned: judge workflow not built yet")


def test_blind_award_hides_organisation_from_judge():
    ...


def test_blind_award_hides_uploaded_file_names():
    ...


def test_live_or_site_visit_rounds_are_not_blind():
    ...
