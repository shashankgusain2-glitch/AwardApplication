"""
Email is the login and one `name` field replaces first/last name.
Existing names are copied before the old columns are removed.
"""
import django.utils.timezone
from django.db import migrations, models


def copy_names(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.all():
        user.name = f"{user.first_name} {user.last_name}".strip()
        user.email = user.email.strip().lower()
        user.save(update_fields=["name", "email"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.RunPython(copy_names, migrations.RunPython.noop),
        migrations.RemoveField(model_name="user", name="first_name"),
        migrations.RemoveField(model_name="user", name="last_name"),
        migrations.RemoveField(model_name="user", name="username"),
        migrations.AddField(
            model_name="user",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="user",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
