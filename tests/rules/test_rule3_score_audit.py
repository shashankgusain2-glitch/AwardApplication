"""
Rule 3: the system records who changed a score, and why.

A submitted score changes only with staff permission and a reason. Every
change is kept permanently (who, when, old and new value, reason), and
neither the record nor the audit log can be edited or deleted, not even
in bulk. Leaders oversee but never change scores.
"""
import pytest
from rest_framework.test import APIClient

from apps.assignments import services as assignments
from apps.audit.models import AuditLog
from apps.core.services import BusinessRuleError
from apps.evaluations import services as evaluations
from apps.evaluations.models import ScoreChange

from ..factories import ApplicationFactory, AwardFactory, JudgeFactory, LeaderFactory, ManagerFactory, StaffFactory


@pytest.fixture
def submitted(db):
    """A judge's submitted evaluation (approach 6, results 7); the award manager confirmed a change after staff."""
    award = AwardFactory(judges_per_report=1)
    staff, judge = StaffFactory(), JudgeFactory(awards=[award])
    manager = ManagerFactory(awards=[award])
    assignment = assignments.assign(ApplicationFactory(award=award), judge, by=staff)
    evaluation = evaluations.save(assignment, judge=judge, scores={"approach": 6, "results": 7}, submit=True)
    request = evaluations.request_change(evaluation, judge=judge, reason="Misread the results section")
    evaluations.decide_change(request, by=staff, approve=True)
    evaluations.decide_change(request, by=manager, approve=True)
    return {"evaluation": evaluation, "judge": judge, "staff": staff}


@pytest.mark.django_db
def test_changing_submitted_score_requires_permission_and_a_reason(submitted):
    evaluation, judge = submitted["evaluation"], submitted["judge"]
    with pytest.raises(BusinessRuleError, match="reason"):
        evaluations.change_scores(evaluation, judge=judge, scores={"results": 9}, reason="   ")
    with pytest.raises(BusinessRuleError, match="submitted"):        # no direct edit after submitting
        evaluations.save(evaluation.assignment, judge=judge, scores={"results": 9})
    assert not ScoreChange.objects.exists()


@pytest.mark.django_db
def test_score_change_records_who_when_old_and_new_value(submitted):
    evaluation, judge = submitted["evaluation"], submitted["judge"]
    evaluations.change_scores(evaluation, judge=judge, scores={"results": 9}, reason="Re-read the evidence")
    change = ScoreChange.objects.get()
    assert (change.criterion.key, change.old_score, change.new_score) == ("results", 7, 9)
    assert change.changed_by == judge and change.reason == "Re-read the evidence" and change.created_at
    evaluation.refresh_from_db()
    assert str(evaluation.total_score) == "7.80"                     # 6×40% + 9×60%
    assert AuditLog.objects.filter(action="score_change", entity_id=str(evaluation.pk)).exists()

    with pytest.raises(BusinessRuleError, match="permission"):       # the permission is used up
        evaluations.change_scores(evaluation, judge=judge, scores={"results": 10}, reason="Again")


@pytest.mark.django_db
def test_score_change_records_cannot_be_edited_or_deleted(submitted):
    evaluations.change_scores(submitted["evaluation"], judge=submitted["judge"], scores={"results": 9},
                              reason="Re-read the evidence")
    change = ScoreChange.objects.get()
    change.reason = "something else"
    with pytest.raises(ValueError):
        change.save()
    with pytest.raises(ValueError):
        change.delete()
    with pytest.raises(ValueError):                                  # bulk changes are blocked too
        ScoreChange.objects.filter(pk=change.pk).update(new_score=10)
    with pytest.raises(ValueError):
        ScoreChange.objects.all().delete()
    with pytest.raises(ValueError):
        AuditLog.objects.all().delete()
    with pytest.raises(ValueError):
        AuditLog.objects.update(changes={})
    assert ScoreChange.objects.get().reason == "Re-read the evidence"


@pytest.mark.django_db
def test_leader_cannot_change_scores(submitted):
    api = APIClient()
    api.force_authenticate(LeaderFactory())
    url = f"/api/v1/evaluations/{submitted['evaluation'].pk}/"
    assert api.patch(url, {"scores": {"results": 10}}, format="json").status_code == 403
    assert api.post(f"{url}change-scores/", {"scores": {"results": 10}, "reason": "I'm the boss"},
                    format="json").status_code == 403
    with pytest.raises(BusinessRuleError):
        evaluations.change_scores(submitted["evaluation"], judge=LeaderFactory(), scores={"results": 10},
                                  reason="I'm the boss")
    assert not ScoreChange.objects.exists()


@pytest.mark.django_db
def test_another_judge_cannot_change_these_scores(submitted):
    other = JudgeFactory()
    with pytest.raises(BusinessRuleError):
        evaluations.change_scores(submitted["evaluation"], judge=other, scores={"results": 10}, reason="Mine now")
    api = APIClient()
    api.force_authenticate(other)
    assert api.post(f"/api/v1/evaluations/{submitted['evaluation'].pk}/change-scores/",
                    {"scores": {"results": 10}, "reason": "x"}, format="json").status_code == 404
