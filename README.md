# Awards Platform

One web platform to run many award programmes. Applicants apply, judges score, staff run each award, and leadership sees every award in one place.

> **Status:** the **applicant workflow** works end to end (from the 12 Oct meeting). Judging, leadership and award setup come next. See [docs/Roadmap.md](docs/Roadmap.md).

## What works now: the applicant workflow

```text
Home → Verify email (6-digit code) → Register organisation (GSTIN + PAN)
     → Events (2) → Fill a short form (save and come back) → Submit
     → See status: In report pool → Assigned → Being judged → Judged
     → Need a change? Ask staff → staff approve → edit and resubmit
```

| Page | Address |
|---|---|
| Home (the 2 events) | http://localhost:8000/ |
| Verify email | http://localhost:8000/verify/ |
| Register organisation | http://localhost:8000/register/ |
| Events | http://localhost:8000/events/ |
| Your application and status | http://localhost:8000/applications/&lt;id&gt;/ |
| Staff: approve edits, move status | http://localhost:8000/staff/ |

**Demo notes**
- No real email is sent. The 6-digit code is shown on screen (and printed in the server log).
- GSTIN and PAN are checked for the right **format** only. Use test values, e.g. GSTIN `27ABCDE1234F1Z5`, PAN `PQRSX6789K`.
- **To log in as staff**, verify the email `staff@awards.example` (created automatically).
- Judging isn't built yet, so staff move a report to "Assigned", "Being judged" and "Judged" by hand.

## The four rules this platform keeps

1. **Blind judging:** if an award uses blind judging, a judge cannot see who applied. *(planned, with judging)*
2. **No conflicts:** a judge is never given an application they have a conflict of interest with. *(planned; staff check conflicts)*
3. **Score audit:** the system records who changed a score, and why. *(planned, with judging)*
4. **Form versions:** last year's applications still open correctly after the questions change. ✅ *working and tested*

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
| `apps/entries/` | Organisations, applications, the applicant pages and the staff page |
| `apps/core/` | Home page and shared bits |
| `apps/judging/`, `apps/dashboard/` | Planned (judges, leadership) |
| `templates/`, `static/` | Pages and styles |
| `tests/` | Tests, including one file per rule in `tests/rules/` |
| `docs/` | Roadmap, user journeys, architecture, decisions, daily reports, meeting notes |

Each file explained: [docs/Code-Guide.md](docs/Code-Guide.md). All documents: [docs/README.md](docs/README.md).
