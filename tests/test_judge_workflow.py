"""
Judge workflow and Round 2 (12 Oct meeting):

  email link → judging tab → accept / decline (declined → back to pool)
  → grade, saving partway → submit → report judged
  → change scores only after staff allow it, with a reason
  → Round 2: group of judges in an online meeting grades the organisation
"""
import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.entries.models import Application
from apps.judging import services
from apps.judging.models import Assignment, ScoreChange

from .conftest import judge_client, make_report

S = Application.Status
BE_SCORES = {"score_leadership": "8", "score_people": "7", "score_results": "9"}


def _assigned_report(judges, staff_user=None):
    app = make_report()
    services.auto_assign(app, staff_user)
    return app


def _grade_all(app, scores=BE_SCORES):
    for a in app.assignments.filter(round=1):
        c = judge_client(a.judge)
        c.post(reverse("judging:respond", args=[a.pk]), {"answer": "accept"})
        c.post(reverse("judging:grade", args=[a.pk]), {**scores, "action": "submit"})


# --- Email link and tab ------------------------------------------------------

@pytest.mark.django_db
def test_email_link_logs_judge_in_and_opens_judging_tab(client, judges):
    link = services.login_link(judges[0])
    response = client.get(link)
    assert response["Location"] == reverse("judging:tab")
    assert "Kapoor" in client.get(reverse("judging:tab")).content.decode()


@pytest.mark.django_db
def test_tampered_link_is_refused(client, judges):
    response = client.get(services.login_link(judges[0])[:-3] + "xyz/")
    assert response["Location"] == reverse("core:home")
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_judge_sees_only_reports_assigned_to_them(judges):
    app = _assigned_report(judges)   # BE needs 3 judges → all three get it
    other = make_report(name="Other Co", gstin="29PQRSX6789K1Z1", slug="kaizen")
    services.auto_assign(other, None)  # Kaizen needs 2 → Kapoor and Rao
    page = judge_client(judges[2]).get(reverse("judging:tab")).content.decode()
    assert "Acme Precision" in page and "Other Co" not in page


# --- Accept / decline -------------------------------------------------------

@pytest.mark.django_db
def test_accept_starts_judging(judges):
    app = _assigned_report(judges)
    a = app.assignments.first()
    judge_client(a.judge).post(reverse("judging:respond", args=[a.pk]), {"answer": "accept"})
    app.refresh_from_db()
    assert app.status == S.JUDGING


@pytest.mark.django_db
def test_declined_report_goes_back_to_pool(judges):
    app = make_report(slug="kaizen")
    services.assign(app, [judges[0]], None)
    a = app.assignments.get()
    judge_client(judges[0]).post(reverse("judging:respond", args=[a.pk]), {"answer": "decline"})
    app.refresh_from_db()
    assert app.status == S.POOL
    assert judges[0] not in services.suggested_judges(app)  # not offered the same report again


@pytest.mark.django_db
def test_judge_cannot_open_report_before_accepting(judges):
    app = _assigned_report(judges)
    a = app.assignments.first()
    response = judge_client(a.judge).get(reverse("judging:grade", args=[a.pk]))
    assert response["Location"] == reverse("judging:tab")


@pytest.mark.django_db
def test_judge_cannot_open_someone_elses_assignment(judges):
    app = make_report(slug="kaizen")
    services.assign(app, [judges[0]], None)
    a = app.assignments.get()
    assert judge_client(judges[1]).get(reverse("judging:grade", args=[a.pk])).status_code == 404


# --- Grading ----------------------------------------------------------------

@pytest.mark.django_db
def test_partial_grading_is_saved(judges):
    app = _assigned_report(judges)
    a = app.assignments.first()
    c = judge_client(a.judge)
    c.post(reverse("judging:respond", args=[a.pk]), {"answer": "accept"})
    c.post(reverse("judging:grade", args=[a.pk]), {"score_leadership": "8", "action": "save"})
    a.refresh_from_db()
    assert a.status == Assignment.Status.ACCEPTED
    assert a.scores_by_key["leadership"].value == 8
    assert a.progress == 33


@pytest.mark.django_db
def test_submit_needs_every_part_scored(judges):
    app = _assigned_report(judges)
    a = app.assignments.first()
    c = judge_client(a.judge)
    c.post(reverse("judging:respond", args=[a.pk]), {"answer": "accept"})
    c.post(reverse("judging:grade", args=[a.pk]), {"score_leadership": "8", "action": "submit"})
    a.refresh_from_db()
    assert a.status == Assignment.Status.ACCEPTED


