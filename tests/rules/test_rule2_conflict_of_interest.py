"""
Rule 2: a judge is never given an application they have a conflict with.

From the 12 Oct meeting: judges do NOT declare conflicts themselves (they
rarely would). Staff record conflicts, and the system refuses those judges,
on the web pages and in the API alike.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.assignments import services as assignments
from apps.assignments.models import ConflictOfInterest, JudgeAssignment
from apps.core.overview import needing_judges
from apps.core.services import BusinessRuleError

from ..factories import ApplicationFactory, AwardFactory, JudgeFactory, StaffFactory


@pytest.fixture
def case(db):
    """One report; judge A has a staff-recorded conflict with its organisation, judge B doesn't."""
    award = AwardFactory(judges_per_report=1)
    report = ApplicationFactory(award=award)
    staff = StaffFactory()
    conflicted, clean = JudgeFactory(awards=[award]), JudgeFactory(awards=[award])
    assignments.record_conflict(judge=conflicted, profile=report.applicant.applicant_profile, by=staff,
                                reason="Former adviser")
    return {"report": report, "staff": staff, "conflicted": conflicted, "clean": clean}


@pytest.mark.django_db
def test_judge_with_staff_recorded_conflict_is_not_suggested(case):
    offered = assignments.eligible_judges(case["report"])
    assert case["conflicted"] not in offered and case["clean"] in offered

    staff_web = APIClient()
    staff_web.force_authenticate(case["staff"])
    ids = [j["id"] for j in staff_web.get(
        f"/api/v1/applications/{case['report'].pk}/eligible-judges/").json()["data"]]
    assert case["conflicted"].pk not in ids


@pytest.mark.django_db
def test_staff_cannot_force_assign_a_judge_with_recorded_conflict(case, client):
    with pytest.raises(BusinessRuleError, match="conflict"):
        assignments.assign(case["report"], case["conflicted"], by=case["staff"])

    api = APIClient()
    api.force_authenticate(case["staff"])
    response = api.post("/api/v1/assignments/", {"report": case["report"].pk, "judge": case["conflicted"].pk},
                        format="json")
    assert response.status_code == 400 and "conflict" in response.json()["message"]

    client.force_login(case["staff"])
    session = client.session
    session["role"] = "staff"
    session.save()
    client.post(reverse("awards:assign", args=[case["report"].pk]), {"judges": [case["conflicted"].pk]})
    assert not JudgeAssignment.objects.filter(judge=case["conflicted"]).exists()   # web form refused too


@pytest.mark.django_db
def test_judges_cannot_record_or_see_conflicts(case):
    api = APIClient()
    api.force_authenticate(case["clean"])
    assert api.get("/api/v1/conflicts/").status_code == 403
    response = api.post("/api/v1/conflicts/", {"judge": case["clean"].pk,
                                               "applicant_profile": case["report"].applicant.applicant_profile.pk},
                        format="json")
    assert response.status_code == 403
    assert ConflictOfInterest.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("conflict_on", ["main", "duplicate"])
def test_staff_recorded_conflict_matches_merged_duplicate_organisation(case, conflict_on):
    """The same company registered twice: once merged, a conflict with either record covers both."""
    from apps.accounts import duplicates
    from apps.accounts.models import DuplicateCandidate

    from ..factories import ApplicantProfileFactory

    main = case["report"].applicant.applicant_profile
    second = ApplicantProfileFactory(organisation_name=main.organisation_name.upper(),
                                     verification_status="pending")
    other_award = AwardFactory(judges_per_report=1)
    other_award.judge_panel.add(case["conflicted"].judge_profile, case["clean"].judge_profile)
    second_report = ApplicationFactory(applicant=second.user, award=other_award)
    if conflict_on == "duplicate":                  # move the conflict to the second record
        ConflictOfInterest.objects.update(applicant_profile=second)
    duplicates.scan(second)
    pair = DuplicateCandidate.objects.get()
    report_of = {main.pk: case["report"], second.pk: second_report}
    unprotected = report_of[main.pk if conflict_on == "duplicate" else second.pk]
    assert case["conflicted"] in assignments.eligible_judges(unprotected)   # missed before the merge

    duplicates.merge(pair, by=case["staff"], keep=main)

    assert case["conflicted"] not in assignments.eligible_judges(unprotected)
    with pytest.raises(BusinessRuleError, match="conflict"):
        assignments.assign(unprotected, case["conflicted"], by=case["staff"])


@pytest.mark.django_db
def test_conflict_recorded_after_assignment_withdraws_it_and_the_report_needs_a_judge_again(db):
    award = AwardFactory(judges_per_report=1)
    report = ApplicationFactory(award=award)
    staff = StaffFactory()
    judge, other = JudgeFactory(awards=[award]), JudgeFactory(awards=[award])
    assignment = assignments.assign(report, judge, by=staff)
    assert not any(row["report"] == report for row in needing_judges())

    assignments.record_conflict(judge=judge, profile=report.applicant.applicant_profile, by=staff,
                                reason="Found out later")
    assignment.refresh_from_db()
    assert assignment.status == JudgeAssignment.Status.DECLINED            # withdrawn at once
    assert any(row["report"] == report for row in needing_judges())         # staff see it needs a judge
    assert assignments.eligible_judges(report) == [other]                   # and only the clean judge is offered
