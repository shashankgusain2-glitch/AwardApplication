"""Rule 3: the system records who changed a score, and why.

From the 12 Oct meeting: changing a graded report's score needs a reason
AND staff permission. Planned: judging is not built yet.
"""
import pytest

pytestmark = pytest.mark.skip(reason="Planned: judging not built yet")


def test_changing_a_graded_score_needs_staff_permission():
    ...


def test_score_change_records_who_when_old_new_and_reason():
    ...


def test_score_change_records_cannot_be_edited_or_deleted():
    ...
