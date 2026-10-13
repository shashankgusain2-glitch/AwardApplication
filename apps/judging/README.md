# apps/judging/

**Judging: the judge's screens.**

## What it does in the application

| Page | Address | What the judge does |
|---|---|---|
| My assignments | `/judge/` | See assigned entries with their round type (desk review, site visit, live presentation); accept or decline |
| Score an entry | `/judge/score/<entry>/` | Read the entry and score each criterion 1–10 |

**Blind judging (Rule 1) happens here.** In a blind award's desk-review round, the company name, location and file names are **removed on the server before the page is built**, so they can't leak. Site visits and live presentations are never blind.

## Files

| File | What it does |
|---|---|
| `views.py` | Builds the judge pages; decides what the judge is allowed to see |
| `urls.py` | The `/judge/...` addresses |
| `models.py` | **Planned** tables: JudgeProfile, Assignment, Score, ScoreChange (who changed a score, when and why, for Rule 3) |
| [migrations/](migrations/) | Database changes for this app (none yet) |

From the 12 Oct meeting: judges don't declare conflicts; staff record them.
