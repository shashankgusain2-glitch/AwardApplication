"""
Object-level security and role rules (the cases the roadmap requires):
- a judge cannot read another judge's assignment
- an applicant cannot read another applicant's report
- only staff/leaders can assign
- a judge can score only assigned reports
"""
import pytest

from apps.assignments.models import JudgeAssignment

from ..factories import ApplicationFactory, JudgeFactory, LeaderFactory, UserFactory

# --- Judges only see their own -----------------------------------------------

@pytest.mark.django_db
def test_judge_cannot_read_another_judges_assignment(world, as_user):
    client = as_user(world["judge_a"])
    assert client.get(f"/api/v1/assignments/{world['a1'].id}/").status_code == 200
    assert client.get(f"/api/v1/assignments/{world['a2'].id}/").status_code == 404


@pytest.mark.django_db
def test_my_assignments_lists_only_the_logged_in_judge(world, as_user):
    rows = as_user(world["judge_a"]).get("/api/v1/judge/my-assignments/").json()["data"]["results"]
    assert [r["id"] for r in rows] == [world["a1"].id]


@pytest.mark.django_db
def test_judges_cannot_use_the_applications_endpoint(world, as_user):
    # Judges see reports only through assignments, where blind judging applies.
    assert as_user(world["judge_a"]).get(f"/api/v1/applications/{world['report_1'].id}/").status_code == 403


# --- Applicants only see their own -------------------------------------------

@pytest.mark.django_db
def test_applicant_cannot_read_another_applicants_report(world, as_user):
    owner = as_user(world["report_1"].applicant)
    assert owner.get(f"/api/v1/applications/{world['report_1'].id}/").status_code == 200
    assert owner.get(f"/api/v1/applications/{world['report_2'].id}/").status_code == 404
    listed = owner.get("/api/v1/applications/").json()["data"]["results"]
    assert [r["id"] for r in listed] == [world["report_1"].id]


@pytest.mark.django_db
def test_applicant_cannot_change_another_applicants_report(world, as_user):
    r = as_user(world["report_1"].applicant).patch(f"/api/v1/applications/{world['report_2'].id}/",
                                                   {"title": "hacked"}, format="json")
    assert r.status_code == 404


@pytest.mark.django_db
def test_staff_and_leaders_see_all_applications(world, as_user):
    for user in (world["staff"], LeaderFactory()):
        assert as_user(user).get("/api/v1/applications/").json()["data"]["count"] == 2


# --- Only staff/leaders assign -----------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("who", ["applicant", "judge"])
def test_only_staff_or_leaders_can_assign(world, as_user, who):
    actor = world["report_1"].applicant if who == "applicant" else world["judge_a"]
    r = as_user(actor).post("/api/v1/assignments/", {"report": world["report_1"].id,
                                                     "judge": world["judge_b"].id}, format="json")
    assert r.status_code == 403
    assert r.json()["success"] is False


@pytest.mark.django_db
@pytest.mark.parametrize("who", ["staff", "leader"])
def test_staff_and_leaders_can_assign(world, as_user, who):
    actor = world["staff"] if who == "staff" else LeaderFactory()
    r = as_user(actor).post("/api/v1/assignments/", {"report": world["report_1"].id,
                                                     "judge": world["judge_b"].id}, format="json")
    assert r.status_code == 201
    assert JudgeAssignment.objects.filter(report=world["report_1"], judge=world["judge_b"]).exists()


# --- Judges score only their own assignments --------------------------------

@pytest.mark.django_db
def test_judge_can_score_only_assigned_reports(world, as_user):
    client = as_user(world["judge_a"])
    ok = client.post("/api/v1/evaluations/", {"assignment": world["a1"].id,
                                              "scores": {"approach": 8, "results": 9}}, format="json")
    assert ok.status_code == 201
    other = client.post("/api/v1/evaluations/", {"assignment": world["a2"].id,
                                                 "scores": {"approach": 8, "results": 9}}, format="json")
    assert other.status_code == 404


