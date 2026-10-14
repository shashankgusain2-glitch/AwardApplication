"""End-to-end API workflows, data rules, the response format, health and docs."""
import pytest
from django.db import IntegrityError, transaction

from apps.applications.models import Application
from apps.assignments.models import JudgeAssignment
from apps.audit.models import AuditLog
from apps.awards.models import Award
from apps.evaluations.models import CriterionScore, ScoreChange

from ..factories import ApplicantProfileFactory, ApplicationFactory, AwardFactory, JudgeFactory, LeaderFactory


@pytest.mark.django_db
def test_applicant_draft_save_midway_and_submit(as_user):
    award = AwardFactory()
    applicant = ApplicantProfileFactory().user
    client = as_user(applicant)
    created = client.post("/api/v1/applications/", {"award": award.slug, "title": "Our story"}, format="json")
    assert created.status_code == 201
    app_id = created.json()["data"]["id"]

    client.patch(f"/api/v1/applications/{app_id}/", {"content": {"org": "Acme"}}, format="json")
    early = client.post(f"/api/v1/applications/{app_id}/submit/")
    assert early.status_code == 400 and "required" in early.json()["message"]

    client.patch(f"/api/v1/applications/{app_id}/", {"content": {"story": "We cut waste."}}, format="json")
    done = client.post(f"/api/v1/applications/{app_id}/submit/")
    assert done.status_code == 200 and done.json()["data"]["status"] == "submitted"

    locked = client.patch(f"/api/v1/applications/{app_id}/", {"title": "Changed"}, format="json")
    assert locked.status_code == 400


@pytest.mark.django_db
def test_full_judging_flow_scores_the_report_and_audits_it(world, as_user):
    for key in ("a1",):
        judge = world["judge_a"]
        client = as_user(judge)
        assert client.post(f"/api/v1/assignments/{world[key].id}/accept/").status_code == 200
        r = client.post("/api/v1/evaluations/", {"assignment": world[key].id, "scores": {"approach": 8},
                                                 "submit": False}, format="json")
        assert r.json()["data"]["status"] == "draft"                      # saved midway
        evaluation_id = r.json()["data"]["id"]
        r = client.patch(f"/api/v1/evaluations/{evaluation_id}/", {"scores": {"results": 9}, "submit": True},
                         format="json")
        assert r.json()["data"]["status"] == "submitted"
        assert r.json()["data"]["total_score"] == "8.60"                  # 0.4×8 + 0.6×9

    # judges_per_report is 2, so one more judge is needed before "scored"
    report = world["report_1"]
    report.refresh_from_db()
    assert report.status == Application.Status.IN_REVIEW
    actions = set(AuditLog.objects.values_list("action", flat=True))
    assert {"assign", "score", "status_change"} <= actions


@pytest.mark.django_db
def test_report_is_scored_when_enough_judges_submit(world, as_user):
    extra = JudgeFactory(awards=[world["award"]])
    as_user(world["staff"]).post("/api/v1/assignments/", {"report": world["report_1"].id, "judge": extra.id},
                                 format="json")
    for judge in (world["judge_a"], extra):
        assignment = JudgeAssignment.objects.get(report=world["report_1"], judge=judge)
        as_user(judge).post("/api/v1/evaluations/", {"assignment": assignment.id,
                                                     "scores": {"approach": 7, "results": 7}, "submit": True},
                            format="json")
    world["report_1"].refresh_from_db()
    assert world["report_1"].status == Application.Status.SCORED


@pytest.mark.django_db
def test_score_change_needs_staff_permission_reason_and_is_recorded(world, as_user):
    judge_client = as_user(world["judge_a"])
    ev = judge_client.post("/api/v1/evaluations/", {"assignment": world["a1"].id,
                                                    "scores": {"approach": 8, "results": 9}, "submit": True},
                           format="json").json()["data"]
    blocked = judge_client.post(f"/api/v1/evaluations/{ev['id']}/change-scores/",
                                {"scores": {"results": 5}, "reason": "Rethink"}, format="json")
    assert blocked.status_code == 400

    req = judge_client.post(f"/api/v1/evaluations/{ev['id']}/request-change/", {"reason": "Misread"},
                            format="json").json()["data"]
    as_user(world["staff"]).post(f"/api/v1/score-change-requests/{req['id']}/decide/", {"approve": True},
                                 format="json")
    too_soon = judge_client.post(f"/api/v1/evaluations/{ev['id']}/change-scores/",
                                 {"scores": {"results": 5}, "reason": "Too soon"}, format="json")
    assert too_soon.status_code == 400                                    # staff alone isn't enough
    confirmed = as_user(LeaderFactory()).post(f"/api/v1/score-change-requests/{req['id']}/decide/",
                                              {"approve": True, "note": "Agreed"}, format="json")
    assert confirmed.json()["data"]["status"] == "approved"
    changed = judge_client.post(f"/api/v1/evaluations/{ev['id']}/change-scores/",
                                {"scores": {"results": 5}, "reason": "Results cover one plant only"}, format="json")
    assert changed.status_code == 200
    data = changed.json()["data"]
    assert data["total_score"] == "6.20"                                  # 0.4×8 + 0.6×5
    assert data["score_changes"][0]["reason"] == "Results cover one plant only"
    change = ScoreChange.objects.get()
    assert (change.old_score, change.new_score, change.changed_by) == (9, 5, world["judge_a"])


@pytest.mark.django_db
def test_declined_report_goes_back_to_the_pool(world, as_user):
    as_user(world["judge_a"]).post(f"/api/v1/assignments/{world['a1'].id}/decline/")
    world["report_1"].refresh_from_db()
    assert world["report_1"].status == Application.Status.SUBMITTED


