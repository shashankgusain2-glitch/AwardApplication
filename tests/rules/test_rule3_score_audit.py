"""
Rule 3: the system records who changed a score, and why.

From the 12 Oct meeting: changing a graded report needs staff permission
and a reason for the change.
"""
import pytest

from apps.judging import services
from apps.judging.models import ScoreChange, ScoreChangeRequest

from ..conftest import make_report


@pytest.fixture
def graded(judges):
    app = make_report(slug="kaizen")
    services.assign(app, [judges[0]], None)
    a = app.assignments.get()
    services.accept(a)
    services.save_scores(a, {"problem": 8, "cause": 7, "change": 8, "result": 9}, {}, submit=True)
    return a


def _allow(assignment):
    services.request_change(assignment, "Rethink")
    services.decide_change_request(assignment.change_requests.get(), True, None)
    assignment.refresh_from_db()


@pytest.mark.django_db
def test_changing_a_graded_score_needs_staff_permission(graded):
    with pytest.raises(services.RuleError):
        services.change_scores(graded, {"result": 5}, "Rethink", graded.judge.user)


@pytest.mark.django_db
def test_change_needs_a_reason(graded):
    _allow(graded)
    with pytest.raises(services.RuleError):
        services.change_scores(graded, {"result": 5}, "   ", graded.judge.user)


@pytest.mark.django_db
def test_score_change_records_who_when_old_new_and_reason(graded):
    _allow(graded)
    services.change_scores(graded, {"result": 5, "problem": 8}, "Result is one month only", graded.judge.user)
    change = ScoreChange.objects.get()  # only the part that changed is recorded
    assert (change.criterion, change.old_value, change.new_value) == ("result", 9, 5)
    assert change.reason == "Result is one month only"
    assert change.changed_by == graded.judge.user
    assert change.changed_at is not None
    assert change.request.status == ScoreChangeRequest.Status.USED


@pytest.mark.django_db
def test_score_change_records_cannot_be_edited_or_deleted(graded):
    _allow(graded)
    services.change_scores(graded, {"result": 5}, "Reason", graded.judge.user)
    change = ScoreChange.objects.get()
    change.new_value = 10
    with pytest.raises(ValueError):
        change.save()
    with pytest.raises(ValueError):
        change.delete()
