"""
Import real people and awards from CSV files, for setting up the live site.

Run with:  python manage.py import_csv <folder> --by <leader email>            (dry run: checks only)
           python manage.py import_csv <folder> --by <leader email> --commit   (saves)
           ... --commit --invite   (also emails each NEW account a "set your password" link)

The folder may hold any of these files (UTF-8, first row is the header; see
deploy/import-templates/ for examples):

  people.csv     email, name, role, expertise, priority, max_open_assignments
  awards.csv     name, rounds, sector, summary, opens_on, closes_on, applicant_type,
                 judges_per_report, blind_judging, entry_fee, manager, staff, judges
  criteria.csv   award, round, label, weight
  questions.csv  award, section, subsection, label, type, required, identifying

Everything goes through the service layer, so the usual rules apply (weights add up
to 100 per round, blind judging needs a desk round, ...) and every change is in the
audit log under the --by leader. The whole import is one transaction: if any row is
wrong, nothing is saved and every problem is listed with its file and line.

Safe to run again: people are matched by email and awards by name. Existing people
keep their role; existing awards keep their status. Staff and judges listed for an
award are added to its team and panel; nobody already there is removed. Criteria
are replaced. Questions publish a new form version only if they changed.
New awards start as Upcoming: open them in the app once they are ready.
"""
import csv
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from apps.accounts import services as account_services
from apps.accounts.models import JudgeProfile, User
from apps.awards import services as award_services
from apps.awards.models import Award
from apps.core.services import BusinessRuleError
from apps.notifications.services import emails_off

ROLES = {"staff", "manager", "judge", "leader"}            # applicants sign up themselves
TRUE, FALSE = {"yes", "y", "true", "1"}, {"no", "n", "false", "0", ""}
QUESTION_TYPES = {"text": "text", "short text": "text", "textarea": "textarea", "long text": "textarea",
                  "file": "file"}
ROUND_KINDS = {"desk": "desk", "desk review": "desk", "site": "site", "site visit": "site",
               "live": "live", "live presentation": "live"}
APPLICANT_TYPES = {**{v: v for v in Award.ApplicantType.values},
                   **{label.lower(): v for v, label in Award.ApplicantType.choices}}
QUESTION_FIELDS = ["key", "label", "type", "section", "subsection", "required", "identifying"]


class RowError(Exception):
    pass


class Rollback(Exception):
    pass


def _rows(path, required):
    """(line number, row) pairs with stripped values. Checks the header first."""
    with path.open(newline="", encoding="utf-8-sig") as f:      # utf-8-sig: Excel's "CSV UTF-8" adds a BOM
        reader = csv.DictReader(f)
        header = [h.strip().lower() for h in (reader.fieldnames or [])]
        missing = [c for c in required if c not in header]
        if missing:
            raise CommandError(f"{path.name}: missing column(s) {', '.join(missing)}. Found: {', '.join(header)}")
        reader.fieldnames = header
        for n, row in enumerate(reader, start=2):
            row = {k: (v or "").strip() for k, v in row.items() if k}
            if any(row.values()):                                # skip blank lines
                yield n, row


def _bool(value, column):
    if value.lower() in TRUE:
        return True
    if value.lower() in FALSE:
        return False
    raise RowError(f"{column} must be yes or no, not '{value}'.")


def _int(value, column, default=None):
    if value == "" and default is not None:
        return default
    try:
        return int(value)
    except ValueError:
        raise RowError(f"{column} must be a whole number, not '{value}'.") from None


def _date(value, column):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise RowError(f"{column} must be a date like 2026-12-15 or 15 Dec 2026, not '{value}'.")


def _emails(value):
    return [e.strip().lower() for e in value.replace(",", ";").split(";") if e.strip()]