@pytest.mark.django_db
def test_report_is_judged_when_all_judges_submit(judges):
    app = _assigned_report(judges)
    _grade_all(app)
    app.refresh_from_db()
    assert app.status == S.JUDGED
    assert app.round1_average == 8.1  # 0.3*8 + 0.3*7 + 0.4*9


@pytest.mark.django_db
def test_graded_report_is_locked(judges):
    app = _assigned_report(judges)
    _grade_all(app)
    a = app.assignments.first()
    judge_client(a.judge).post(reverse("judging:grade", args=[a.pk]), {**BE_SCORES, "score_results": "2", "action": "save"})
    assert a.scores_by_key["results"].value == 9


# --- Changing scores: staff permission + reason ------------------------------

@pytest.mark.django_db
def test_score_change_needs_staff_permission_and_is_recorded(judges, staff_client):
    app = _assigned_report(judges)
    _grade_all(app)
    a = app.assignments.first()
    c = judge_client(a.judge)

    # Without permission: nothing changes.
    c.post(reverse("judging:grade", args=[a.pk]), {**BE_SCORES, "score_results": "6", "reason": "x", "action": "change"})
    assert a.scores_by_key["results"].value == 9

    # Ask, staff allow, then change with a reason.
    c.post(reverse("judging:grade", args=[a.pk]), {"reason": "Misread the results table", "action": "request_change"})
    request = a.change_requests.get()
    staff_client.post(reverse("staff:score_request_action", args=[request.pk]), {"action": "approve"})
    c.post(reverse("judging:grade", args=[a.pk]),
           {**BE_SCORES, "score_results": "6", "reason": "Results cover one plant only", "action": "change"})

    assert a.scores_by_key["results"].value == 6
    change = ScoreChange.objects.get()
    assert (change.criterion, change.old_value, change.new_value) == ("results", 9, 6)
    assert change.reason == "Results cover one plant only"
    assert change.changed_by == a.judge.user

    # Permission is used up: a second change needs a new request.
    a.refresh_from_db()
    assert not a.change_allowed


@pytest.mark.django_db
def test_refused_change_request_keeps_scores(judges, staff_client):
    app = _assigned_report(judges)
    _grade_all(app)
    a = app.assignments.first()
    services.request_change(a, "Want to rethink")
    staff_client.post(reverse("staff:score_request_action", args=[a.change_requests.get().pk]), {"action": "decline"})
    a.refresh_from_db()
    assert not a.change_allowed


# --- Round 2 -----------------------------------------------------------------

@pytest.mark.django_db
def test_round2_meeting_with_group_of_judges(judges, staff_client):
    app = _assigned_report(judges)
    _grade_all(app)
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "shortlist"})
    when = (timezone.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {
        "action": "round2", "scheduled_at": when, "meeting_link": "https://meet.example/abc",
        "judges": [judges[0].pk, judges[1].pk]})
    app.refresh_from_db()
    assert app.round2_meeting.meeting_link == "https://meet.example/abc"
    round2 = app.assignments.filter(round=2)
    assert round2.count() == 2

    for a in round2:
        judge_client(a.judge).post(reverse("judging:grade", args=[a.pk]),
                                   {"score_story": "9", "score_evidence": "8", "score_answers": "9", "action": "submit"})
    app.refresh_from_db()
    assert app.status == S.ROUND2_DONE
    assert app.round2_average == 8.6


@pytest.mark.django_db
def test_grade_page_loads_while_grading_after_and_with_permission(judges):
    app = _assigned_report(judges)
    a = app.assignments.first()
    c = judge_client(a.judge)
    c.post(reverse("judging:respond", args=[a.pk]), {"answer": "accept"})
    assert c.get(reverse("judging:grade", args=[a.pk])).status_code == 200      # grading
    c.post(reverse("judging:grade", args=[a.pk]), {**BE_SCORES, "action": "submit"})
    page = c.get(reverse("judging:grade", args=[a.pk])).content.decode()        # locked
    assert "Ask staff for permission" in page
    a.refresh_from_db()
    services.request_change(a, "Rethink")
    services.decide_change_request(a.change_requests.get(), True, None)
    page = c.get(reverse("judging:grade", args=[a.pk])).content.decode()        # allowed
    assert "Reason for the change" in page
