"""
How much of a report has been judged: one bar per report (all its judges together)
for staff and leaders, and one bar per report for each judge (their own part).
"""
import pytest
from django.urls import reverse

from apps.assignments import services as assignments
from apps.evaluations import services as evaluations

from .conftest import ACCOUNTS, login, make_user
from .factories import ApplicationFactory, AwardFactory, JudgeFactory, StaffFactory


@pytest.fixture
def half_judged():
    """A report needing 2 judges on 2 criteria: judge A saved 1 score, judge B hasn't started."""
    award = AwardFactory(judges_per_report=2)
    report = ApplicationFactory(award=award)
    a, b = JudgeFactory(awards=[award]), JudgeFactory(awards=[award])
    staff = StaffFactory()
    first = assignments.assign(report, a, by=staff)
    second = assignments.assign(report, b, by=staff)
    for assignment, judge in ((first, a), (second, b)):
        assignments.start_review(assignment, judge=judge)
    evaluations.save(first, judge=a, scores={"approach": 7})
    return report, first, second


@pytest.mark.django_db
def test_progress_counts_saved_scores_across_all_judges(half_judged):
    report, first, second = half_judged
    assert evaluations.assignment_progress(first) == 50
    assert evaluations.assignment_progress(second) == 0
    assert evaluations.report_progress(report) == 25               # 1 of the 4 scores the report needs

    evaluations.save(second, judge=second.judge, scores={"approach": 6, "results": 8}, submit=True)
    assert evaluations.assignment_progress(second) == 100
    assert evaluations.report_progress(report) == 75


@pytest.mark.django_db
def test_judges_still_to_be_assigned_count_as_not_judged():
    award = AwardFactory(judges_per_report=3)
    report = ApplicationFactory(award=award)
    judge = JudgeFactory(awards=[award])
    assignment = assignments.assign(report, judge, by=StaffFactory())
    assignments.start_review(assignment, judge=judge)
    evaluations.save(assignment, judge=judge, scores={"approach": 7, "results": 7}, submit=True)
    assert evaluations.report_progress(report) == 33               # 1 of 3 judges' work done


@pytest.mark.django_db
def test_a_declined_judge_counts_for_nothing(half_judged):
    report, first, second = half_judged
    second.status = "declined"
    second.save()
    assert evaluations.report_progress(report) == 25               # still needs a second judge


@pytest.mark.django_db
def test_staff_see_the_report_bar_and_the_judge_sees_their_own(half_judged, client):
    report, first, _ = half_judged
    make_user(ACCOUNTS["staff"], "staff")
    login(client, ACCOUNTS["staff"])
    entries = client.get(reverse("awards:entries")).content.decode()
    assert "25% judged" in entries
    assign_page = client.get(reverse("awards:assign", args=[report.pk])).content.decode()
    assert "25% of the report judged" in assign_page

    first.judge.set_password("Test-pass-2026!")
    first.judge.save()
    client.post(reverse("accounts:logout"))
    login(client, first.judge.email)
    mine = client.get(reverse("judging:assignments")).content.decode()
    assert "50% judged by you" in mine
