"""
Changes after submitting need two confirmations: programme staff on the award check the
request, then it is confirmed: an applicant's edit by the award's manager (a leader only if
the award has no manager), a judge's score change by a leader. Nothing changes until the
final yes, nobody can skip a step, and "late" requests are blocked:
  - an applicant can only edit a submitted report before any judge starts on it;
  - a judge can only change a submitted score until the result is decided.
"""
import pytest

from apps.applications import services as applications
from apps.assignments import services as assignments
from apps.core.services import BusinessRuleError
from apps.evaluations import services as evaluations
from apps.evaluations.models import ScoreChange
from apps.notifications.models import Notification

from .factories import (
    ApplicationFactory,
    AwardFactory,
    JudgeFactory,
    LeaderFactory,
    ManagerFactory,
    StaffFactory,
    decide,
)


@pytest.fixture
def people():
    award = AwardFactory(judges_per_report=1)
    return {"award": award, "staff": StaffFactory(), "leader": LeaderFactory(), "judge": JudgeFactory(awards=[award]),
            "manager": ManagerFactory(awards=[award])}


# --- Applicant: edit a submitted report ----------------------------------------------------

@pytest.mark.django_db
def test_edit_needs_staff_then_the_award_manager_and_only_then_takes_effect(people):
    report = ApplicationFactory(award=people["award"])
    applications.request_edit(report, by=report.applicant, reason="Wrong turnover figure")
    applications.decide_edit(report, by=people["staff"], allow=True, note="Small fix")
    report.refresh_from_db()
    assert not report.edit_allowed and report.requests.get().status == "staff_approved"
    to_manager = Notification.objects.filter(user=people["manager"]).latest("created_at")
    assert "waiting for you to confirm" in to_manager.message
    assert not Notification.objects.filter(user=people["leader"]).exists()          # leaders aren't involved
    assert "passed it to the award manager" in Notification.objects.filter(
        user=report.applicant).latest("created_at").message

    with pytest.raises(BusinessRuleError, match="needs the award manager"):
        applications.decide_edit(report, by=people["leader"], allow=True)
    applications.decide_edit(report, by=people["manager"], allow=True)
    report.refresh_from_db()
    assert report.edit_allowed and not report.edit_requested
    message = Notification.objects.filter(user=report.applicant).latest("created_at").message
    assert "approved by the award manager" in message and "You can now change your application" in message


@pytest.mark.django_db
def test_without_an_award_manager_the_staff_check_decides_and_leaders_never_hear(people):
    people["award"].manager = None
    people["award"].save()
    report = ApplicationFactory(award=people["award"])
    applications.request_edit(report, by=report.applicant, reason="Wrong turnover figure")
    with pytest.raises(BusinessRuleError, match="staff check this request first"):
        applications.decide_edit(report, by=people["leader"], allow=True)
    applications.decide_edit(report, by=people["staff"], allow=True)
    report.refresh_from_db()
    assert report.edit_allowed and report.requests.get().status == "approved"
    assert "approved by programme staff" in Notification.objects.filter(
        user=report.applicant).latest("created_at").message
    assert not Notification.objects.filter(user=people["leader"]).exists()


@pytest.mark.django_db
def test_edit_requests_are_told_to_staff_only(people):
    report = ApplicationFactory(award=people["award"])
    applications.request_edit(report, by=report.applicant, reason="Wrong turnover figure")
    told = set(Notification.objects.filter(kind="request").values_list("user", flat=True))
    assert told == {people["staff"].pk}                     # not the manager (until staff pass it on), not leaders


@pytest.mark.django_db
def test_staff_refusal_ends_it_and_the_applicant_sees_why(people):
    report = ApplicationFactory(award=people["award"])
    applications.request_edit(report, by=report.applicant, reason="Typo")
    applications.decide_edit(report, by=people["staff"], allow=False, note="Typos don't affect scoring.")
    report.refresh_from_db()
    assert not report.edit_allowed and not report.edit_requested
    message = Notification.objects.filter(user=report.applicant).latest("created_at").message
    assert "refused" in message and "Typos don't affect scoring." in message
    with pytest.raises(BusinessRuleError, match="already been decided"):
        applications.decide_request(report.requests.get(), by=people["leader"], approve=True)


@pytest.mark.django_db
def test_nobody_skips_a_step(people):
    report = ApplicationFactory(award=people["award"])
    applications.request_edit(report, by=report.applicant, reason="Wrong figure")
    for wrong in (people["leader"], people["manager"]):     # the manager can't check what they then confirm
        with pytest.raises(BusinessRuleError, match="staff check this request first"):
            applications.decide_edit(report, by=wrong, allow=True)
    applications.decide_edit(report, by=people["staff"], allow=True)
    with pytest.raises(BusinessRuleError, match="needs the award manager"):
        applications.decide_edit(report, by=StaffFactory(), allow=True)


