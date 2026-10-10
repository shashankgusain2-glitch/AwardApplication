"""Rule 1: if an award uses blind judging, a judge cannot see who applied."""
import pytest

pytestmark = pytest.mark.skip(reason="Not built yet - see docs/testing.md")


def test_blind_award_hides_identifying_answers_from_judge():
    ...


def test_blind_award_hides_organisation_in_judge_api_response():
    ...


def test_non_blind_award_shows_organisation_to_judge():
    ...


def test_live_round_two_is_not_blind():
    ...
