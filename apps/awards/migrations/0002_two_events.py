"""Create the two demo events with short, starter-friendly forms."""
import datetime

from django.db import migrations

EVENTS = [
    {
        "slug": "business-excellence",
        "name": "Business Excellence Award",
        "summary": "For organisations that show excellence in leadership, ways of working and results.",
        "deadline": datetime.date(2026, 11, 30),
        "questions": [
            {"key": "about", "label": "Tell us about your organisation in a few lines", "type": "textarea", "required": True},
            {"key": "employees", "label": "Number of employees", "type": "number", "required": True},
            {"key": "achievement", "label": "Your biggest achievement in the last 3 years", "type": "textarea", "required": True},
            {"key": "results", "label": "Key results, with numbers", "type": "textarea", "required": True},
            {"key": "contact", "label": "Contact person and phone number", "type": "text", "required": True},
        ],
    },
    {
        "slug": "kaizen",
        "name": "Kaizen Competition",
        "summary": "For shop-floor teams that made a small change with a big, measurable result.",
        "deadline": datetime.date(2026, 12, 15),
        "questions": [
            {"key": "team", "label": "Team name", "type": "text", "required": True},
            {"key": "members", "label": "Number of team members", "type": "number", "required": True},
            {"key": "problem", "label": "What was the problem?", "type": "textarea", "required": True},
            {"key": "change", "label": "What did your team change?", "type": "textarea", "required": True},
            {"key": "result", "label": "What is the result, with numbers?", "type": "textarea", "required": True},
        ],
    },
]


def create_events(apps, schema_editor):
    Award = apps.get_model("awards", "Award")
    FormVersion = apps.get_model("awards", "FormVersion")
    for event in EVENTS:
        award, _ = Award.objects.get_or_create(
            slug=event["slug"],
            defaults={"name": event["name"], "summary": event["summary"], "deadline": event["deadline"]},
        )
        FormVersion.objects.get_or_create(award=award, number=1, defaults={"questions": event["questions"]})


def remove_events(apps, schema_editor):
    apps.get_model("awards", "Award").objects.filter(slug__in=[e["slug"] for e in EVENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [("awards", "0001_initial")]
    operations = [migrations.RunPython(create_events, remove_events)]
