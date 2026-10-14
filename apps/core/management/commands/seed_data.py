"""
Load realistic demo data through the service layer (so every business rule
and audit entry applies). Safe to run more than once.

Run with:  python manage.py seed_data

Creates: 1 leader, 2 staff, 3 judges, 5 applicants (organisations), the two
demo awards (rounds, form v1, criteria), 10 reports, judge assignments and
some finished evaluations. All accounts use DEMO_PASSWORD (see .env.example).
Test data only: never run this against a real deployment.
"""
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import ApplicantProfile, JudgeProfile, User
from apps.applications import services as applications
from apps.applications.models import Application
from apps.assignments import services as assignments
from apps.awards import services as award_services
from apps.awards.models import Award, Criterion
from apps.core import demo_data
from apps.evaluations import services as evaluations
from apps.notifications.services import emails_off

DEFAULT_DEMO_PASSWORD = "Awards-Demo-2026"

LEADER = ("leader@awards.example", "A. Verma")
STAFF = [("staff@awards.example", "Meena Shah"), ("staff2@awards.example", "Arjun Mehta")]
JUDGES = [
    # email, name, expertise, priority
    ("kapoor@judges.example", "Dr. R. Kapoor", "Manufacturing, quality", 1),
    ("rao@judges.example", "Prof. N. Rao", "Operations, academia", 2),
    ("iyer@judges.example", "Ms. A. Iyer", "Strategy, finance", 3),
]
APPLICANTS = [
    # email, contact name, organisation, GSTIN (fake but well-formed), verified?
    ("priya@acme.example", "Priya Kulkarni", "Acme Precision Components Pvt Ltd", "27AAAAA0001A1Z5", True),
    ("ganesh@shriganesh.example", "Ravi Ganesh", "Shri Ganesh Polymers Ltd", "24AAAAA0002A1Z3", True),
    ("anita@coastalfoods.example", "Anita D'Souza", "Coastal Marine Foods", "32AAAAA0003A1Z1", True),
    ("vikram@vertexpharma.example", "Vikram Rao", "Vertex Pharma Labs", "36AAAAA0004A1Z9", True),
    ("meera@northstar.example", "Meera Iyer", "Northstar Auto Components", "29AAAAA0005A1Z7", False),
]


def question_key(label):
    return slugify(label)[:40].replace("-", "_")


