"""Grading criteria and judges per report for the two demo events."""
from django.db import migrations

SETTINGS = {
    "business-excellence": {
        "judges_per_report": 3,
        "criteria": [
            {"key": "leadership", "label": "Leadership and strategy", "weight": 30},
            {"key": "people", "label": "Processes and people", "weight": 30},
            {"key": "results", "label": "Results and impact", "weight": 40},
        ],
        "round2_criteria": [
            {"key": "story", "label": "Clarity of the story", "weight": 30},
            {"key": "evidence", "label": "Evidence behind the claims", "weight": 40},
            {"key": "answers", "label": "Answers to the judges", "weight": 30},
        ],
    },
    "kaizen": {
        "judges_per_report": 2,
        "criteria": [
            {"key": "problem", "label": "Problem clarity", "weight": 25},
            {"key": "cause", "label": "Root cause found", "weight": 25},
            {"key": "change", "label": "Improvement made", "weight": 25},
            {"key": "result", "label": "Result and how it is kept going", "weight": 25},
        ],
        "round2_criteria": [
            {"key": "explain", "label": "Team explains the change clearly", "weight": 40},
            {"key": "proof", "label": "Proof the result is real", "weight": 30},
            {"key": "spread", "label": "Can it spread to other lines", "weight": 30},
        ],
    },
}


def fill(apps, schema_editor):
    Award = apps.get_model("awards", "Award")
    for slug, values in SETTINGS.items():
        Award.objects.filter(slug=slug).update(**values)


class Migration(migrations.Migration):
    dependencies = [("awards", "0003_award_criteria_award_judges_per_report_and_more")]
    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
