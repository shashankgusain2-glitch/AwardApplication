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
