# Deployment runbook

How to put the Awards Platform on a real server. The full checklists (security, pre-launch, monitoring, risks) are in [FUTURE_GOALS_AND_DEPLOYMENT.md](../FUTURE_GOALS_AND_DEPLOYMENT.md) §4. This page is the short "do this, then this" version.

## What's in the repository

| File | Purpose |
|---|---|
| `Dockerfile.prod` | Production image: installs `requirements/prod.txt`, collects static files at build time, runs **Gunicorn** as a non-root user |
| `requirements/prod.txt` | Gunicorn, Sentry, django-storages (S3) on top of `base.txt` (WhiteNoise is in `base.txt`) |
| `config/settings/prod.py` | `DEBUG=False`, required secrets and hosts, HTTPS redirect, secure cookies, HSTS, WhiteNoise compressed static files, S3 for uploads when a bucket is set, logs to stdout, Sentry when `SENTRY_DSN` is set |
| `.env.production.example` | Every production variable, with placeholders. Copy it to `.env.production` on the server (git ignores that file) |
| `docker-compose.prod.yml` | Single-server option: the app plus Nginx. The database is a **managed** PostgreSQL |
| `deploy/nginx.conf` | HTTPS, HTTP→HTTPS redirect, 12 MB upload limit, rate limit on the web login |
| `.github/workflows/ci.yml` | Lint, migration check, tests, dependency scan, and a job that **builds the production image and runs `check --deploy`** |

## Option A: Render or Railway (simplest)

1. Create a managed PostgreSQL 16 database and copy its connection URL.
2. Create a web service from this repository using **`Dockerfile.prod`**.
3. Add the variables from `.env.production.example`, with real values (`DATABASE_URL` from step 1, fresh secrets, your domain in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`).
4. Set the **release / pre-deploy command** to `python manage.py migrate --noinput`.
5. Set the health check path to `/api/v1/health/`.
6. Deploy, then add your domain; the platform issues the HTTPS certificate.
7. Create the first leader account (see "First account" below).

## Option B: one VPS with Docker

```bash
git clone https://github.com/shashankgusain2-glitch/AwardApplication.git && cd AwardApplication
```
```bash
cp .env.production.example .env.production
```
Edit `.env.production` with real values. Replace `awards.example.org` in `deploy/nginx.conf` with your domain and get a certificate (for example, `certbot certonly --standalone -d your.domain` before starting Nginx). Then:
```bash
docker compose -f docker-compose.prod.yml build
```
```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate --noinput
```
```bash
docker compose -f docker-compose.prod.yml up -d
```

## Every release

1. CI is green on `main` (tests and the `prod-image` job).
2. Back up the database (managed platforms: take a manual snapshot).
3. Deploy the new image, then run `python manage.py migrate --noinput`.
4. Smoke test: `https://your.domain/api/v1/health/` returns `"database": "ok"`; log in as each role once.
5. If something is wrong: redeploy the previous image (see "Rollback" in FUTURE_GOALS_AND_DEPLOYMENT.md §4.9).

## First account

Run once, in a one-off container (it gets the **leader** role):
```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py createsuperuser
```
Create every other staff, judge and leader account from that leader account. **Never run `seed_data` in production**, and don't set `DEMO_PASSWORD` there.

## Check before going live

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py check --deploy
```
Expected: no issues, or only `security.W021` (HSTS preload), which stays off until the domain is final.
