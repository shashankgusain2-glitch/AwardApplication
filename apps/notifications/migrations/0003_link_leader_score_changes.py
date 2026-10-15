"""
Point leaders' older score-change notifications at the page for that one request
(Confirm / Refuse), like new ones, instead of the general list.
"""
from django.db import migrations


def relink(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    ScoreChangeRequest = apps.get_model("evaluations", "ScoreChangeRequest")
    for note in Notification.objects.filter(user__role="leader", message__contains="· Score change by",
                                            link="/leadership/requests/"):
        reference = note.message.split(" ", 1)[0]
        req = (ScoreChangeRequest.objects.filter(evaluation__assignment__report__reference=reference,
                                                 created_at__lte=note.created_at)
               .order_by("-created_at").first())
        if req is not None:
            note.link = f"/leadership/requests/score/{req.pk}/"
            note.save(update_fields=["link"])


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_remove_leader_edit_notifications"),
        ("evaluations", "0002_two_step_approvals"),
    ]

    operations = [migrations.RunPython(relink, migrations.RunPython.noop)]
