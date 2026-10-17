"""
Roadmap step 3.4, Core API: the endpoints added to close the gaps, and the
bugs found while testing them in Postman.

- /auth/me/, user deactivate / activate (leaders only, never yourself)
- /assignments/bulk/ (exact pairs, or "fill with the best judges"; all or nothing)
- /judge/my-assignments/ rows carry submission date, status and criteria
- /dashboard/summary/ and /lookups/
- fixed: bad refresh token on logout, ?round=abc, true/false as a score
"""
import pytest

from apps.accounts.models import User
from apps.assignments.models import JudgeAssignment

from ..conftest import PASSWORD
from ..factories import (
    ApplicantProfileFactory,
    ApplicationFactory,
    AwardFactory,
    JudgeFactory,
    LeaderFactory,
    StaffFactory,
    UserFactory,
)

LOGIN = "/api/v1/auth/login/"


def tokens(api, user):
    return api.post(LOGIN, {"email": user.email, "password": PASSWORD}, format="json").json()["data"]


# --- /auth/me/ ------------------------------------------------------------------

@pytest.mark.django_db
def test_me_needs_a_token(api):
    response = api.get("/api/v1/auth/me/")
    assert response.status_code == 401
    assert response.json()["success"] is False


@pytest.mark.django_db
def test_me_reads_and_updates_only_my_name(api):
    user = UserFactory(name="Old Name")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens(api, user)['access']}")
    assert api.get("/api/v1/auth/me/").json()["data"]["email"] == user.email
    response = api.patch("/api/v1/auth/me/", {"name": "New Name", "role": "leader"}, format="json")
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.name == "New Name" and user.role == "applicant"


# --- Users: deactivate / activate -------------------------------------------------

@pytest.mark.django_db
def test_leader_deactivates_a_user_and_their_tokens_stop_working(api, as_user):
    judge = JudgeFactory()
    issued = tokens(api, judge)
    response = as_user(LeaderFactory()).post(f"/api/v1/users/{judge.id}/deactivate/")
    assert response.status_code == 200 and response.json()["data"]["is_active"] is False

    assert api.post("/api/v1/auth/refresh/", {"refresh": issued["refresh"]}, format="json").status_code == 401
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {issued['access']}")
    assert api.get("/api/v1/auth/me/").status_code == 401
    api.credentials()
    assert api.post(LOGIN, {"email": judge.email, "password": PASSWORD}, format="json").status_code == 401


@pytest.mark.django_db
def test_leader_can_reactivate(as_user):
    judge = JudgeFactory(is_active=False)
    response = as_user(LeaderFactory()).post(f"/api/v1/users/{judge.id}/activate/")
    assert response.status_code == 200 and response.json()["data"]["is_active"] is True


@pytest.mark.django_db
@pytest.mark.parametrize("factory", [StaffFactory, JudgeFactory, UserFactory])
def test_only_leaders_deactivate(as_user, factory):
    target = JudgeFactory()
    assert as_user(factory()).post(f"/api/v1/users/{target.id}/deactivate/").status_code == 403


@pytest.mark.django_db
def test_leader_cannot_lock_themselves_out(as_user):
    leader = LeaderFactory()
    client = as_user(leader)
    assert client.post(f"/api/v1/users/{leader.id}/deactivate/").status_code == 400
    assert client.patch(f"/api/v1/users/{leader.id}/", {"role": "applicant"}, format="json").status_code == 400
    leader.refresh_from_db()
    assert leader.is_active and leader.role == "leader"


# --- Bulk assign ----------------------------------------------------------------------

@pytest.mark.django_db
def test_bulk_assign_exact_pairs(world, as_user):
    judge_c = JudgeFactory(awards=[world["award"]])
    report_3 = ApplicationFactory(award=world["award"])
    response = as_user(world["staff"]).post("/api/v1/assignments/bulk/", {"items": [
        {"report": world["report_1"].id, "judge": judge_c.id},
        {"report": report_3.id, "judge": judge_c.id},
    ]}, format="json")
    assert response.status_code == 201
    assert len(response.json()["data"]) == 2
    assert JudgeAssignment.objects.filter(judge=judge_c).count() == 2


@pytest.mark.django_db
def test_bulk_assign_is_all_or_nothing(world, as_user):
    judge_c = JudgeFactory(awards=[world["award"]])
    response = as_user(world["staff"]).post("/api/v1/assignments/bulk/", {"items": [
        {"report": world["report_1"].id, "judge": judge_c.id},
        {"report": world["report_1"].id, "judge": world["judge_a"].id},   # already on it
    ]}, format="json")
    assert response.status_code == 400
    assert "Item 2" in response.json()["message"]
    assert not JudgeAssignment.objects.filter(judge=judge_c).exists()   # item 1 rolled back


@pytest.mark.django_db
def test_bulk_auto_fills_each_report_up_to_judges_per_report(as_user):
    award = AwardFactory(judges_per_report=2)
    JudgeFactory(awards=[award]), JudgeFactory(awards=[award]), JudgeFactory(awards=[award])
    reports = [ApplicationFactory(award=award), ApplicationFactory(award=award)]
    response = as_user(StaffFactory()).post("/api/v1/assignments/bulk/",
                                            {"reports": [r.id for r in reports]}, format="json")
    assert response.status_code == 201
    for report in reports:
        assert report.assignments.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("payload", [{}, {"items": [], "reports": []}, {"items": [{"report": 1}], "reports": [1]}])