class Command(BaseCommand):
    help = "Load demo users, awards, reports, assignments and evaluations (safe to re-run)."

    def handle(self, *args, **options):
        from django.conf import settings
        from django.core.management.base import CommandError
        if settings.SETTINGS_MODULE.endswith(".prod"):
            raise CommandError("seed_data loads DEMO accounts with a shared password. It refuses to run with "
                               "production settings. Create the first leader with createsuperuser instead.")
        with emails_off(), transaction.atomic():   # demo data: in-app notifications only, no emails
            self.load()

    def load(self):
        password = os.environ.get("DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD)
        leader = self.user(*LEADER, User.Role.LEADER, password)
        staff = [self.user(email, name, User.Role.STAFF, password) for email, name in STAFF]
        judges = [self.user(email, name, User.Role.JUDGE, password) for email, name, _, _ in JUDGES]
        applicants = [self.user(email, name, User.Role.APPLICANT, password) for email, name, *_ in APPLICANTS]

        awards = [self.award(slug, leader) for slug in demo_data.BUILT_AWARDS]
        for judge, (_, _, expertise, priority) in zip(judges, JUDGES, strict=True):
            profile, _ = JudgeProfile.objects.update_or_create(
                user=judge, defaults={"expertise": expertise, "priority": priority, "max_open_assignments": 10})
            profile.awards.set(awards)

        profiles = []
        for user, (_, contact, org, gstin, verified) in zip(applicants, APPLICANTS, strict=True):
            profile, _ = ApplicantProfile.objects.update_or_create(user=user, defaults={
                "organisation_name": org, "gstin": gstin, "holder_pan": gstin[2:12],
                "contact_name": contact, "sector": "Manufacturing", "organisation_size": "medium"})
            if verified and profile.verification_status != "verified":
                from apps.accounts.services import verify_organisation
                verify_organisation(profile, by=staff[0], approve=True, note="Seed data")
            profiles.append(profile)

        # A conflict recorded by staff: Rao must never judge Shri Ganesh Polymers.   [Rule 2]
        assignments.record_conflict(judge=judges[1], profile=profiles[1], by=staff[0],
                                    reason="Former adviser to the company")

        if Application.objects.exists():
            self.stdout.write("Reports already exist; skipping reports, assignments and evaluations.")
        else:
            self.reports(applicants, awards, staff[0], judges)

        self.print_logins(password)

    # --- helpers ------------------------------------------------------------

    def user(self, email, name, role, password):
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create_user(email=email, password=password, name=name, role=role)
        else:
            user.name, user.role, user.is_active = name, role, True
            if not user.has_usable_password() or not user.password:
                user.set_password(password)
            user.save()
        return user

    def award(self, slug, leader):
        base = next(a for a in demo_data.AWARDS if a["slug"] == slug)
        award = award_services.get_or_create_from_demo(slug)
        award.status = Award.Status.OPEN
        award.closes_on = award_services.parse_display_date(base["deadline"])
        award.save()
        if not award.rounds.exists():
            award_services.set_rounds(award, base["round_types"])
        if award.current_form is None:
            questions = [{"key": "org" if q.get("key") == "org" else question_key(q["label"]),
                          "label": q["label"], "type": q["type"], "required": q["type"] != "file",
                          "identifying": q["identifying"], "section": section["name"]}
                         for section in base["form_sections"] for q in section["questions"]]
            award_services.publish_form_version(award, questions, leader)
        if not award.criteria.exists():
            for round_number, criteria in ((1, base["criteria"]), (2, base["round2_criteria"])):
                for order, c in enumerate(criteria):
                    Criterion.objects.create(award=award, round_number=round_number, key=slugify(c["name"])[:50],
                                             label=c["name"], weight=c["weight"], order=order)
        return award

    def answers(self, form, organisation):
        """
        Only the questions marked identifying (and file names) mention the
        organisation, like a real entry; blind judging hides exactly those.
        """
        out = {}
        for q in form.questions:
            if q["type"] == "file":
                out[q["key"]] = f"{slugify(organisation)[:20]}-{q['key'][:20]}.pdf"
            elif q["key"] == "org":
                out[q["key"]] = organisation
            elif q.get("identifying"):
                out[q["key"]] = f"{organisation} ({q['label'].lower()})"
            else:
                out[q["key"]] = f"Sample answer to “{q['label']}”: what we did, the numbers, and what we learned."
        return out

    def reports(self, applicants, awards, staff, judges):
        """10 reports (5 applicants × 2 awards) at different stages."""
        plan = [
            # (applicant index, award index, stage)
            (0, 0, "scored"), (0, 1, "scored"),
            (1, 0, "in_review"), (1, 1, "assigned"),
            (2, 0, "scored"), (2, 1, "in_review"),
            (3, 0, "assigned"), (3, 1, "submitted"),
            (4, 0, "submitted"), (4, 1, "draft"),      # Northstar isn't verified yet
        ]
        for i, (a, w, stage) in enumerate(plan):
            applicant, award = applicants[a], awards[w]
            org = applicant.applicant_profile.organisation_name
            report = applications.create_draft(applicant=applicant, award=award, title=f"{award.name} 2026: {org}")
            applications.update(report, by=applicant, content=self.answers(report.form_version, org))
            if stage == "draft":
                continue
            applications.submit(report, by=applicant)
            if stage == "submitted":
                continue
            picks = assignments.eligible_judges(report)[:award.judges_per_report]
            made = [assignments.assign(report, judge, by=staff) for judge in picks]
            if stage == "assigned":
                continue
            for n, assignment in enumerate(made):
                if stage == "in_review" and n > 0:
                    break
                assignments.start_review(assignment, judge=assignment.judge)
                criteria = evaluations.criteria_for(assignment)
                scores = {key: 6 + (i + n + k) % 4 for k, key in enumerate(criteria)}
                evaluations.save(assignment, judge=assignment.judge, scores=scores,
                                 feedback="Clear evidence; good results.", submit=(stage == "scored"))
        self.stdout.write(self.style.SUCCESS("Created 10 reports with assignments and evaluations."))

    def print_logins(self, password):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Test logins (demo data only)"))
        rows = [(LEADER[0], "leader")] + [(e, "staff") for e, _ in STAFF] + \
               [(e, "judge") for e, *_ in JUDGES] + [(e, "applicant") for e, *_ in APPLICANTS]
        for email, role in rows:
            self.stdout.write(f"  {role:10} {email}")
        self.stdout.write(f"  Password for all: {password}")
