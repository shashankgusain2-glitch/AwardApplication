import pytest
from rest_framework.test import APIClient

from apps.assignments import services as assignments

from ..factories import ApplicationFactory, AwardFactory, JudgeFactory, ManagerFactory, StaffFactory


@pytest.fixture
def api():
    """A client with no login."""
    return APIClient()


@pytest.fixture
def as_user():
    """as_user(user) → an API client logged in as that user."""
    def make(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client
    return make


@pytest.fixture
def world(db):
    """
    One award, two judges, staff, and two reports from different applicants:
    judge A is assigned report 1, judge B is assigned report 2.
    """
    award = AwardFactory()
    staff = StaffFactory()
    manager = ManagerFactory(awards=[award])
    judge_a, judge_b = JudgeFactory(awards=[award]), JudgeFactory(awards=[award])
    report_1, report_2 = ApplicationFactory(award=award), ApplicationFactory(award=award)
    a1 = assignments.assign(report_1, judge_a, by=staff)
    a2 = assignments.assign(report_2, judge_b, by=staff)
    return {"award": award, "staff": staff, "manager": manager, "judge_a": judge_a, "judge_b": judge_b,
            "report_1": report_1, "report_2": report_2, "a1": a1, "a2": a2}
