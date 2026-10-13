"""
Awards and everything staff configure without code.

Planned models:
- Award: the programme (e.g. "Business Excellence"). Lasts for years.
- AwardCycle: one year of an award. Holds the per-award settings:
  number of rounds (1 or 2), blind judging on/off, judges per entry,
  entry fee flag, open/close dates.
- FormVersion: the application questions for a cycle, stored as JSON.
  Never edited after publishing; changes create a new version.   [Rule 4]
  Questions can be marked "identifying" so blind judging hides them. [Rule 1]
- Criterion: a scoring question with weight and max score, per round.
- AwardStaff: links a user to an award as Member or Working staff.
"""
from django.db import models


class AwardSetting(models.Model):
    """
    The settings staff saved for one award on the Award settings screen
    (round types, blind judging, judges per entry, ...).

    Stored in the database so every user sees the same settings: a judge
    sees the blind-judging setting that staff saved. The award's default
    settings and content still come from apps/core/demo_data.py until the
    full Award tables above are built.
    """
    slug = models.SlugField(unique=True)
    data = models.JSONField(default=dict)
    updated_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings for {self.slug}"
