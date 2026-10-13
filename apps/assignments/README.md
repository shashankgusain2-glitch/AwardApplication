# apps/assignments/

**Which judge grades which report, and conflicts recorded by staff.**

| File | What it does |
|---|---|
| `models.py` | `JudgeAssignment` (judge, report, round, status; unique per judge/report/round) and `ConflictOfInterest` (Rule 2) |
| `services.py` | Who may judge a report (panel, no conflict, under workload limit, priority order), assign, reassign, judge accepts or declines (declined → back to the pool), staff record conflicts, and **what a judge may see of a report** (blind judging, Rule 1) |
| `api/` | `/api/v1/assignments/`, `/api/v1/judge/my-assignments/`, `/api/v1/conflicts/` |
| `admin.py` | Assignments and conflicts |
| [migrations/](migrations/) | Database tables for this app |
