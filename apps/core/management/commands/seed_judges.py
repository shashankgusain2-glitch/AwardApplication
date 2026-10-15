"""
Add a pool of spare demo judges and put them on every award's panel, so
new awards always have free judges to assign. Safe to run more than once:
existing judges are updated, not duplicated, and nobody is removed from a panel.

Run with:  python manage.py seed_judges
           python manage.py seed_judges --award <slug>   (one award only)

Run it again after creating a new award to add the pool to its panel.
All accounts use DEMO_PASSWORD (see .env.example).
Test data only: never run this against a real deployment.
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import JudgeProfile, User
from apps.awards import services as award_services
from apps.awards.models import Award
from apps.notifications.services import emails_off

from .seed_data import DEFAULT_DEMO_PASSWORD

POOL = [
    # email, name, expertise, priority (the seed_data judges are 1–3, so they stay first choice)
    ("mehta@judges.example", "Dr. S. Mehta", "Manufacturing, lean", 4),
    ("banerjee@judges.example", "Prof. A. Banerjee", "Quality, Six Sigma", 4),
    ("nair@judges.example", "Ms. L. Nair", "Healthcare, pharma", 5),
    ("singh@judges.example", "Mr. H. Singh", "Automotive, supply chain", 5),
    ("joshi@judges.example", "Dr. P. Joshi", "Food processing, safety", 5),
    ("reddy@judges.example", "Ms. K. Reddy", "IT, digital transformation", 6),
    ("chatterjee@judges.example", "Prof. D. Chatterjee", "Sustainability, energy", 6),
    ("pillai@judges.example", "Mr. V. Pillai", "Finance, governance", 6),
    ("desai@judges.example", "Ms. R. Desai", "People, HR practices", 7),
    ("khan@judges.example", "Dr. F. Khan", "Operations, academia", 7),
    ("gupta@judges.example", "Mr. N. Gupta", "Small business, startups", 8),
    ("menon@judges.example", "Ms. T. Menon", "Customer experience, services", 8),
]


class Command(BaseCommand):
    help = "Add spare demo judges and put them on every award's panel (safe to re-run)."

    def add_arguments(self, parser):
        parser.add_argument("--award", help="Only this award's slug (default: every award).")

    def handle(self, *args, **options):
        from django.conf import settings
        if (settings.SETTINGS_MODULE or os.environ.get("DJANGO_SETTINGS_MODULE", "")).endswith(".prod"):
            raise CommandError("seed_judges creates DEMO accounts with a shared password. It refuses to run "
                               "with production settings. Invite real judges from the People page instead.")
        awards = Award.objects.all()
        if options["award"]:
            awards = awards.filter(slug=options["award"])
            if not awards.exists():
                raise CommandError(f"No award with slug '{options['award']}'.")
        with emails_off(), transaction.atomic():
            judges = [self.judge(*row) for row in POOL]
            for award in awards:
                # set_panel replaces the panel, so keep everyone already on it. Audited as the system.
                current = list(User.objects.filter(judge_profile__awards=award))
                award_services.set_panel(award, by=None, judges=current + [j for j in judges if j not in current])
                self.stdout.write(f"  {award.name}: {award.judge_panel.count()} judges on the panel")
        self.stdout.write(self.style.SUCCESS(
            f"{len(judges)} spare judges ready. Password for all: "
            f"{os.environ.get('DEMO_PASSWORD', DEFAULT_DEMO_PASSWORD)}"))

    def judge(self, email, name, expertise, priority):
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            password = os.environ.get("DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD)
            user = User.objects.create_user(email=email, password=password, name=name, role=User.Role.JUDGE)
        else:
            user.name, user.role, user.is_active = name, User.Role.JUDGE, True
            user.save()
        JudgeProfile.objects.update_or_create(
            user=user, defaults={"expertise": expertise, "priority": priority, "max_open_assignments": 10})
        return user
