"""Rule 2: a judge is never given an application they have a conflict with.

From the 12 Oct meeting: judges do NOT declare conflicts themselves
(they rarely would); staff check for conflicts when assigning.
Planned: judge assignment is not built yet.
"""
import pytest

pytestmark = pytest.mark.skip(reason="Planned: judge assignment not built yet")


def test_staff_flagged_conflict_blocks_assignment():
    ...


def test_conflict_matches_organisation_by_gstin():
    ...


def test_declined_report_returns_to_pool_without_conflicted_judge():
    ...
