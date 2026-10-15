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
| `render.yaml` | Render Blueprint: the web service, health check, and every variable (secrets generated or asked for) |
| `railway.json` | Railway: build with `Dockerfile.prod`, health check |
| `deploy/start.sh` | Start-up: Gunicorn on the platform's `$PORT`; migrations first when `RUN_MIGRATIONS_ON_START=true` |

The app finds the address Render or Railway gives it by itself (`RENDER_EXTERNAL_HOSTNAME`, `RAILWAY_PUBLIC_DOMAIN`), so `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `SITE_URL` are only needed for your own domain.

## The chosen setup: Supabase (database + files) with Render or Railway (the app)

You need four free accounts: **GitHub** (you have it), **Supabase**, **Render** *or* **Railway**, and an **email service** (Brevo, Resend or SendGrid all have free tiers). Do the steps in this order. Paste secrets only into the dashboards, never into chat, email or the repository.

### Step 1: Supabase (about 10 minutes)
1. Sign up at supabase.com → **New project**. Name `awards-platform`, region **Mumbai (ap-south-1)**. Save the database password in a password manager.
2. **Connect** → choose the **Session pooler** connection string (it works over IPv4, which Render and Railway need). Copy it and add `?sslmode=require` at the end. This is your `DATABASE_URL`. Keep `DB_TRANSACTION_POOLER=False`.
3. **Storage** → **New bucket** `awards-uploads`, **Public: off**. Then **Storage → Settings → S3 connection**: copy the endpoint and region, and **create an access key** (ID and secret).

### Step 2a: Render (recommended; about 10 minutes)
1. Sign up at render.com with GitHub. **New → Blueprint** → pick `AwardApplication`. Render reads `render.yaml`.
2. Fill in the values it asks for:
   - `DATABASE_URL`: from step 1.2.
   - `AWS_*`: from step 1.3.
   - `EMAIL_*` and `DEFAULT_FROM_EMAIL`: from step 3. You can leave them empty for now; `SHOW_INVITE_LINKS=True` covers you.
   - `SENTRY_DSN`: optional.
   
   `SECRET_KEY` and `JWT_SIGNING_KEY` are generated for you.
3. **Apply**. The first build takes a few minutes; migrations run on start. When it shows *Live*, open `https://<name>.onrender.com/api/v1/health/`. It should say `"database": "ok"`.
4. The free plan sleeps when idle, so the first visit takes about a minute. Switch the plan to *Starter* before real users arrive.

### Step 2b: Railway (alternative)
1. Sign up at railway.com with GitHub → **New project → Deploy from GitHub repo** → `AwardApplication`. Railway reads `railway.json` and builds `Dockerfile.prod`.
2. **Variables**: add the same values as in `render.yaml`:
   - `DJANGO_SETTINGS_MODULE=config.settings.prod`
   - `RUN_MIGRATIONS_ON_START=true`
   - a `SECRET_KEY` and `JWT_SIGNING_KEY` (make each with `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
   - `DATABASE_URL`, `AWS_*`, `EMAIL_*`, `SHOW_INVITE_LINKS=True`
3. **Settings → Networking → Generate domain**. Open `https://<name>.up.railway.app/api/v1/health/` and check it says `"database": "ok"`.

Use **one** of Render or Railway for the live site. Keeping the second one as a staging copy is fine, but give it its **own** Supabase project, so tests never touch real data.

### Step 3: Email (so invites and notifications arrive)
1. Sign up with an email service and verify your sending address or domain. For a domain, add the SPF and DKIM records it shows you.
2. Copy its **SMTP** details into the variables: `EMAIL_HOST`, `EMAIL_PORT=587`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`.
3. Test: add yourself as a staff member under *People*. If the email arrives, set `SHOW_INVITE_LINKS=False`.
4. If no email arrives and the logs show a connection timeout, the hosting plan may block outgoing mail ports. Some free plans do; check your plan's current rules. Try the provider's alternative port (often `2525`), or a paid plan. Until then, `SHOW_INVITE_LINKS=True` shows the leader each invite link to send by hand.

### Step 4: First leader and real data
In the Render **Shell** tab (or `railway run`), run `python manage.py createsuperuser` once. Then follow "From an empty database to a working site" below.

## Option A: Render or Railway with any managed PostgreSQL

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

### Or: import people and awards from CSV files

Steps 2 and 3 can be done in one go with `import_csv`. Fill in copies of the files in [deploy/import-templates/](../deploy/import-templates/) (column notes in its README). **Don't commit the real files**: they hold people's emails.

On Render, open the service's **Shell** tab. The first leader must already exist (`createsuperuser`). Then:

1. Put the files in a folder. The Shell has no upload button, so paste each file:
   ```bash
   mkdir -p /tmp/import && cat > /tmp/import/people.csv <<'EOF'
   (paste the file's contents here, then press Enter)
   EOF
   ```
   Repeat for `awards.csv`, `criteria.csv` and `questions.csv`. Any file can be left out.
2. Check them. This is a dry run: nothing is saved, and every problem is listed by file and line.
   ```bash
   python manage.py import_csv /tmp/import --by <your leader email>
   ```
3. When it says "Dry run, nothing saved. Would do: …", save, and email each new account its set-your-password link:
   ```bash
   python manage.py import_csv /tmp/import --by <your leader email> --commit --invite
   ```
   While email isn't set up (`SHOW_INVITE_LINKS=True`), the links are also printed so you can pass them on by hand.
4. Log in, check the awards' set-up checklists, then set each award to **Open**. Imported awards start as Upcoming.

Running it again is safe: people are matched by email and awards by name. Nobody is removed from a team or panel, criteria are replaced, and a new form version is published only if the questions changed. Existing people keep their role.

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
