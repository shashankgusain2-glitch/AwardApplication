"""
When applicants can apply to an award.

  - Staff can open an award as soon as its form is published; criteria and a judge
    panel are only needed before judges are assigned (or the award moves to Judging).
  - An Upcoming award opens by itself on its opening date (if its form is published),
    and an Open award closes by itself after its closing date.
"""
from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.applications import services as applications
from apps.assignments import services as assignments
from apps.audit.models import AuditLog
from apps.awards import services as award_services
from apps.awards.models import Award
from apps.core.services import BusinessRuleError

from .factories import ApplicationFactory, AwardFactory, JudgeFactory, StaffFactory

TODAY = date(2026, 10, 14)


def _new_award(**fields):
    """A brand-new award as staff make it: a published form, but no criteria and no judges yet."""
    award = AwardFactory(status=Award.Status.UPCOMING, **fields)
    award.criteria.all().delete()
    return award


@pytest.mark.django_db
def test_staff_can_open_an_award_with_only_a_form():
    award = _new_award()
    award_services.set_status(award, by=StaffFactory(), status=Award.Status.OPEN)
    assert award.status == Award.Status.OPEN


@pytest.mark.django_db
def test_an_award_without_a_form_cannot_open():
    award = _new_award()
    award.form_versions.all().delete()
    with pytest.raises(BusinessRuleError, match="Publish the application form"):
        award_services.set_status(award, by=StaffFactory(), status=Award.Status.OPEN)


@pytest.mark.django_db
def test_award_opens_by_itself_on_its_opening_date():
    award = _new_award(opens_on=TODAY, closes_on=TODAY + timedelta(30))
    later = _new_award(opens_on=TODAY + timedelta(1))
    award_services.apply_date_rules(today=TODAY)
    award.refresh_from_db()
    later.refresh_from_db()
    assert award.status == Award.Status.OPEN and later.status == Award.Status.UPCOMING
    entry = AuditLog.objects.get(entity="award", entity_id=str(award.pk), action="status_change")
    assert entry.user is None and entry.changes["automatic"] == "opening date reached"


@pytest.mark.django_db
def test_award_without_a_form_or_dates_does_not_open_by_itself():
    no_form = _new_award(opens_on=TODAY)
    no_form.form_versions.all().delete()
    no_date = _new_award(opens_on=None)
    already_closed = _new_award(opens_on=TODAY - timedelta(10), closes_on=TODAY - timedelta(1))
    award_services.apply_date_rules(today=TODAY)
    for award in (no_form, no_date, already_closed):
        award.refresh_from_db()
        assert award.status == Award.Status.UPCOMING


@pytest.mark.django_db
def test_award_closes_by_itself_after_its_closing_date_and_drafts_cannot_be_submitted():
    award = AwardFactory(closes_on=TODAY - timedelta(1))
    draft = ApplicationFactory(award=award, status="draft", submitted_at=None)
    award_services.apply_date_rules(today=TODAY)
    award.refresh_from_db()
    assert award.status == Award.Status.CLOSED
    with pytest.raises(BusinessRuleError, match="isn't taking applications any more"):
        applications.submit(draft, by=draft.applicant)


@pytest.mark.django_db
def test_staff_cannot_reopen_an_award_whose_closing_date_has_passed():
    award = _new_award(closes_on=timezone.localdate() - timedelta(1))
    with pytest.raises(BusinessRuleError, match="closing date has passed"):
        award_services.set_status(award, by=StaffFactory(), status=Award.Status.OPEN)


@pytest.mark.django_db
def test_judges_need_criteria_and_a_panel_first():
    award = _new_award()
    award_services.set_status(award, by=StaffFactory(), status=Award.Status.OPEN)
    report = ApplicationFactory(award=award)
    judge = JudgeFactory()
    with pytest.raises(BusinessRuleError, match="isn't ready for judging: Round 1 criteria"):
        assignments.assign(report, judge, by=StaffFactory())
    with pytest.raises(BusinessRuleError, match="Not ready for judging"):
        award_services.set_status(award, by=StaffFactory(), status=Award.Status.JUDGING)


@pytest.mark.django_db
def test_a_page_visit_opens_a_due_award_so_applicants_can_apply(applicant_client):
    award = _new_award(name="Water Saving Award", opens_on=timezone.localdate())
    pick = applicant_client.get(reverse("entries:form")).content.decode()   # the middleware runs first
    award.refresh_from_db()
    assert award.status == Award.Status.OPEN
    assert "Water Saving Award" in pick and "Opening soon" not in pick
    applicant_client.post(reverse("entries:form", args=[award.slug]), {"action": "start", "title": "Our entry"})
    assert award.applications.count() == 1
