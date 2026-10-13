"""
Rule 2: a judge is never given an application they have a conflict with.

From the 12 Oct meeting: judges do NOT declare conflicts themselves (they
rarely would). Staff record conflicts, and the system refuses those judges.
"""
import pytest

pytestmark = pytest.mark.skip(reason="Not built yet - see docs/testing.md")


def test_judge_with_staff_recorded_conflict_is_not_suggested():
    ...


def test_staff_cannot_force_assign_a_judge_with_recorded_conflict():
    ...


def test_staff_recorded_conflict_matches_merged_duplicate_organisation():
    ...


def test_conflict_recorded_by_staff_after_assignment_removes_it_and_reassigns():
    ...
