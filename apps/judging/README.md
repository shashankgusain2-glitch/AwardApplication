# apps/judging/

**Judging: the judge's screens**, on the real database (`apps/assignments/` and `apps/evaluations/` services).

## What it does in the application

| Page | Address | What the judge does |
|---|---|---|
| My assignments | `/judge/` | Their **own assignments**, with the round type and status. Accept or Decline (declined reports go back to the pool). This is where a judge lands after logging in |
| Answer an assignment | `/judge/assignments/<id>/respond/` | The Accept / Decline buttons. Accepting opens the grading page |
| Grade a report | `/judge/score/<assignment id>/` | Read the report as the judge may see it, score each criterion 1–10 with comments and overall feedback, save midway, submit. After submitting: ask staff to change a score, and change it with a reason once allowed (Rule 3; every change is listed) |
| Score an entry (menu) | `/judge/score/` | Opens the first report being graded, or the list |

A judge only ever reaches their own assignments: another judge's gives **404**.

**Blind judging (Rule 1) happens on the server** in `report_for_judge()` (`apps/assignments/services.py`): in a blind award's desk-review round, identifying answers, the report title, the applicant's name and uploaded file names are removed before the page is built. Site visits and live presentations are never blind.

## Files

| File | What it does |
|---|---|
| `views.py` | The judge pages: assignments, accept/decline, grading (save, submit, ask to change, change) |
| `urls.py` | The `/judge/...` addresses |
| `models.py` | No tables here: assignments and evaluations live in `apps/assignments/` and `apps/evaluations/` |
| [migrations/](migrations/) | Empty: this app has no tables |

From the 12 Oct meeting: judges don't declare conflicts; staff record them.
