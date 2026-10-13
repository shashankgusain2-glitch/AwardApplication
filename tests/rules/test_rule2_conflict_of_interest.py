"""
Rule 2: a judge is never given an application they have a conflict with.

From the 12 Oct meeting: judges don't declare conflicts (they rarely would);
STAFF record them, and the system enforces them when assigning.
"""
import pytest
from django.urls import reverse

from apps.awards.models import Award
from apps.judging import services
from apps.judging.models import Conflict

from ..conftest import make_report


def _conflict(judge, app):
    return Conflict.objects.create(judge=judge, organisation=app.organisation)


@pytest.mark.django_db
def test_conflicted_judge_is_never_suggested(judges):
    app = make_report()
    _conflict(judges[0], app)
    assert judges[0] not in services.suggested_judges(app)


@pytest.mark.django_db
def test_auto_assign_skips_conflicted_judge(judges):
    app = make_report(slug="kaizen")
    _conflict(judges[0], app)
    picks = services.auto_assign(app, None)
    assert judges[0] not in picks


@pytest.mark.django_db
def test_staff_cannot_force_assign_a_conflicted_judge(judges, staff_client):
    app = make_report()
    _conflict(judges[0], app)
    staff_client.post(reverse("staff:report_action", args=[app.pk]), {"action": "assign", "judges": [judges[0].pk]})
    assert not app.assignments.exists()


@pytest.mark.django_db
def test_conflicted_judge_cannot_be_in_round2_meeting(judges):
    app = make_report(status="shortlisted")
    _conflict(judges[0], app)
    with pytest.raises(services.RuleError):
        services.schedule_round2(app, app.updated_at, "https://meet.example/x", [judges[0]], None)


@pytest.mark.django_db
def test_conflict_applies_to_every_report_of_that_organisation(judges):
    app = make_report()
    _conflict(judges[0], app)
    award = Award.objects.get(slug="kaizen")
    second = app.organisation.applications.create(award=award, form_version=award.current_form, status="pool")
    assert judges[0] not in services.suggested_judges(second)
