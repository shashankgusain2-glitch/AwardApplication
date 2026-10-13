"""Staff tools and the leadership dashboard (12 Oct meeting)."""
import pytest
from django.test import Client
from django.urls import reverse

from apps.awards.models import Award
from apps.core.models import ActivityLog
from apps.entries.models import Application
from apps.judging import services
from apps.judging.models import Conflict

from .conftest import User, make_report

S = Application.Status


@pytest.mark.django_db
def test_auto_assign_balances_workload(judges, staff_client):
    first = make_report(slug="kaizen")
    staff_client.post(reverse("staff:report_action", args=[first.pk]), {"action": "auto_assign"})
    assert sorted(a.judge.name for a in first.assignments.all()) == ["Kapoor", "Rao"]  # priority 1 and 2

    # Kapoor is now full (limit 1), so the next report goes to Rao and Iyer.
    judges[0].max_load = 1
    judges[0].save()
    second = make_report(name="Two", gstin="29PQRSX6789K1Z1", slug="kaizen")
    picks = services.auto_assign(second, None)
    assert sorted(j.name for j in picks) == ["Iyer", "Rao"]


@pytest.mark.django_db
def test_equal_priority_goes_to_lighter_load(judges):
    for j in judges:
        j.priority = 1
        j.save()
    busy = make_report(name="Busy", gstin="29PQRSX6789K1Z1", slug="kaizen")
    services.assign(busy, [judges[0]], None)        # Kapoor has 1 open report
    app = make_report(slug="kaizen")
    picks = services.auto_assign(app, None)          # needs 2: the two with 0 load
    assert judges[0] not in picks


@pytest.mark.django_db
def test_judge_at_limit_is_not_offered(judges):
    judges[2].max_load = 0
    judges[2].save()
    app = make_report()
    assert judges[2] not in services.suggested_judges(app)


@pytest.mark.django_db
def test_judges_per_report_is_set_by_staff(judges, staff_client):
    award = Award.objects.get(slug="kaizen")
    staff_client.post(reverse("staff:events"), {
        "award": award.pk, f"e{award.pk}-judges_per_report": "1",
        f"e{award.pk}-is_open": "on", f"e{award.pk}-deadline": "2026-12-15"})
    app = make_report(slug="kaizen")
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "auto_assign"})
    assert app.assignments.count() == 1


@pytest.mark.django_db
def test_staff_can_add_judge_with_priority_and_panel(staff_client):
    award = Award.objects.get(slug="kaizen")
    staff_client.post(reverse("staff:judges"), {
        "add_judge": "1", "judge-name": "New Judge", "judge-email": "new@j.example", "judge-expertise": "Lean",
        "judge-priority": "4", "judge-max_load": "5", "judge-panels": [award.pk]})
    judge = User.objects.get(email="new@j.example").judge
    assert (judge.priority, judge.max_load, list(judge.panels.all())) == (4, 5, [award])


@pytest.mark.django_db
def test_form_change_publishes_new_version_and_keeps_old_reports(staff_client):
    old = make_report(slug="kaizen")
    award = Award.objects.get(slug="kaizen")
    keep = [q["key"] for q in award.current_form.questions][:2]
    staff_client.post(reverse("staff:form_editor", args=["kaizen"]),
                      {"keep": keep, "label": "Money saved per year", "type": "number", "required": "on"})
    award.refresh_from_db()
    assert award.current_form.number == 2
    assert [q["label"] for q in award.current_form.questions][-1] == "Money saved per year"
    old.refresh_from_db()
    assert old.form_version.number == 1


@pytest.mark.django_db
def test_actions_are_recorded_in_activity_log(judges, staff_client):
    app = make_report(status=S.SUBMITTED)
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "confirm"})
    entry = ActivityLog.objects.get(application=app)
    assert "Confirmed" in entry.action and entry.actor.email == "staff@uec.example"


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["staff:home", "staff:reports", "staff:judges", "staff:requests",
                                  "staff:events", "staff:activity"])
def test_staff_pages_load(staff_client, name):
    assert staff_client.get(reverse(name)).status_code == 200


@pytest.mark.django_db
def test_applicants_and_judges_cannot_use_staff_pages(judges):
    c = Client()
    c.force_login(judges[0].user)
    assert c.get(reverse("staff:home")).status_code == 302


# --- Leadership --------------------------------------------------------------

@pytest.mark.django_db
def test_leadership_dashboard_counts_the_whole_event(judges):
    make_report(status=S.POOL)
    make_report(name="B", gstin="29PQRSX6789K1Z1", status=S.REJECTED)
    make_report(name="C", gstin="33PQRSX6789K1Z2", status=S.JUDGING)
    leader = User.objects.create(email="lead@uec.example", username="lead@uec.example", is_leader=True)
    c = Client()
    c.force_login(leader)
    page = c.get(reverse("dashboard:overview"))
    be = next(e for e in page.context["events"] if e["award"].slug == "business-excellence")
    assert (be["pool"], be["rejected"], be["evaluating"]) == (1, 1, 1)


@pytest.mark.django_db
def test_only_leadership_sees_dashboard(staff_client):
    assert staff_client.get(reverse("dashboard:overview")).status_code == 302


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["submitted", "pool", "assigned", "judging", "judged", "shortlisted",
                                    "round2_done", "rejected"])
def test_staff_report_page_loads_at_every_stage(judges, staff_client, status):
    app = make_report(status=status)
    app.edit_request = "requested"
    app.edit_reason = "Typo"
    app.save()
    assert staff_client.get(reverse("staff:report", args=[app.pk])).status_code == 200
