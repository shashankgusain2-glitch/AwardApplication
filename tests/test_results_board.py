"""The results board (/results/): who sees which results, ranking, and re-evaluated entries."""
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.applications.models import Application
from apps.evaluations.models import Evaluation

from .conftest import login
from .factories import (
    ApplicantProfileFactory,
    ApplicationFactory,
    AwardFactory,
    JudgeFactory,
    LeaderFactory,
    StaffFactory,
)

S = Application.Status


def _decided(award, name, average, status):
    """A decided report whose two judges both gave `average`."""
    from apps.assignments.models import JudgeAssignment
    profile = ApplicantProfileFactory(organisation_name=name)
    report = ApplicationFactory(award=award, applicant=profile.user, status=status)
    for _ in range(2):
        judge = JudgeFactory(awards=[award])
        assignment = JudgeAssignment.objects.create(judge=judge, report=report, round=1,
                                                    status=JudgeAssignment.Status.COMPLETED)
        Evaluation.objects.create(assignment=assignment, status=Evaluation.Status.SUBMITTED, total_score=average,
                                  submitted_at=timezone.now())
    return report


@pytest.fixture
def board(db):
    award = AwardFactory(name="Kaizen")
    other = AwardFactory(name="Energy")
    staff = StaffFactory(awards=[award])
    reports = {
        "gold": _decided(award, "Gold Ltd", 9, S.APPROVED),
        "silver": _decided(award, "Silver Ltd", 8, S.APPROVED),
        "lost": _decided(award, "Lost Ltd", 4, S.REJECTED),
        "energy": _decided(other, "Energy Ltd", 7, S.APPROVED),
    }
    ApplicationFactory(award=award, status=S.SCORED)                 # not decided yet: not on the board
    return {"award": award, "other": other, "staff": staff, **reports}


def _page(client, user, award):
    user.set_password("Test-pass-2026!")
    user.save()
    login(client, user.email, "Test-pass-2026!")
    response = client.get(reverse("core:results") + f"?award={award.slug}")
    assert response.status_code == 200
    return response.content.decode()


def test_staff_see_the_full_ranking_of_their_awards(board, client):
    page = _page(client, board["staff"], board["award"])
    assert page.index("Gold Ltd") < page.index("Silver Ltd") < page.index("Lost Ltd")
    assert "#1" in page and "#2" in page and "Not successful" in page and "Full ranking" in page
    assert "Energy" not in page                                       # not on that award's team


def test_leaders_see_every_award(board, client):
    page = _page(client, LeaderFactory(), board["other"])
    assert "Energy Ltd" in page and "Kaizen" in page


def test_applicants_see_successful_entries_and_their_own_result(board, client):
    lost = board["lost"]
    page = _page(client, lost.applicant, board["award"])
    assert "Gold Ltd" in page and "Lost Ltd" in page and ">You<" in page
    assert "Ask for re-evaluation" in page

    page = _page(client, board["gold"].applicant, board["award"])
    assert "Lost Ltd" not in page                                    # someone else's unsuccessful result


def test_entries_declined_at_the_staff_check_have_no_result(board, client):
    from apps.applications import services as applications
    declined = ApplicationFactory(award=board["award"], status=S.REJECTED)     # never judged
    assert not applications.can_request_reevaluation(declined)
    page = _page(client, declined.applicant, board["award"])
    assert declined.reference not in page and "Ask for re-evaluation" not in page


def test_judges_see_successful_entries_only(board, client):
    judge = JudgeFactory(awards=[board["award"]])
    page = _page(client, judge, board["award"])
    assert "Gold Ltd" in page and "Silver Ltd" in page and "Lost Ltd" not in page


def test_every_role_has_the_results_link(board, client):
    for user in (board["lost"].applicant, JudgeFactory(), board["staff"], LeaderFactory()):
        page = _page(client, user, board["award"])
        assert f'href="{reverse("core:results")}"' in page


def test_logged_out_visitors_are_sent_to_login(client):
    response = client.get(reverse("core:results"))
    assert response.status_code == 302 and reverse("accounts:login") in response["Location"]
