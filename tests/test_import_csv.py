"""`python manage.py import_csv`: real people and awards from CSV files, for the live site."""
import shutil
from io import StringIO
from pathlib import Path

import pytest
from django.core import mail
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.awards.models import Award

from .factories import AwardFactory, JudgeFactory, LeaderFactory, StaffFactory

TEMPLATES = Path(__file__).resolve().parent.parent / "deploy" / "import-templates"
AWARD = "Business Excellence Award 2027"


@pytest.fixture
def leader(db):
    return LeaderFactory(email="lead@org.example")


@pytest.fixture
def folder(tmp_path):
    for f in TEMPLATES.glob("*.csv"):
        shutil.copy(f, tmp_path)
    return tmp_path


def run(folder, *flags):
    out = StringIO()
    call_command("import_csv", str(folder), "--by", "lead@org.example", *flags, stdout=out, stderr=out)
    return out.getvalue()


def test_dry_run_saves_nothing(leader, folder):
    output = run(folder)
    assert "Dry run" in output and "5 people added" in output and "1 awards added" in output
    assert User.objects.count() == 1 and not Award.objects.exists()


def test_templates_import_everything(leader, folder):
    run(folder, "--commit")

    award = Award.objects.get(name=AWARD)
    assert award.status == Award.Status.UPCOMING
    assert [r.kind for r in award.rounds.all()] == ["desk", "live"]
    assert award.blind_judging and award.entry_fee == 5000 and award.judges_per_report == 2
    assert award.manager.email == "award.manager@yourorg.example"
    assert list(award.staff.values_list("email", flat=True)) == ["staff.one@yourorg.example"]
    assert award.judge_panel.count() == 2
    judge = User.objects.get(email="judge.one@yourorg.example")
    assert judge.role == User.Role.JUDGE and judge.judge_profile.priority == 1
    assert not judge.has_usable_password()                     # they set it from the invite
    assert award.criteria.filter(round_number=1).count() == 3 and award.criteria.filter(round_number=2).count() == 2
    questions = award.current_form.questions
    assert [q["label"] for q in questions][0] == "Organisation name" and questions[0]["identifying"]
    assert questions[4]["type"] == "file" and not questions[4]["required"]
    assert AuditLog.objects.filter(user=leader).exists()       # every change is under the leader


def test_running_twice_changes_nothing(leader, folder):
    run(folder, "--commit")
    output = run(folder, "--commit")
    assert "0 people added, 5 people updated, 0 awards added, 1 awards updated" in output
    assert "0 form versions" in output
    award = Award.objects.get(name=AWARD)
    assert award.form_versions.count() == 1 and User.objects.count() == 6


def test_existing_panel_and_staff_are_kept(leader, folder):
    run(folder, "--commit")
    award = Award.objects.get(name=AWARD)
    extra_judge, extra_staff = JudgeFactory(awards=[award]), StaffFactory()
    award.staff.add(extra_staff)

    run(folder, "--commit")

    assert award.judge_panel.filter(user=extra_judge).exists()
    assert award.staff.filter(pk=extra_staff.pk).exists()


def test_one_bad_row_saves_nothing_and_names_every_problem(leader, folder):
    (folder / "criteria.csv").write_text(
        "award,round,label,weight\n"
        f"{AWARD},1,Leadership,30\n"
        f"{AWARD},1,Results,30\n"                                  # round 1 adds up to 60
        "No Such Award,1,Anything,100\n")
    with (folder / "people.csv").open("a") as f:
        f.write("someone@org.example,Some One,applicant,,,\n")

    with pytest.raises(CommandError, match="Nothing was saved"):
        run(folder, "--commit")

    assert User.objects.count() == 1 and not Award.objects.exists()


def test_problems_are_listed_with_file_and_line(leader, folder):
    with (folder / "people.csv").open("a") as f:
        f.write("someone@org.example,Some One,applicant,,,\n")
    err = StringIO()
    with pytest.raises(CommandError):
        call_command("import_csv", str(folder), "--by", "lead@org.example", stdout=StringIO(), stderr=err)
    assert "people.csv line 7: role must be one of" in err.getvalue()


def test_blind_award_without_desk_round_is_refused(leader, folder):
    awards = (folder / "awards.csv").read_text().replace("desk;live", "site")
    (folder / "awards.csv").write_text(awards)
    err = StringIO()
    with pytest.raises(CommandError):
        call_command("import_csv", str(folder), "--by", "lead@org.example", stdout=StringIO(), stderr=err)
    assert "Blind judging needs a desk review round" in err.getvalue()


def test_existing_account_with_another_role_is_not_changed(leader, folder):
    JudgeFactory(email="staff.one@yourorg.example")
    with pytest.raises(CommandError):
        run(folder, "--commit")
    assert User.objects.get(email="staff.one@yourorg.example").role == User.Role.JUDGE


def test_only_a_leader_can_import(db, folder):
    StaffFactory(email="lead@org.example")
    with pytest.raises(CommandError, match="must be an active leader"):
        run(folder)


def test_invite_emails_only_new_accounts(leader, folder, django_capture_on_commit_callbacks):
    run(folder, "--commit")
    (folder / "people.csv").write_text("email,name,role\nnew.judge@org.example,New Judge,judge\n"
                                       "judge.one@yourorg.example,Dr. Meera Iyer,judge\n")
    for name in ("awards", "criteria", "questions"):
        (folder / f"{name}.csv").unlink()
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):       # invites are sent after the commit
        run(folder, "--commit", "--invite")

    assert [m.to for m in mail.outbox] == [["new.judge@org.example"]]


def test_invite_needs_commit(leader, folder):
    with pytest.raises(CommandError, match="--invite only works with --commit"):
        run(folder, "--invite")


def test_existing_award_matched_by_name_keeps_its_status(leader, folder):
    award = AwardFactory(name=AWARD, status=Award.Status.OPEN)
    run(folder, "--commit")
    award.refresh_from_db()
    assert award.status == Award.Status.OPEN and award.entry_fee == 5000
    assert Award.objects.filter(name=AWARD).count() == 1
