# Awards Platform

One web platform to run many award programmes. Applicants apply, judges score, staff run each award, and leadership sees every award in one place. Staff set up each award (rounds, blind judging, form questions) on screen, without code.

> **Status:** project skeleton. Features are being built phase by phase. See [docs/Roadmap.md](docs/Roadmap.md).

## The four rules this platform keeps

1. **Blind judging:** if an award uses blind judging, a judge cannot see who applied.
2. **No conflicts:** a judge is never given an application they have a conflict of interest with.
3. **Score audit:** the system records who changed a score, and why.
4. **Form versions:** last year's applications still open correctly after the questions change.

## Run it

### Option A: Docker (easiest)

Needs [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.

```bash
docker compose up --build
```

Open http://localhost:8000

### Option B: Python on your machine

Needs Python 3.12+ and PostgreSQL 16 (or use SQLite for a quick try).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # then edit .env if needed
python manage.py migrate
python manage.py runserver
```

Open http://localhost:8000

### Admin login

```bash
python manage.py createsuperuser
```

Then open http://localhost:8000/admin

### Demo data

```bash
python manage.py seed_demo
```

All demo data is fake.

## Run the tests

```bash
pytest
```

See [docs/testing.md](docs/testing.md) for what the tests check and what they don't.

## Project layout

| Folder | What's inside |
|---|---|
| `config/` | Project-wide settings |
| `apps/` | The application: `accounts`, `awards`, `entries`, `judging`, `dashboard`, `core` |
| `templates/`, `static/` | Pages, CSS, images |
| `tests/` | Tests, including one file per rule in `tests/rules/` |
| `docs/` | Roadmap, user workflows, architecture, decisions, daily reports, meeting notes |

Full details: [docs/Architecture.md](docs/Architecture.md). All documents: [docs/README.md](docs/README.md).