@pytest.mark.django_db
def test_an_open_edit_request_closes_when_a_judge_starts(people):
    report = ApplicationFactory(award=people["award"])
    assignment = assignments.assign(report, people["judge"], by=people["staff"])   # assigned, not started: fine
    applications.request_edit(report, by=report.applicant, reason="Wrong figure")
    assert Notification.objects.filter(user=people["staff"], is_read=False).exists()
    assignments.start_review(assignment, judge=people["judge"])                     # judge starts meanwhile

    req = report.requests.get()
    assert req.status == "declined" and "started judging" in req.decision_note
    assert "closed because a judge has started judging" in Notification.objects.filter(
        user=report.applicant).latest("created_at").message
    assert not Notification.objects.filter(user=people["staff"], is_read=False,
                                           message__contains="Edit after submitting").exists()   # reminder cleared
    with pytest.raises(BusinessRuleError, match="no edit request waiting|hasn't asked"):
        applications.decide_edit(report, by=people["staff"], allow=True)

    report.refresh_from_db()
    assert not report.edit_requested
    with pytest.raises(BusinessRuleError, match="Judging has started"):
        applications.request_edit(report, by=report.applicant, reason="Another try")


@pytest.mark.django_db
def test_judges_wait_while_the_applicant_is_allowed_to_edit(people):
    report = ApplicationFactory(award=people["award"])
    assignment = assignments.assign(report, people["judge"], by=people["staff"])
    applications.request_edit(report, by=report.applicant, reason="Wrong figure")
    applications.decide_edit(report, by=people["staff"], allow=True)
    applications.decide_edit(report, by=people["manager"], allow=True)
    with pytest.raises(BusinessRuleError, match="submit it again"):
        assignments.start_review(assignment, judge=people["judge"])
    report.refresh_from_db()
    applications.submit(report, by=report.applicant)
    assignments.start_review(assignment, judge=people["judge"])                     # fine once resubmitted


# --- Judge: change a submitted score ------------------------------------------------------

def _scored(people):
    report = ApplicationFactory(award=people["award"])
    assignment = assignments.assign(report, people["judge"], by=people["staff"])
    evaluation = evaluations.save(assignment, judge=people["judge"], scores={"approach": 6, "results": 7},
                                  submit=True)
    return report, evaluation


@pytest.mark.django_db
def test_score_change_needs_staff_then_the_award_manager(people):
    report, evaluation = _scored(people)
    req = evaluations.request_change(evaluation, judge=people["judge"], reason="Misread the results")
    with pytest.raises(BusinessRuleError, match="staff check this request first"):
        evaluations.decide_change(req, by=people["leader"], approve=True)
    evaluations.decide_change(req, by=people["staff"], approve=True, note="Fair")
    with pytest.raises(BusinessRuleError, match="Ask for permission"):           # staff alone isn't enough
        evaluations.change_scores(evaluation, judge=people["judge"], scores={"results": 9}, reason="Misread")
    with pytest.raises(BusinessRuleError, match="needs the award manager"):      # leaders aren't involved
        evaluations.decide_change(req, by=people["leader"], approve=True)
    assert not Notification.objects.filter(user=people["leader"]).exists()
    evaluations.decide_change(req, by=people["manager"], approve=True)
    evaluations.change_scores(evaluation, judge=people["judge"], scores={"results": 9}, reason="Misread")
    assert ScoreChange.objects.get().new_score == 9


@pytest.mark.django_db
def test_score_change_is_blocked_once_the_result_is_decided(people):
    report, evaluation = _scored(people)
    req = evaluations.request_change(evaluation, judge=people["judge"], reason="Misread")
    evaluations.decide_change(req, by=people["staff"], approve=True)
    evaluations.decide_change(req, by=people["manager"], approve=True)
    report.refresh_from_db()
    decide(report)                                                    # result decided meanwhile
    with pytest.raises(BusinessRuleError, match="already been decided"):
        evaluations.change_scores(evaluation, judge=people["judge"], scores={"results": 9}, reason="Misread")

    other_report, other = _scored({**people, "judge": JudgeFactory(awards=[people["award"]])})
    decide(other_report, successful=False)
    with pytest.raises(BusinessRuleError, match="already been decided"):
        evaluations.request_change(other, judge=other.assignment.judge, reason="Too late")


@pytest.mark.django_db
def test_a_waiting_score_change_cannot_be_approved_after_the_result(people):
    report, evaluation = _scored(people)
    req = evaluations.request_change(evaluation, judge=people["judge"], reason="Misread")
    report.refresh_from_db()
    decide(report)
    with pytest.raises(BusinessRuleError, match="Refuse this request"):
        evaluations.decide_change(req, by=people["staff"], approve=True)
    evaluations.decide_change(req, by=people["staff"], approve=False, note="Result already decided")
    assert "Result already decided" in Notification.objects.filter(
        user=people["judge"]).latest("created_at").message