@pytest.mark.django_db
def test_assignment_needs_a_verified_organisation(as_user):
    report = ApplicationFactory()
    profile = report.applicant.applicant_profile
    profile.verification_status = "pending"
    profile.save()
    judge = JudgeFactory(awards=[report.award])
    r = as_user(LeaderFactory()).post("/api/v1/assignments/", {"report": report.id, "judge": judge.id},
                                      format="json")
    assert r.status_code == 400 and "verify" in r.json()["message"]


@pytest.mark.django_db
def test_leader_approves_scored_report_staff_cannot(world, as_user):
    report = world["report_1"]
    report.status = Application.Status.SCORED
    report.save()
    assert as_user(world["staff"]).post(f"/api/v1/applications/{report.id}/change-status/",
                                        {"status": "approved"}, format="json").status_code == 400
    ok = as_user(LeaderFactory()).post(f"/api/v1/applications/{report.id}/change-status/",
                                       {"status": "approved"}, format="json")
    assert ok.status_code == 200 and ok.json()["data"]["status"] == "approved"


# --- Database rules -----------------------------------------------------------

@pytest.mark.django_db
def test_database_rejects_scores_outside_1_to_10(world, as_user):
    as_user(world["judge_a"]).post("/api/v1/evaluations/", {"assignment": world["a1"].id,
                                                            "scores": {"approach": 8}}, format="json")
    score = CriterionScore.objects.get()
    score.score = 11
    with pytest.raises(IntegrityError), transaction.atomic():
        score.save()


@pytest.mark.django_db
def test_api_rejects_scores_outside_1_to_10(world, as_user):
    r = as_user(world["judge_a"]).post("/api/v1/evaluations/", {"assignment": world["a1"].id,
                                                                "scores": {"approach": 0}}, format="json")
    assert r.status_code == 400 and "1 to 10" in r.json()["message"]


@pytest.mark.django_db
def test_same_judge_cannot_be_assigned_twice_to_a_report(world):
    with pytest.raises(IntegrityError), transaction.atomic():
        JudgeAssignment.objects.create(judge=world["judge_a"], report=world["report_1"], round=1)


@pytest.mark.django_db
def test_soft_delete_hides_rows_but_keeps_them():
    award = AwardFactory()
    award.delete()
    assert not Award.objects.filter(pk=award.pk).exists()
    assert Award.all_objects.filter(pk=award.pk, is_deleted=True).exists()


@pytest.mark.django_db
def test_audit_entries_cannot_be_changed(world):
    entry = AuditLog.objects.first()
    entry.action = "update"
    with pytest.raises(ValueError):
        entry.save()


@pytest.mark.django_db
def test_published_form_version_cannot_be_changed():
    form = AwardFactory().current_form
    form.questions = []
    with pytest.raises(Exception, match="published form version"):
        form.save()


# --- Response format, pagination, filtering, health, docs -------------------

@pytest.mark.django_db
def test_list_responses_are_wrapped_and_paginated(world, as_user):
    body = as_user(world["staff"]).get("/api/v1/applications/?page_size=1").json()
    assert body["success"] is True and body["message"] == "" and body["errors"] is None
    assert body["data"]["count"] == 2 and len(body["data"]["results"]) == 1 and body["data"]["next"]


@pytest.mark.django_db
def test_filtering_search_and_ordering(world, as_user):
    client = as_user(world["staff"])
    assert client.get("/api/v1/applications/?status=assigned").json()["data"]["count"] == 2
    assert client.get("/api/v1/applications/?status=draft").json()["data"]["count"] == 0
    ref = world["report_2"].reference
    assert client.get(f"/api/v1/applications/?search={ref}").json()["data"]["count"] == 1
    assert client.get("/api/v1/applications/?ordering=-created_at").status_code == 200


@pytest.mark.django_db
def test_validation_errors_use_the_same_shape(world, as_user):
    body = as_user(world["staff"]).post("/api/v1/assignments/", {}, format="json").json()
    assert body["success"] is False and body["data"] is None
    assert "report" in body["errors"] and "judge" in body["errors"]


@pytest.mark.django_db
def test_health_endpoint(api):
    r = api.get("/api/v1/health/")
    assert r.status_code == 200 and r.json()["data"] == {"status": "ok", "database": "ok"}


@pytest.mark.django_db
def test_api_docs_and_schema_load(api):
    assert api.get("/api/schema/").status_code == 200
    assert api.get("/api/docs/").status_code == 200


@pytest.mark.django_db
def test_awards_are_public_read_only(api):
    award = AwardFactory()
    r = api.get(f"/api/v1/awards/{award.slug}/")
    assert r.status_code == 200
    assert [c["key"] for c in r.json()["data"]["criteria"]] == ["approach", "results"]
    assert api.post("/api/v1/awards/", {}, format="json").status_code in (401, 403, 405)


@pytest.mark.django_db
def test_seed_data_creates_the_required_demo_set():
    from django.core.management import call_command

    from apps.accounts.models import User
    call_command("seed_data", verbosity=0, stdout=open("/dev/null", "w"))
    count = lambda role: User.objects.filter(role=role).count()  # noqa: E731
    assert (count("leader"), count("staff"), count("judge"), count("applicant")) == (1, 2, 3, 5)
    assert Application.objects.count() == 10
    for judge in User.objects.filter(role="judge"):
        assert judge.judge_assignments.count() >= 2                       # several per judge
    assert Application.objects.filter(status="scored").exists()            # some already scored
    call_command("seed_data", verbosity=0, stdout=open("/dev/null", "w"))  # safe to re-run
    assert Application.objects.count() == 10
