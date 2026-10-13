"""Replace the is_leader flag with one role per user."""
from django.db import migrations, models


def leaders_keep_their_role(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_leader=True).update(role="leader")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("applicant", "Applicant"), ("staff", "Staff"), ("judge", "Judge"), ("leader", "Leader")],
                default="applicant",
                max_length=20,
            ),
        ),
        migrations.RunPython(leaders_keep_their_role, migrations.RunPython.noop),
        migrations.RemoveField(model_name="user", name="is_leader"),
    ]
