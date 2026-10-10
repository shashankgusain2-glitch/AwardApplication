"""Rule 2: a judge is never given an application they have a conflict with."""
import pytest

pytestmark = pytest.mark.skip(reason="Not built yet - see docs/testing.md")


def test_conflicted_judge_is_not_suggested_for_assignment():
    ...


def test_staff_cannot_force_assign_conflicted_judge():
    ...


def test_conflict_matches_merged_duplicate_organisation():
    ...


def test_late_conflict_removes_assignment_and_reassigns():
    ...