def test_bulk_assign_needs_exactly_one_of_items_or_reports(as_user, payload):
    assert as_user(StaffFactory()).post("/api/v1/assignments/bulk/", payload, format="json").status_code == 400


@pytest.mark.django_db
def test_judges_cannot_bulk_assign(world, as_user):
    response = as_user(world["judge_a"]).post("/api/v1/assignments/bulk/",
                                              {"reports": [world["report_1"].id]}, format="json")
    assert response.status_code == 403


# --- My assignments rows ------------------------------------------------------------------

@pytest.mark.django_db
def test_my_assignments_rows_have_what_the_judge_list_needs(world, as_user):
    row = as_user(world["judge_a"]).get("/api/v1/judge/my-assignments/").json()["data"]["results"][0]
    report = row["report"]
    assert report["title"] == world["report_1"].title
    assert report["submitted_at"] and report["report_status"] == "assigned"
    assert report["applicant"] == world["report_1"].applicant.display_name   # award isn't blind
    assert [c["key"] for c in row["criteria"]] == ["approach", "results"]
    assert row["status"] == "pending"


@pytest.mark.django_db
def test_my_assignments_hide_the_applicant_on_blind_awards(world, as_user):
    world["award"].blind_judging = True
    world["award"].save()
    report = as_user(world["judge_a"]).get("/api/v1/judge/my-assignments/").json()["data"]["results"][0]["report"]
    assert report["applicant"] is None
    assert "Secret Org" not in str(report)


# --- Dashboard summary and lookups ---------------------------------------------------------

@pytest.mark.django_db
def test_summary_counts_only_what_each_role_may_see(world, as_user):
    applicant = world["report_1"].applicant
    mine = as_user(applicant).get("/api/v1/dashboard/summary/").json()["data"]
    assert mine["role"] == "applicant" and mine["total"] == 1
    assert mine["applications_by_status"]["assigned"] == 1

    judge = as_user(world["judge_a"]).get("/api/v1/dashboard/summary/").json()["data"]
    assert judge["total"] == 1 and judge["assignments_by_status"]["pending"] == 1

    staff = as_user(world["staff"]).get("/api/v1/dashboard/summary/").json()["data"]
    assert staff["total"] == 2 and staff["applications_by_status"]["assigned"] == 2
    assert staff["awards"][0]["evaluations_total"] == 2


@pytest.mark.django_db
def test_summary_and_lookups_need_a_token(api):
    assert api.get("/api/v1/dashboard/summary/").status_code == 401
    assert api.get("/api/v1/lookups/").status_code == 401


@pytest.mark.django_db
def test_lookups_list_the_codes(as_user):
    data = as_user(UserFactory()).get("/api/v1/lookups/").json()["data"]
    assert {"value": "judge", "label": "Judge"} in data["roles"]
    assert data["score_range"] == {"min": 1, "max": 10}


# --- Bugs found while testing ------------------------------------------------------------------

@pytest.mark.django_db
def test_logout_with_a_broken_refresh_token_is_400_not_500(as_user):
    response = as_user(UserFactory()).post("/api/v1/auth/logout/", {"refresh": "garbage"}, format="json")
    assert response.status_code == 400
    assert response.json()["message"].startswith("refresh:")


@pytest.mark.django_db
def test_eligible_judges_with_a_bad_round_is_400_not_500(world, as_user):
    response = as_user(world["staff"]).get(f"/api/v1/applications/{world['report_1'].id}/eligible-judges/?round=abc")
    assert response.status_code == 400


@pytest.mark.django_db
def test_true_is_not_a_score(world, as_user):
    response = as_user(world["judge_a"]).post("/api/v1/evaluations/", {
        "assignment": world["a1"].id, "scores": {"approach": True, "results": 8}}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_field_errors_name_the_field_in_the_message(as_user):
    response = as_user(StaffFactory()).get("/api/v1/applications/?status=bogus")
    assert response.status_code == 400
    assert response.json()["message"].startswith("status:")


@pytest.mark.django_db
def test_deactivated_users_are_not_offered_as_judges(world, as_user):
    judge_c = JudgeFactory(awards=[world["award"]])
    User.objects.filter(pk=judge_c.pk).update(is_active=False)
    ids = [j["id"] for j in as_user(world["staff"]).get(
        f"/api/v1/applications/{world['report_1'].id}/eligible-judges/").json()["data"]]
    assert judge_c.id not in ids


@pytest.mark.django_db
def test_deleting_a_draft_returns_an_empty_204(as_user):
    from apps.applications import services
    award = AwardFactory()
    applicant = ApplicantProfileFactory().user                # an organisation with its GSTIN and PAN
    draft = services.create_draft(applicant=applicant, award=award, title="Draft")
    response = as_user(applicant).delete(f"/api/v1/applications/{draft.id}/")
    assert response.status_code == 204
    assert response.content == b""   # a body on 204 breaks HTTP clients (found in Postman)
