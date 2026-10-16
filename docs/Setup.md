# Setup

## Option A: Docker (recommended)

Needs Docker Desktop running.

```bash
docker compose up --build
```

This starts PostgreSQL and the app, runs migrations, loads demo data (`seed_data`) and serves http://localhost:8000.

| What | Where |
|---|---|
| Website | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ |
| Health | http://localhost:8000/api/v1/health/ |

Useful commands while it runs:

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web pytest
docker compose exec web ruff check .
docker compose logs web
```

## Option B: Python on your machine

Needs Python 3.11+ (3.12 recommended). Uses SQLite unless you set a PostgreSQL `DATABASE_URL`.

1. **Virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   source .venv/bin/activate       # macOS / Linux
   ```
2. **Install packages** (`requirements/base.txt` = runtime, `requirements/dev.txt` = runtime + tests + lint)
   ```bash
   pip install -r requirements/dev.txt
   ```
3. **Settings file**
   ```bash
   cp .env.example .env
   ```
   For SQLite, set `DATABASE_URL=sqlite:///db.sqlite3` in `.env`. Settings are split into `config/settings/base.py`, `dev.py`, `test.py`, `prod.py`; the default is `dev`.
4. **Database tables**
   ```bash
   python manage.py migrate
   ```
5. **Demo data** (prints the test logins; password = `DEMO_PASSWORD` in `.env`)
   ```bash
   python manage.py seed_data
   ```
6. **Admin account** (gets the leader role)
   ```bash
   python manage.py createsuperuser
   ```
7. **Run**
   ```bash
   python manage.py runserver
   ```
8. **Tests and lint**
   ```bash
   pytest
   ruff check .
   ```

## Demo accounts

`seed_data` creates these accounts. **They all share one password: the `DEMO_PASSWORD` value in `.env`** (copied from `.env.example`). Running `seed_data` again resets every account to that password. These are test accounts for your own machine only. Never create them in production.

Log in at http://localhost:8000/login/. There is one login form for everybody, and it sends each person to their own home page.

| Role | Email | Name | Home page after login | What you can try |
|---|---|---|---|---|
| Leadership | `leader@awards.example` | A. Verma | `/leadership/` | Overview of every award; create an award and pick its manager; People; approve an award's result as a whole; results board |
| Award manager | `manager@awards.example` | R. Kulkarni | `/staff/` | Manages both demo awards: set-up pages, team, confirm edit and score-change requests, re-evaluations, *Prepare results* (decide each entry, send the award's result); doesn't assign judges |
| Staff | `staff@awards.example` | Meena Shah | `/staff/` | On both demo awards: verify organisations, accept or decline entries, duplicate review, form builder, assign judges, check requests |
| Staff | `staff2@awards.example` | Arjun Mehta | `/staff/` | Same, but on Kaizen only (staff only see their own awards) |
| Judge | `kapoor@judges.example` | Dr. R. Kapoor | `/judge/` | Only their own assignments; Accept or Decline; score; ask to change a score |
| Judge | `rao@judges.example` | Prof. N. Rao | `/judge/` | A different set of assignments; has a recorded conflict with Shri Ganesh Polymers |
| Judge | `iyer@judges.example` | Ms. A. Iyer | `/judge/` | A different set of assignments again |
| Applicant | `priya@acme.example` | Priya Kulkarni | `/applicant/` | Their own applications (Acme Precision Components, verified) |
| Applicant | `ganesh@shriganesh.example` | Ravi Ganesh | `/applicant/` | Shri Ganesh Polymers (verified) |
| Applicant | `anita@coastalfoods.example` | Anita D'Souza | `/applicant/` | Coastal Marine Foods (verified) |
| Applicant | `vikram@vertexpharma.example` | Vikram Rao | `/applicant/` | Vertex Pharma Labs (verified) |
| Applicant | `meera@northstar.example` | Meera Iyer | `/applicant/` | Northstar Auto Components, **not verified yet**, so they see the "Staff are verifying" message |
| Applicant | `sunil@shreeganesh.example` | Sunil Patel | `/applicant/` | A second registration of Shri Ganesh Polymers (same PAN): shows up on Duplicate review |
| Applicant | `accounts@coastalmarine.example` | Joseph Fernandes | `/applicant/` | "COASTAL MARINE FOODS PVT. LTD.": a duplicate by name, with a Kaizen draft |
| Applicant | `neha@vertexlabs.example` | Neha Rao | `/applicant/` | "Vertex Pharma Laboratories": a possible duplicate (similar name), no entries |

Quick checks:

- Log in as one role and open another role's address (for example `/staff/` as a judge). You get the "403 not allowed" page.
- Open `/admin/` with any account above. You are sent to the admin login, because only admin accounts (made with `createsuperuser`) can open it.
- Log out before switching accounts.

To see the password in your own terminal:

```bash
grep DEMO_PASSWORD .env
```

## Test the API with Postman

Import the collection and environment from [postman/](../postman/README.md), set `demo_password` in the environment, and run the collection top to bottom (116 requests, each with tests). The checklist is in [postman/CHECKLIST.md](../postman/CHECKLIST.md). Interactive API docs: http://localhost:8000/api/docs/.

## Production notes

Step-by-step deployment: [Deployment.md](Deployment.md).

Use `DJANGO_SETTINGS_MODULE=config.settings.prod`. It **requires** `SECRET_KEY` and `ALLOWED_HOSTS` from the environment, forces HTTPS, secure cookies and HSTS. Set `JWT_SIGNING_KEY` (32+ characters), `CORS_ALLOWED_ORIGINS` for the frontend, and a real `EMAIL_BACKEND`. Never run `seed_data` in production.
