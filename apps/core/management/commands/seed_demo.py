"""
Old name for the demo data command, kept so older instructions still work.
Runs `seed_data`.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Same as `python manage.py seed_data`."

    def handle(self, *args, **options):
        call_command("seed_data")
