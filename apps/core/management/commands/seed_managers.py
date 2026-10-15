"""
Add a pool of spare demo award managers, ready for awards created later.
They manage nothing yet: a leader picks one per award on
Leadership → Awards and managers (+ New award, or Team).
Safe to run more than once: existing accounts are updated, not duplicated,
and nobody is removed from an award.

Run with:  python manage.py seed_managers

All accounts use DEMO_PASSWORD (see .env.example).
Test data only: never run this against a real deployment.
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User

from .seed_data import DEFAULT_DEMO_PASSWORD

POOL = [
    # email, name
    ("manager.anand@awards.example", "Anand Rao"),
    ("manager.fatima@awards.example", "Fatima Sheikh"),
    ("manager.gurpreet@awards.example", "Gurpreet Kaur"),
    ("manager.joseph@awards.example", "Joseph Mathew"),
    ("manager.lakshmi@awards.example", "Lakshmi Iyer"),
]


class Command(BaseCommand):
    help = "Add spare demo award managers for future awards (safe to re-run)."

    def handle(self, *args, **options):
        from django.conf import settings
        if (settings.SETTINGS_MODULE or os.environ.get("DJANGO_SETTINGS_MODULE", "")).endswith(".prod"):
            raise CommandError("seed_managers creates DEMO accounts with a shared password. It refuses to run "
                               "with production settings. Add real managers from the People page instead.")
        password = os.environ.get("DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD)
        with transaction.atomic():
            for email, name in POOL:
                user = User.objects.filter(email__iexact=email).first()
                if user is None:
                    User.objects.create_user(email=email, password=password, name=name, role=User.Role.MANAGER)
                else:
                    user.name, user.role, user.is_active = name, User.Role.MANAGER, True
                    user.save()
                self.stdout.write(f"  manager  {email}  ({name})")
        self.stdout.write(self.style.SUCCESS(f"{len(POOL)} spare award managers ready. Password for all: {password}"))
