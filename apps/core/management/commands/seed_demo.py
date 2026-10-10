"""
Load fake demo data: two awards, judges, organisations (with duplicates).

Run with:  python manage.py seed_demo
Never use real company names, PAN or GST numbers here.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load fake demo data for the two sample awards."

    def handle(self, *args, **options):
        # Filled in once the award, entry and judging models exist.
        self.stdout.write(self.style.WARNING("No demo data yet — models are not built."))
