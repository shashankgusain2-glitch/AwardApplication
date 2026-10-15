"""
Leaders no longer take part in applicants' edit requests (staff check them, the award manager
confirms) or in re-evaluations (the award manager decides). Remove the notifications leaders
got about those under the old two-step rule, so their inbox only holds what is theirs to act on.
"""
from django.db import migrations
from django.db.models import Q


def remove(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    old_rule = Q(message__contains="· Edit after submitting") | (
        Q(message__contains="· Re-evaluation of the result") & Q(message__contains="waiting for a leader"))
    Notification.objects.filter(old_rule, user__role="leader").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
        ("accounts", "0006_duplicate_candidates"),
    ]

    operations = [migrations.RunPython(remove, migrations.RunPython.noop)]
