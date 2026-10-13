"""
Create the demo people so every workflow can be tried. Safe to run again.

Run with:  python manage.py seed_demo
Log in as any of them by verifying their email on the website.
All names and emails are fake.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.awards.models import Award

STAFF_EMAIL = "staff@uec.example"
LEADER_EMAIL = "leader@uec.example"
JUDGES = [
    # email, name, expertise, priority, max load
    ("kapoor@judges.example", "Dr. R. Kapoor", "Manufacturing, quality", 1, 10),
    ("rao@judges.example", "Prof. N. Rao", "Operations, academia", 2, 10),
    ("iyer@judges.example", "Ms. A. Iyer", "Strategy, finance", 3, 8),
]


class Command(BaseCommand):
    help = "Create demo staff, leader and judges (safe to run more than once)."

    def handle(self, *args, **options):
        from apps.judging.services import get_or_create_judge

        User = get_user_model()
        staff, _ = User.objects.get_or_create(email=STAFF_EMAIL, defaults={"username": STAFF_EMAIL})
        staff.is_staff = True
        staff.save()

        leader, _ = User.objects.get_or_create(email=LEADER_EMAIL, defaults={"username": LEADER_EMAIL})
        leader.is_leader = True
        leader.save()

        events = list(Award.objects.all())
        for email, name, expertise, priority, max_load in JUDGES:
            get_or_create_judge(email, name, expertise, priority, max_load, events)

        self.stdout.write(self.style.SUCCESS(
            f"Ready. Log in by verifying: staff {STAFF_EMAIL}, leader {LEADER_EMAIL}, "
            f"judges {', '.join(j[0] for j in JUDGES)}"))
