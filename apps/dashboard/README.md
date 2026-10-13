# apps/dashboard/

**Leadership: one view across all awards.**

## What it does in the application

| Page | Address | What leadership does |
|---|---|---|
| Overview | `/leadership/` | Every award's stage, entries, judging progress and flags in one table |
| Review queue | `/leadership/review/` | Decide ties, big score gaps and appeals |
| Approve results | `/leadership/results/` | Approve the winners or send them back |

Leadership **can't change scores**. They approve or send back.

## Files

| File | What it does |
|---|---|
| `views.py` | Builds the leadership pages |
| `urls.py` | The `/leadership/...` addresses |
| `models.py` | No tables of its own; it reads from the other apps |
| [migrations/](migrations/) | Empty: this app has no tables |
