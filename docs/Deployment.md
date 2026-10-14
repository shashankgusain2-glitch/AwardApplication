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

## Option A+: Supabase for the database and files (app on Render or Railway)

Supabase gives you a managed **PostgreSQL** and **file storage**. It does not run the Django app, so the app still goes on Render or Railway (Option A). Use only these two parts of Supabase:

- **Not** Supabase Auth: Django already handles login, roles, JWT and password reset.
- **Not** its auto-generated API or row-level security: all the rules (blind judging, conflicts, recorded score changes, who sees what) live in the Django code, and browsers must never talk to the database directly.

**1. Database**
1. Create a project in the **Mumbai (ap-south-1)** region and save the database password in your password manager.
2. In *Connect*, copy a connection string, then set `DATABASE_URL` to it with `?sslmode=require` on the end:
   - **Direct or session pooler (port 5432):** use this if your host supports it. Set `DB_TRANSACTION_POOLER=False`.
   - **Transaction pooler (port 6543):** many cheaper hosts only reach Supabase over IPv4, and this pooler works over IPv4. Set `DB_TRANSACTION_POOLER=True`. The app then turns off server-side cursors and connection reuse, which that pooler needs.
3. Run `python manage.py migrate --noinput` from the app (release command). Don't create tables in the Supabase dashboard.

**2. File storage (uploads)**
1. In *Storage*, create a **private** bucket (for example `awards-uploads`). Never make it public: downloads must go through the app's `/files/<id>/` permission check.
2. In *Storage → Settings*, turn on the S3 connection and create an access key.
3. Set:

| Variable | Value |
|---|---|
| `AWS_STORAGE_BUCKET_NAME` | `awards-uploads` |
| `AWS_S3_ENDPOINT_URL` | the S3 endpoint shown in Storage → Settings (it ends in `/storage/v1/s3`) |
| `AWS_S3_REGION_NAME` | your project's region, e.g. `ap-south-1` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | the access key from step 2 |
| `AWS_S3_ADDRESSING_STYLE` | `path` |

**3. Plans and backups**
- The free plan suits a **demo or staging** copy. Free projects can be paused when idle and have limited backups; check Supabase's current plan details.
- For real applicants, use a paid plan with daily backups, and still test a restore (see FUTURE_GOALS_AND_DEPLOYMENT.md §4.6).
- Moving away later only means a new `DATABASE_URL` (a `pg_dump` / restore) and new storage keys. No code changes.

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

## From an empty database to a working site (after launch)

Production starts **empty**: no demo people, no demo awards. `seed_data` refuses to run with production settings. Add the real data through the app:

1. **First leader:** `createsuperuser` (above). Log in at `/login/`; you land on the leadership overview.
2. **People** (leadership menu): add programme staff, judges and other leaders. Each gets an email with a link to set their password, so the email service must be working first. Applicants sign up themselves on `/signup/`.
3. **Awards** (staff menu, log in as a staff member): **+ New award**, then follow the four steps on the award page:
   - details and rounds
   - application form
   - scoring criteria (weights add up to 100 per round)
   - judge panel
   
   Then set the status to **Open**. The page lists anything still missing.
4. Applicants can now see the award on their dashboard and apply. Staff verify each organisation, then assign judges.
5. Check **Audit log** (leadership menu) to confirm actions are being recorded.

## Backup and restore test (before launch, then monthly)

```bash
pg_dump --format=custom --no-owner "$DATABASE_URL" > awards-backup.dump
```
Restore into a **new, empty** database (never over production), point a copy of the app at it, and log in:
```bash
pg_restore --no-owner --dbname "$SCRATCH_DATABASE_URL" awards-backup.dump
```
The test passes if you can log in as a leader and the Audit log and applications look right. Note the date in the runbook.

## Check before going live

```bash
docker compose -f docker-compose.prod.yml run --rm web python manage.py check --deploy
```
Expected: no issues, or only `security.W021` (HSTS preload), which stays off until the domain is final.
