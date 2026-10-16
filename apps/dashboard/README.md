# apps/dashboard/

**Leadership: one view across all awards**, on the real database.

## What it does in the application

| Page | Address | What leadership does |
|---|---|---|
| Overview | `/leadership/` | Real counts: every award's stage, manager, entries, judging progress and open requests in one table |
| Awards and managers | `/leadership/awards/` | Every award with its **award manager** and **staff**; flags awards with no active manager. **+ New award** (only leaders create awards, and pick the manager while creating it) and **Team** (change the manager or the staff) |
| People | `/leadership/people/` | Add staff, award managers, judges and leaders (each gets an email with a set-your-password link); deactivate, reactivate, resend the invite. Staff and managers are listed with the awards they are on. Applicants sign up themselves |
| Approve award results | `/leadership/results/` | Each award's result sent by its manager: the ranking, then **Approve award result** (published: results board, applicants told) or **Send back** with a note. Below, every award's result status and what's still to do. Leaders don't decide single applications |

Leadership **can't change scores**. They approve or reject; only scored reports can be approved.

## Files

| File | What it does |
|---|---|
| `views.py` | The leadership pages: overview, awards and managers, approve award results, people |
| `urls.py` | The `/leadership/...` addresses |
| `models.py` | No tables of its own; it reads from the other apps |
| [migrations/](migrations/) | Empty: this app has no tables |