class Command(BaseCommand):
    help = "Import real staff, judges, managers, leaders and awards from CSV files (dry run unless --commit)."

    def add_arguments(self, parser):
        parser.add_argument("folder", help="Folder holding people.csv, awards.csv, criteria.csv, questions.csv")
        parser.add_argument("--by", required=True, help="Email of the leader doing the import (for the audit log)")
        parser.add_argument("--commit", action="store_true", help="Save. Without it nothing is written.")
        parser.add_argument("--invite", action="store_true",
                            help="Email each NEW account a set-your-password link (needs --commit and working email)")

    def handle(self, *args, folder, by, commit, invite, **options):
        root = Path(folder)
        if not root.is_dir():
            raise CommandError(f"No folder '{folder}'.")
        files = {name: root / f"{name}.csv" for name in ("people", "awards", "criteria", "questions")}
        if not any(p.exists() for p in files.values()):
            raise CommandError(f"'{folder}' has none of people.csv, awards.csv, criteria.csv, questions.csv.")
        leader = User.objects.filter(email__iexact=by.strip(), is_active=True).first()
        if leader is None or not (leader.role == User.Role.LEADER or leader.is_superuser):
            raise CommandError(f"'{by}' must be an active leader account. Create one with createsuperuser first.")
        if invite and not commit:
            raise CommandError("--invite only works with --commit.")

        self.leader, self.errors, self.created_users = leader, [], []
        self.counts = {k: 0 for k in ("people added", "people updated", "awards added", "awards updated",
                                      "criteria sets", "form versions")}
        try:
            with emails_off(), transaction.atomic():
                if files["people"].exists():
                    self.import_people(files["people"])
                if files["awards"].exists():
                    self.import_awards(files["awards"])
                if files["criteria"].exists():
                    self.import_criteria(files["criteria"])
                if files["questions"].exists():
                    self.import_questions(files["questions"])
                if self.errors or not commit:
                    raise Rollback
                if invite:
                    for user in self.created_users:
                        link = account_services.invite(user, by=leader)     # sent after the commit
                        if settings.SHOW_INVITE_LINKS:
                            self.stdout.write(f"  invite link for {user.email}: {link}")
        except Rollback:
            pass

        summary = ", ".join(f"{v} {k}" for k, v in self.counts.items())
        if self.errors:
            for where, message in self.errors:
                self.stderr.write(f"  {where}: {message}")
            raise CommandError(f"{len(self.errors)} problem(s) found. Nothing was saved. Fix the rows above and "
                               f"run again.")
        if not commit:
            self.stdout.write(self.style.WARNING(f"Dry run, nothing saved. Would do: {summary}. "
                                                 f"Run again with --commit to save."))
            return
        self.stdout.write(self.style.SUCCESS(f"Imported: {summary}."))
        if self.created_users and not invite:
            self.stdout.write("New accounts have no password yet. Send invites from the People page, "
                              "or run again with --invite.")

    # Each row (or award) runs in its own savepoint, so one bad row doesn't stop the
    # others from being checked; the outer transaction still rolls back if any failed.
    def attempt(self, where, fn, *args):
        try:
            with transaction.atomic():
                return fn(*args)
        except (RowError, BusinessRuleError) as e:
            self.errors.append((where, str(e)))
        except DatabaseError as e:
            self.errors.append((where, f"database refused the row: {e}"))
        return None

    # --- people -------------------------------------------------------------------

    def import_people(self, path):
        seen = set()
        for n, row in _rows(path, ["email", "name", "role"]):
            where = f"people.csv line {n}"
            if row["email"].lower() in seen:
                self.errors.append((where, f"{row['email']} is listed twice."))
                continue
            seen.add(row["email"].lower())
            self.attempt(where, self.person, row)

    def person(self, row):
        email, name, role = row["email"].lower(), row["name"], row["role"].lower()
        if "@" not in email:
            raise RowError(f"'{row['email']}' isn't an email address.")
        if not name:
            raise RowError("name is empty.")
        if role not in ROLES:
            raise RowError(f"role must be one of {', '.join(sorted(ROLES))}, not '{row['role']}'. "
                           f"(Applicants sign up themselves.)")
        judge_fields = {}
        if role == "judge":
            judge_fields = {"expertise": row.get("expertise", ""),
                            "priority": _int(row.get("priority", ""), "priority", 5),
                            "max_open_assignments": _int(row.get("max_open_assignments", ""),
                                                         "max_open_assignments", 10)}
            if not 1 <= judge_fields["priority"] <= 99:
                raise RowError("priority must be from 1 (first choice) to 99.")
            if judge_fields["max_open_assignments"] < 1:
                raise RowError("max_open_assignments must be at least 1.")

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = account_services.create_account(created_by=self.leader, email=email, name=name, role=role,
                                                   **judge_fields)
            self.created_users.append(user)
            self.counts["people added"] += 1
            return
        if user.role != role:
            raise RowError(f"{email} already exists as {user.get_role_display()}. Change roles in the app, "
                           f"not by import.")
        if user.name != name:
            user.name = name
            user.save(update_fields=["name", "updated_at"])
        if role == "judge":
            JudgeProfile.objects.update_or_create(user=user, defaults=judge_fields)
        self.counts["people updated"] += 1

    # --- awards ---------------------------------------------------------------------

    def import_awards(self, path):
        seen = set()
        for n, row in _rows(path, ["name", "rounds"]):
            where = f"awards.csv line {n}"
            if row["name"].lower() in seen:
                self.errors.append((where, f"'{row['name']}' is listed twice."))
                continue
            seen.add(row["name"].lower())
            self.attempt(where, self.award, row)

    def award(self, row):
        rounds = []
        for part in row["rounds"].replace(",", ";").split(";"):
            if part.strip():
                kind = ROUND_KINDS.get(part.strip().lower())
                if kind is None:
                    raise RowError(f"round '{part.strip()}' must be desk, site or live.")
                rounds.append(kind)
        applicant_type = APPLICANT_TYPES.get((row.get("applicant_type") or "organisation").lower())
        if applicant_type is None:
            raise RowError("applicant_type must be organisation, team or unit.")
        fields = {
            "name": row["name"], "sector": row.get("sector", ""), "summary": row.get("summary", ""),
            "opens_on": _date(row.get("opens_on", ""), "opens_on"),
            "closes_on": _date(row.get("closes_on", ""), "closes_on"),
            "applicant_type": applicant_type,
            "judges_per_report": _int(row.get("judges_per_report", ""), "judges_per_report", 2),
            "blind_judging": _bool(row.get("blind_judging", ""), "blind_judging"),
            "entry_fee": _int(row.get("entry_fee", ""), "entry_fee", 0),
        }
        manager = self.user_with_role(row.get("manager", ""), User.Role.MANAGER, "manager")
        staff = [self.user_with_role(e, User.Role.STAFF, "staff") for e in _emails(row.get("staff", ""))]
        judges = [self.user_with_role(e, User.Role.JUDGE, "judges") for e in _emails(row.get("judges", ""))]

        award = Award.objects.filter(name__iexact=row["name"]).first()
        if award is None:
            award = award_services.create_award(by=self.leader, rounds=rounds, **fields)
            self.counts["awards added"] += 1
        else:
            award_services.update_award(award, by=self.leader, rounds=rounds, **fields)
            self.counts["awards updated"] += 1

        # Add to the team and panel; keep anyone already there (they may have been added in the app).
        if staff or manager:
            current_staff = list(award.staff.all())
            award_services.set_team(award, by=self.leader, staff=current_staff + [s for s in staff
                                                                                  if s not in current_staff],
                                    manager=manager, change_manager=manager is not None)
        if judges:
            current = list(User.objects.filter(judge_profile__awards=award))
            award_services.set_panel(award, by=self.leader, judges=current + [j for j in judges if j not in current])

    def user_with_role(self, email, role, column):
        if not email:
            return None
        user = User.objects.filter(email__iexact=email.strip()).first()
        if user is None:
            raise RowError(f"{column}: no account {email}. Add it to people.csv first.")
        if user.role != role:
            raise RowError(f"{column}: {email} is {user.get_role_display()}, not {role.label}.")
        return user

    # --- criteria and questions (grouped by award) -------------------------------------

    def grouped(self, path, required, filename):
        groups = {}
        for n, row in _rows(path, required):
            award = Award.objects.filter(name__iexact=row["award"]).first()
            if award is None:
                self.errors.append((f"{filename} line {n}", f"no award named '{row['award']}' "
                                                            f"(add it to awards.csv)."))
                continue
            groups.setdefault(award, []).append((n, row))
        return groups

    def import_criteria(self, path):
        for award, rows in self.grouped(path, ["award", "round", "label", "weight"], "criteria.csv").items():
            where = f"criteria.csv lines {rows[0][0]}-{rows[-1][0]} ({award.name})"
            self.attempt(where, self.criteria, award, rows)

    def criteria(self, award, rows):
        award_services.save_criteria(award, by=self.leader, rows=[
            {"round_number": row["round"], "label": row["label"], "weight": row["weight"]} for _, row in rows])
        self.counts["criteria sets"] += 1

    def import_questions(self, path):
        for award, rows in self.grouped(path, ["award", "label", "type"], "questions.csv").items():
            where = f"questions.csv lines {rows[0][0]}-{rows[-1][0]} ({award.name})"
            self.attempt(where, self.questions, award, rows)

    def questions(self, award, rows):
        editor_rows = []
        for n, row in rows:
            kind = QUESTION_TYPES.get(row["type"].lower())
            if kind is None:
                raise RowError(f"line {n}: type must be text, textarea or file, not '{row['type']}'.")
            try:
                editor_rows.append({**row, "type": kind, "key": row.get("key", ""),
                                    "required": _bool(row.get("required", ""), "required"),
                                    "identifying": _bool(row.get("identifying", ""), "identifying")})
            except RowError as e:
                raise RowError(f"line {n}: {e}") from None
        questions = award_services.questions_from_editor(editor_rows)
        current = award.current_form
        if current and [{f: q.get(f, "") for f in QUESTION_FIELDS} for q in current.questions] == \
                [{f: q.get(f, "") for f in QUESTION_FIELDS} for q in questions]:
            return                                               # unchanged: don't publish a new version
        award_services.publish_form_version(award, questions, self.leader)
        self.counts["form versions"] += 1
