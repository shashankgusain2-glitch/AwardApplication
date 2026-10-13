# Awards Platform

One web platform to run many award programmes. Applicants apply, judges score, staff run each award, and leadership sees every award in one place.

> **Status:** every user's workflow from the 12 Oct meeting works end to end: **applicant, judge (Rounds 1 and 2), staff and leadership**. See [docs/User-Journeys.md](docs/User-Journeys.md).

## What works now: one award cycle, every user

```text
Applicant  verify email → register organisation (GSTIN + PAN) → choose 1 of 2 events
           → short form (save and come back) → submit
Staff      check the report → confirm (into the report pool) or reject (failed proof check)
           → assign judges: conflicts excluded, workload balanced, N judges per report
Judge      email link → judging tab → accept / decline (declined → back to the pool)
           → grade, saving partway → submit → report "Judged"
           → change a grade: ask staff → staff allow → change with a reason (recorded)
Staff      shortlist → schedule a Round 2 online meeting with a group of judges
Judges     grade the organisation after the meeting → "Round 2 graded"
Leadership dashboard: drafts, being checked, pool, under evaluation, judged,
           rejected, Round 2, rankings, judge workload, recent activity
Applicant  sees each status change; can ask staff to allow changes to the report
```

**Demo accounts** (log in by verifying the email; the code is shown on screen):

| Who | Email | Lands on |
|---|---|---|
| Applicant | any email | Register organisation → Events |
| Staff | `staff@uec.example` | http://localhost:8000/staff/ |
| Judges | `kapoor@judges.example`, `rao@judges.example`, `iyer@judges.example` | http://localhost:8000/judge/ |
| Leadership | `leader@uec.example` | http://localhost:8000/leadership/ |

Judges can also use the **login link** staff send them (shown on the Judges page as the "demo outbox").

**Demo notes**
- No real email is sent; codes and links are shown on screen and printed in the server log.
- GSTIN and PAN are checked for the right **format** only. Test values: GSTIN `27ABCDE1234F1Z5`, PAN `PQRSX6789K`.
- Business Excellence needs 3 judges per report, Kaizen 2. Staff can change this on the Events page.

## The four rules this platform keeps

1. **Blind judging:** a judge cannot see who applied. *(not built: not asked for in the 12 Oct meeting; Round 2 is a live meeting)*
2. **No conflicts:** a judge is never given a report they have a conflict with. ✅ *staff record conflicts; the system refuses those judges*
3. **Score audit:** the system records who changed a score, and why. ✅ *needs staff permission and a reason; records are permanent*
4. **Form versions:** old applications still open correctly after questions change. ✅ *staff publish a new version; old reports keep theirs*

## Run it

### Option A: Docker (easiest)

Needs [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.

```bash
docker compose up --build
```

Open http://localhost:8000. The database tables, the 2 events and the staff account are created automatically.

### Option B: Python on your machine

Needs Python 3.12+. Uses SQLite, so no database server is needed.

```bash
python -m venv .venv
.venv\Scripts\activate           # Mac/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env             # then set DATABASE_URL=sqlite:///db.sqlite3
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://localhost:8000

## Run the tests

```bash
pytest
```

With Docker: `docker compose exec web pytest`. See [docs/testing.md](docs/testing.md) for what the tests check and what they don't.

## Project layout

| Folder | What's inside |
|---|---|
| `config/` | Project-wide settings and the top-level address map |
| `apps/accounts/` | Users and email verification |
| `apps/awards/` | Events (awards) and their versioned forms |
| `apps/entries/` | Organisations, applications and the applicant pages |
| `apps/judging/` | Judges, conflicts, assignments, grading, score changes, Round 2 (rules in `services.py`) |
| `apps/staff/` | Staff pages: reports, judges, requests, events and forms, activity |
| `apps/dashboard/` | Leadership dashboard |
| `apps/core/` | Home page, activity log, demo accounts |
| `templates/`, `static/` | Pages and styles |
| `tests/` | Tests, including one file per rule in `tests/rules/` |
| `docs/` | Roadmap, user journeys, architecture, decisions, daily reports, meeting notes |

Each file explained: [docs/Code-Guide.md](docs/Code-Guide.md). All documents: [docs/README.md](docs/README.md).
