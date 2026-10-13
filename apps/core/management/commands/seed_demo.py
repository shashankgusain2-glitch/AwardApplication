"""
Create the demo staff account so the staff side of the workflow can be tried.

Run with:  python manage.py seed_demo
Log in as staff by verifying the email below on the website.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

STAFF_EMAIL = "staff@awards.example"


class Command(BaseCommand):
    help = "Create the demo staff account (safe to run more than once)."

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(email=STAFF_EMAIL, defaults={"username": STAFF_EMAIL})
        if not user.is_staff:
            user.is_staff = True
            user.save()
        self.stdout.write(self.style.SUCCESS(
            f"Staff account {'created' if created else 'ready'}: verify {STAFF_EMAIL} on the website to log in as staff."))
