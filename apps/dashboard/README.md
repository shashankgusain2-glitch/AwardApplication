# apps/dashboard/

**Leadership: one view across all awards**, on the real database.

## What it does in the application

| Page | Address | What leadership does |
|---|---|---|
| Overview | `/leadership/` | Real counts: every award's stage, entries, judging progress and open requests in one table |
| All applications | `/leadership/review/` | The full list of submitted applications (filter by status and award) with how many judges have submitted, the average total and the spread |
| Approve results | `/leadership/results/` | Reports every judge has scored, best first, with each judge's total and feedback. Approve or reject (with a note); big disagreements between judges are flagged |

Leadership **can't change scores**. They approve or reject; only scored reports can be approved.

## Files

| File | What it does |
|---|---|
| `views.py` | The leadership pages and the approve / reject action |
| `urls.py` | The `/leadership/...` addresses |
| `models.py` | No tables of its own; it reads from the other apps |
| [migrations/](migrations/) | Empty: this app has no tables |