@pytest.mark.django_db
def test_judge_cannot_read_another_judges_evaluation(world, as_user):
    as_user(world["judge_b"]).post("/api/v1/evaluations/", {"assignment": world["a2"].id,
                                                            "scores": {"approach": 5}}, format="json")
    evaluation_id = world["a2"].evaluation.id
    assert as_user(world["judge_a"]).get(f"/api/v1/evaluations/{evaluation_id}/").status_code == 404


@pytest.mark.django_db
def test_non_judges_cannot_create_evaluations(world, as_user):
    r = as_user(world["staff"]).post("/api/v1/evaluations/", {"assignment": world["a1"].id,
                                                             "scores": {"approach": 8}}, format="json")
    assert r.status_code == 403


# --- Users -------------------------------------------------------------------

@pytest.mark.django_db
def test_only_leaders_create_staff_judge_or_leader_accounts(world, as_user):
    payload = {"email": "newjudge@example.com", "name": "New Judge", "role": "judge", "priority": 2}
    assert as_user(world["staff"]).post("/api/v1/users/", payload, format="json").status_code == 403
    r = as_user(LeaderFactory()).post("/api/v1/users/", payload, format="json")
    assert r.status_code == 201
    from apps.accounts.models import User
    assert User.objects.get(email="newjudge@example.com").judge_profile.priority == 2


@pytest.mark.django_db
def test_applicants_cannot_list_users_but_can_read_themselves(as_user):
    applicant = UserFactory()
    client = as_user(applicant)
    assert client.get("/api/v1/users/").status_code == 403
    me = client.patch("/api/v1/users/me/", {"name": "Renamed", "role": "leader"}, format="json")
    assert me.status_code == 200
    applicant.refresh_from_db()
    assert applicant.name == "Renamed" and applicant.role == "applicant"   # role can't be self-changed


# --- Blind judging through the API (Rule 1) ---------------------------------

@pytest.mark.django_db
def test_blind_award_hides_identity_from_judge(world, as_user):
    world["award"].blind_judging = True
    world["award"].save()
    report = as_user(world["judge_a"]).get(f"/api/v1/assignments/{world['a1'].id}/").json()["data"]["report"]
    answers = {a["key"]: a for a in report["answers"]}
    assert report["blind"] is True and report["applicant"] is None
    assert answers["org"]["value"] is None and answers["org"]["hidden"] is True
    assert answers["story"]["value"] == "We cut waste."
    assert "Secret Org" not in str(report)


@pytest.mark.django_db
def test_open_award_shows_identity_to_judge(world, as_user):
    report = as_user(world["judge_a"]).get(f"/api/v1/assignments/{world['a1'].id}/").json()["data"]["report"]
    assert report["blind"] is False
    assert {a["key"]: a["value"] for a in report["answers"]}["org"] == "Secret Org Ltd"


@pytest.mark.django_db
def test_assigning_a_conflicted_judge_is_refused(world, as_user):
    from apps.assignments.services import record_conflict
    profile = world["report_1"].applicant.applicant_profile
    record_conflict(judge=world["judge_b"], profile=profile, by=world["staff"], reason="Former employer")
    r = as_user(world["staff"]).post("/api/v1/assignments/", {"report": world["report_1"].id,
                                                             "judge": world["judge_b"].id}, format="json")
    assert r.status_code == 400
    assert "conflict" in r.json()["message"]


@pytest.mark.django_db
def test_eligible_judges_excludes_conflicts_and_already_assigned(world, as_user):
    extra = JudgeFactory(awards=[world["award"]])
    rows = as_user(world["staff"]).get(f"/api/v1/applications/{world['report_1'].id}/eligible-judges/").json()
    emails = [u["email"] for u in rows["data"]]
    assert world["judge_a"].email not in emails          # already on it
    assert extra.email in emails and world["judge_b"].email in emails


@pytest.mark.django_db
def test_application_reports_are_unique_per_award(as_user):
    report = ApplicationFactory()
    r = as_user(report.applicant).post("/api/v1/applications/", {"award": report.award.slug, "title": "Again"},
                                       format="json")
    assert r.status_code == 400
    assert "already" in r.json()["message"]
