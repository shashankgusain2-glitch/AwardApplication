"""
R4 notifications: the right person gets an in-app notification and an
email when something they care about changes. Emails go out only after
the change is saved, and a broken email server never undoes the change.
"""
from unittest import mock

import pytest
from django.urls import reverse

from apps.accounts import services as account_services
from apps.applications import services as application_services
from apps.assignments import services as assignment_services
from apps.evaluations import services as evaluation_services
from apps.notifications.models import Notification

from .conftest import ACCOUNTS, seeded_client
from .factories import (
    ApplicantProfileFactory,
    ApplicationFactory,
    AwardFactory,
    JudgeFactory,
    LeaderFactory,
    ManagerFactory,
    StaffFactory,
)


@pytest.fixture
def saved(django_capture_on_commit_callbacks):
    """`with saved():` runs the block, then the after-save callbacks (the emails), like a real commit."""
    return lambda: django_capture_on_commit_callbacks(execute=True)


@pytest.mark.django_db
def test_verifying_an_organisation_tells_the_applicant(saved, mailoutbox):
    profile = ApplicantProfileFactory(verification_status="pending")
    with saved():
        account_services.verify_organisation(profile, by=StaffFactory(), approve=True)
    note = Notification.objects.get(user=profile.user)
    assert "is verified" in note.message
    assert len(mailoutbox) == 1 and mailoutbox[0].to == [profile.user.email]
    assert "http://localhost:8000/applicant/organisation/" in mailoutbox[0].body


@pytest.mark.django_db
def test_assigning_tells_the_judge_and_declining_tells_staff(saved, mailoutbox):
    award = AwardFactory()
    staff, judge = StaffFactory(), JudgeFactory(awards=[award])
    with saved():
        assignment = assignment_services.assign(ApplicationFactory(award=award), judge, by=staff)
    assert Notification.objects.filter(user=judge, kind="assignment").exists()
    with saved():
        assignment_services.decline(assignment, judge=judge)
    assert "declined" in Notification.objects.get(user=staff).message
    assert {m.to[0] for m in mailoutbox} == {judge.email, staff.email}


@pytest.mark.django_db
def test_submit_edit_request_and_decision_reach_the_right_people():
    award = AwardFactory()
    applicant = ApplicantProfileFactory().user
    staff = StaffFactory()
    manager = ManagerFactory(awards=[award])
    app = application_services.create_draft(applicant=applicant, award=award, title="Entry")
    application_services.update(app, by=applicant, content={"org": "X", "city": "Pune", "story": "Y"})
    application_services.submit(app, by=applicant)
    assert "was submitted" in Notification.objects.filter(user=applicant).first().message

    application_services.request_edit(app, by=applicant, reason="Wrong figure")
    assert "the applicant asks" in Notification.objects.get(user=staff).message
    leader = LeaderFactory()
    application_services.decide_edit(app, by=staff, allow=True)
    assert "passed it to the award manager" in Notification.objects.filter(user=applicant).first().message
    assert "waiting for you to confirm" in Notification.objects.filter(user=manager).first().message
    assert not Notification.objects.filter(user=leader).exists()
    application_services.decide_edit(app, by=manager, allow=True)
    assert "approved by the award manager" in Notification.objects.filter(user=applicant).first().message


@pytest.mark.django_db
def test_leader_decision_tells_the_applicant(saved, mailoutbox):
    app = ApplicationFactory(status="scored")
    with saved():
        application_services.change_status(app, by=LeaderFactory(), new_status="approved", note="Well done")
    note = Notification.objects.get(user=app.applicant)
    assert "approved" in note.message and "Well done" in note.message
    assert mailoutbox[-1].to == [app.applicant.email]


@pytest.mark.django_db
def test_score_change_request_and_decision():
    award = AwardFactory()
    world = {"staff": StaffFactory(), "judge_a": JudgeFactory(awards=[award])}
    a1 = assignment_services.assign(ApplicationFactory(award=award), world["judge_a"], by=world["staff"])
    assignment_services.start_review(a1, judge=world["judge_a"])
    evaluation = evaluation_services.save(a1, judge=world["judge_a"], scores={"approach": 7, "results": 8},
                                          submit=True)
    request = evaluation_services.request_change(evaluation, judge=world["judge_a"], reason="Misread")
    assert Notification.objects.filter(user=world["staff"], kind="request").exists()
    evaluation_services.decide_change(request, by=world["staff"], approve=True)
    assert "passed it to leadership" in Notification.objects.filter(user=world["judge_a"]).first().message
    evaluation_services.decide_change(request, by=LeaderFactory(), approve=True)
    assert "approved by leadership" in Notification.objects.filter(user=world["judge_a"]).first().message


@pytest.mark.django_db
def test_a_broken_email_server_never_undoes_the_action(saved):
    profile = ApplicantProfileFactory(verification_status="pending")
    with mock.patch("apps.notifications.services.send_mail", side_effect=OSError("SMTP down")), saved():
        account_services.verify_organisation(profile, by=StaffFactory(), approve=True)
    profile.refresh_from_db()
    assert profile.verification_status == "verified"
    assert Notification.objects.filter(user=profile.user).exists()


@pytest.mark.django_db
def test_seed_data_sends_no_email(seeded, mailoutbox):
    assert Notification.objects.exists()       # in-app notifications are still created
    assert mailoutbox == []


# --- The notifications page ---------------------------------------------------------

@pytest.mark.django_db
def test_inbox_shows_only_my_notifications_and_the_unread_count(seeded):
    judge = seeded_client("judge")
    page = judge.get(reverse("notifications:inbox")).content.decode()
    mine = Notification.objects.filter(user__email=ACCOUNTS["judge"])
    assert mine.exists() and mine.first().message[:30] in page
    others = Notification.objects.exclude(user__email=ACCOUNTS["judge"]).first()
    assert others.message not in page
    assert f"{mine.filter(is_read=False).count()} unread" in page


@pytest.mark.django_db
def test_opening_marks_read_and_follows_only_internal_links(seeded):
    judge = seeded_client("judge")
    note = Notification.objects.filter(user__email=ACCOUNTS["judge"]).first()
    response = judge.post(reverse("notifications:open", args=[note.pk]))
    assert response.status_code == 302 and response["Location"] == note.link
    note.refresh_from_db()
    assert note.is_read

    note.link = "https://evil.example/phish"
    note.save()
    assert judge.post(reverse("notifications:open", args=[note.pk]))["Location"] == reverse("notifications:inbox")


@pytest.mark.django_db
def test_cannot_open_someone_elses_notification(seeded):
    other = Notification.objects.exclude(user__email=ACCOUNTS["judge"]).first()
    assert seeded_client("judge").post(reverse("notifications:open", args=[other.pk])).status_code == 404


@pytest.mark.django_db
def test_mark_all_read(seeded):
    judge = seeded_client("judge")
    judge.post(reverse("notifications:read_all"))
    assert not Notification.objects.filter(user__email=ACCOUNTS["judge"], is_read=False).exists()


@pytest.mark.django_db
def test_inbox_needs_login(client):
    response = client.get(reverse("notifications:inbox"))
    assert response.status_code == 302 and reverse("accounts:login") in response["Location"]
