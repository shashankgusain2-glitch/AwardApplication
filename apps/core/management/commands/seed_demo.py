"""
Create demo accounts so every role can log in. Safe to run more than once.

Run with:  python manage.py seed_demo

Staff, judge and leader accounts are never self-registered; in the demo
they're created here (in real use, by an admin at /admin/).
All accounts use the demo password from the DEMO_PASSWORD environment
variable (default below; see .env.example). Test accounts only: never
use these on a real deployment.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

DEFAULT_DEMO_PASSWORD = "Awards-Demo-2026"

DEMO_ACCOUNTS = [
    # email, first name, last name, role
    ("priya@acme.example", "Priya", "Kulkarni", "applicant"),   # owns the sample applications
    ("staff@awards.example", "Meena", "Shah", "staff"),
    ("kapoor@judges.example", "R.", "Kapoor", "judge"),         # most sample assignments
    ("rao@judges.example", "N.", "Rao", "judge"),               # one assignment (K-0012)
    ("leader@awards.example", "A.", "Verma", "leader"),
]


class Command(BaseCommand):
    help = "Create demo accounts for every role (applicant, staff, judge, leader)."

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD)
        User = get_user_model()
        for email, first, last, role in DEMO_ACCOUNTS:
            user, created = User.objects.get_or_create(
                email=email, defaults={"username": email, "first_name": first, "last_name": last, "role": role})
            if created or not user.password or not user.has_usable_password():
                user.set_password(password)   # stored hashed
            user.role = role
            user.save()
            self.stdout.write(f"{'Created' if created else 'Ready  '} {role:9} {email}")
        self.stdout.write(self.style.SUCCESS(
            "Demo accounts ready. Password: the DEMO_PASSWORD setting (see .env.example)."))
