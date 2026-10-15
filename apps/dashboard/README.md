# apps/dashboard/

**Leadership: one view across all awards**, on the real database.

## What it does in the application

| Page | Address | What leadership does |
|---|---|---|
| Overview | `/leadership/` | Real counts: every award's stage, manager, entries, judging progress and open requests in one table |
| Awards and managers | `/leadership/awards/` | Every award with its **award manager** and **staff**; flags awards with no active manager. **+ New award** (only leaders create awards, and pick the manager while creating it) and **Team** (change the manager or the staff) |
| All applications | `/leadership/review/` | The full list of submitted applications (filter by status and award) with how many judges have submitted, the average total and the spread |
| People | `/leadership/people/` | Add staff, award managers, judges and leaders (each gets an email with a set-your-password link); deactivate, reactivate, resend the invite. Staff and managers are listed with the awards they are on. Applicants sign up themselves |
| Audit log | `/leadership/audit/` | Every important action (who, what, which record, when), filter by person, action, record type and date; read-only |
| Approve results | `/leadership/results/` | Reports every judge has scored, best first, with each judge's total and feedback. Approve or reject (with a note); big disagreements between judges are flagged |

Leadership **can't change scores**. They approve or reject; only scored reports can be approved.

## Files

| File | What it does |
|---|---|
| `views.py` | The leadership pages: overview, awards and managers, all applications, approve / reject, people, audit log |
| `urls.py` | The `/leadership/...` addresses |
| `models.py` | No tables of its own; it reads from the other apps |
| [migrations/](migrations/) | Empty: this app has no tables |
