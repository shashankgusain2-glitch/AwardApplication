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

## Production notes

Use `DJANGO_SETTINGS_MODULE=config.settings.prod`. It **requires** `SECRET_KEY` and `ALLOWED_HOSTS` from the environment, forces HTTPS, secure cookies and HSTS. Set `JWT_SIGNING_KEY` (32+ characters), `CORS_ALLOWED_ORIGINS` for the frontend, and a real `EMAIL_BACKEND`. Never run `seed_data` in production.
