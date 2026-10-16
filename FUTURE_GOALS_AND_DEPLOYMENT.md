# Future Goals and Deployment Plan: Awards Platform

> **Snapshot:** 16 Oct 2026, `main` at `04d5ee8`. What already exists, day by day, is in [PROGRESS_LOG.md](PROGRESS_LOG.md); the delivery timeline is in [docs/Project-Roadmap.md](docs/Project-Roadmap.md).
> **Hosting (decided 14 Oct, live 15 Oct 2026):** a **demo site** runs on Render's free plan with PostgreSQL on Supabase and deploys `main` automatically. It holds demo data and demo accounts on purpose. ⚠️ **Not provided yet:** the **target date for real users**. The timeline in §7 counts back from that launch day "**D**" (pick the date and fill it in).
> Estimates follow the roadmap style in `docs/Project-Roadmap.md`: hours of focused work, plus a "done when" check.

---

## 1. Achieved so far

- [x] Planning: workflows, roadmap, decision log (Phase 1)
- [x] Clickable skeleton for the website and every portal (Phase 2)
- [x] 3.1 Data model and database (constraints, soft delete; migrations for every later change)
- [x] 3.2 Backend foundation (split settings, response format, pagination, throttling, logging, `/api/v1/health/`, seed data)
- [x] 3.3 Authentication and roles (one login form, applicant sign-up, role redirect, `/admin/` for admins only); a fifth role, the **award manager**, since 15 Oct
- [x] 3.4 Core API (all endpoints; Postman: 124 requests, 280 checks, 0 failures)
- [x] 3.5 Every role's screens on real data; the whole flow from applying to a published result works
- [x] Rules 1–4 (blind judging, conflicts, recorded score changes, form versions) enforced on the server and tested, with no skipped rule tests
- [x] CI: lint, migration check, tests, dependency scan and a production-image check on every push
- [x] Production setup in the repo: Gunicorn, WhiteNoise, `Dockerfile.prod`, Nginx, Sentry, S3 option, SMTP settings ([docs/Deployment.md](docs/Deployment.md))
- [x] R0 Phase 3 wrapped up: quick review, 3.6–3.8, real Rule 2/3 tests, junk-input sweep (14 Oct)
- [x] R1 Award administration: a leader creates an award and picks its manager; the award's team sets it up and opens it without code (14–15 Oct)
- [x] R2 Document upload (PDF/JPG/PNG, 10 MB, permission-checked downloads, neutral names for blind judges)
- [x] R4 Notifications by email and a Notifications page; leaders only get notifications they act on (16 Oct)
- [x] R5 People: leaders add staff, award managers, judges and leaders with an invite email; deactivate and reactivate. *(The audit-log viewer was removed on 16 Oct, D15; the trail is read-only in `/admin/`.)*
- [x] R8 (part) Duplicate organisations: automatic detection, per-award review by programme staff, merge / keep separate / undo (15 Oct)
- [x] R11 Award managers and award-only access for staff and managers (15 Oct)
- [x] R12 Staff accept or decline each entry; applicants see judging progress (15 Oct)
- [x] R13 Results: results board for every role; the award manager decides each entry; **leadership approves each award's result as a whole** (published, applicants told); re-evaluation decided by the award manager with fresh judges (15–16 Oct)
- [x] R14 `import_csv` to load real staff, judges, managers, leaders and awards (15 Oct)
- [x] **Deployed:** demo site live on Render + Supabase (15 Oct)
- [ ] Ready for real users: domain, real email, file storage bucket, backups, monitoring, a real leader account and real data (see §4)

---

## 2. Remaining work: phased plan

| Phase | Goal | Tasks | Est. hours | Suggested timeline | Depends on | Done when |
|---|---|---|---|---|---|---|
| ✅ **R0 · Wrap up Phase 3** (done 14 Oct 2026; 1 Rule 2 test stays skipped until duplicate detection, R8) | Close the roadmap's Phase 3 | 1-hour quick review; 3.6 feature slices; 3.7 validation pass; 3.8 cleanup; replace the skipped Rule 2 and Rule 3 placeholder tests | 14 | Week 1 | none | Roadmap steps 3.6–3.8 ticked; 0 skipped rule tests |
| ✅ **R1 · Award administration** (done 14 Oct 2026; leaders create awards and pick the manager since 15 Oct. The old demo-only *Award settings* screen was removed on 16 Oct) | Run more than 2 programmes without code | Screens to create and edit awards, rounds, criteria (weights must add up to 100), dates and the judge panel; settings screen for any award, not just the 2 demo ones | 10 | Week 1–2 | R0 | Staff create a third award end to end in the browser |
| ✅ **R2 · Document upload** (done 14 Oct; virus scan and S3 bucket still to set up) | Applicants upload evidence | Upload on file questions (type and size checks, 10 MB limit already in the model); storage in `MEDIA_ROOT` locally and S3-compatible in production; download links for staff; blind view keeps file names hidden; virus or type scan | 8 | Week 2 | Media storage decision (§4) | A PDF uploaded by an applicant opens for the assigned judge with its name hidden on blind awards |
| **R3 · Judging criteria and scoring rules** | Rules per award | Criteria editor per round; scoring guidance text; tie and spread rules (for example, flag a spread of 2 or more, already shown to leaders); round-2 shortlisting from round-1 scores | 8 | Week 2 | R1 | A Business Excellence report moves from desk review to live presentation by rule |
| ✅ **R4 · Notifications** (done 14 Oct, except per-user opt-out; needs an SMTP account in production) | People know what changed | Notification bell and list on the web (the API exists); email through SMTP or SES for assignment, verification, edit decision and result; email templates; per-user opt-out | 6 | Week 2–3 | Email service (§4) | A judge gets an email and an in-app note when assigned |
| ✅ **R5 · Account and admin tools** (done 14 Oct 2026; the audit-log viewer was removed again on 16 Oct, D15) | No `/admin/` needed for daily work | Leader screen to create, deactivate and reactivate staff, judge and leader accounts (the API exists); invite email with a set-password link; audit-log viewer with filters (who, what, when) | 8 | Week 3 | R4 (invite email) | A leader adds a judge from the portal; the action shows in the audit viewer |
| 🟡 **R6 · Dashboards, reports, search, export** (leader overview, results board and publishing results done 15–16 Oct; export is left) | Leaders and staff can report | Charts per award; search and filter everywhere; export lists to **CSV** and results to **PDF**; ~~publish results to applicants~~ (done: award-level approval) | 6 | Week 1–2 | R3 | A leader downloads an award's approved results as CSV and PDF |
| **R7 · Password and account self-service** | Fewer support requests | Password reset by email (the web flow exists; needs a real email backend); change password; optional two-factor login for staff and leaders | 4 | Week 3 | R4 | Reset email arrives in production and works once |
| 🟡 **R8 · Duplicates and public site** (duplicates done 15 Oct 2026: detection, per-award review, merge / keep separate / undo; the public pages are left) | Remove the last sample content | ~~Duplicate-organisation detection and the merge screen~~ (done); public award pages from the `Award` table instead of `demo_data.py` | 3 | Week 2 | R1 | `apps/core/demo_data.py` no longer feeds any page |
| **R9 · Performance** | Fast at 80 awards and thousands of reports | Fix N+1 queries (`report_for_judge`, per-award counts); `select_related`/`prefetch_related`; database indexes review; pagination on long web lists; caching of public pages | 6 | Week 4 | R6 | Main pages under 300 ms with 5,000 reports in a load-test database |
| **R10 · Accessibility and responsive** | Usable by everyone, on phones | WCAG 2.1 AA pass (labels, contrast, keyboard, focus, error text); mobile layouts for all portals; axe or Lighthouse checks | 6 | Week 4 | R0–R8 screens | Lighthouse accessibility ≥ 90 on every portal page; usable at 375 px |
| ✅ **R11 · Award managers** (done 15 Oct) | Each award has an owner | A fifth role; one manager per award, chosen by leadership; staff allocated per award; staff and managers only reach their own awards | 8 | done | R1 | A manager sees only their award; leadership picks the manager when creating an award |
| ✅ **R12 · Entry checks and progress** (done 15 Oct) | Only eligible entries reach judges | Staff accept or decline each submitted entry (reason to the applicant); applicants see judging progress (counts only) | 4 | done | R11 | A declined entry tells the applicant why; a submitted entry can't be assigned before it is accepted |
| ✅ **R13 · Results and re-evaluation** (done 15–16 Oct) | Fair, approved results | Award manager decides each entry and sends the award's result; leadership approves it as a whole (published, results board, applicants told) or sends it back; re-evaluation once per entry, decided by the award manager with fresh judges | 10 | done | R11 | An award's result is published only after leadership approves it; a re-evaluated entry shows "Re-evaluated · was …" |
| ✅ **R14 · Real data import** (done 15 Oct) | Load real people and awards | `python manage.py import_csv <folder> --by <leader>`: dry run by default, one transaction, every row checked by the services | 3 | done | R1 | The example CSVs import cleanly; a bad row saves nothing and is named |
| **Optional · Separate SPA frontend** | Only if wanted | React or Vue app on the existing `/api/v1/` (JWT client with refresh, route guards by role) | 30+ | after launch | API is stable | Not needed for launch: the templates already cover every role |

---

## 3. Testing and quality plan

| Level | What | Tool | Target |
|---|---|---|---|
| Unit | Services (`apps/*/services.py`): every rule and status change | pytest + factory-boy | Every `BusinessRuleError` path covered |
| Integration | API endpoints and web views with the database | pytest-django, DRF `APIClient` | Each endpoint: success, 400, 401, 403/404 |
| Role and permission | Every page and endpoint × every role; other users' ids → 404 | Parametrised pytest (exists for homes and API; extend to new screens) | No page reachable by the wrong role |
| End-to-end | Real browser: apply → verify → assign → grade → approve | Playwright (new) + the existing `tests/test_web_workflow.py` | Runs in CI on every merge to `main` |
| API contract | Postman collection on fresh seed data | Newman in CI | 0 failures |
| Load | 200 concurrent users; judges grading; leader dashboards | Locust or k6 | p95 < 800 ms, no errors |
| Security | OWASP Top 10 check (below); dependency scan; ZAP baseline scan | `pip-audit`, OWASP ZAP | No high findings open |
| Accessibility | Automated + manual keyboard pass | axe / Lighthouse | WCAG 2.1 AA |
| UAT | Real staff, a judge and a leader on a staging copy | Checklist below | Every row signed off |

**OWASP Top 10 quick check**

- [ ] **A01 Broken access control:** role tests on every route; ids filtered in `get_queryset()`; re-test in production.
- [ ] **A02 Cryptographic failures:** HTTPS only, HSTS, secure cookies (already in `prod.py`); secrets never in git.
- [ ] **A03 Injection:** ORM only, no raw SQL; templates auto-escape; check the upload file names.
- [ ] **A04 Insecure design:** blind judging and conflicts enforced on the server (done); review the new features the same way.
- [ ] **A05 Misconfiguration:** `DEBUG=False`, strict `ALLOWED_HOSTS`/CORS/CSRF origins, `/admin/` on a non-obvious path or behind an IP allow-list.
- [ ] **A06 Vulnerable components:** `pip-audit` in CI; Dependabot.
- [ ] **A07 Authentication failures:** login throttle (done), password policy (done), optional 2FA for staff and leaders.
- [ ] **A08 Integrity:** pinned dependencies; CI builds the image that gets deployed.
- [ ] **A09 Logging and monitoring:** audit log (done), Sentry, alerts.
- [ ] **A10 SSRF:** no server-side fetching of user URLs (keep it that way).

**UAT checklist**

- [ ] An applicant signs up, fills the profile, uploads a PDF, submits, and asks to edit before judging starts.
- [ ] Staff verify the organisation, accept the entry, check the edit request (the award manager confirms it), review a possible duplicate, and assign judges (a conflicted judge is not offered).
- [ ] A judge sees only their reports; blind fields are hidden; they save midway and submit; a score change needs staff's check and the award manager's confirmation, and records the reason.
- [ ] The award manager decides every entry and sends the award's result; a leader approves the award's result (and exports CSV/PDF once R6 is done); applicants see it on the results board and one asks for a re-evaluation.
- [ ] Old applications open with their own form version after the questions change.
- [ ] Emails arrive (assignment, verification, result, password reset).
- [ ] Works on a phone and with the keyboard only.

---

## 4. Deployment requirements

### 4.1 Infrastructure

| Need | Recommendation (hosting not decided) | Notes |
|---|---|---|
| App server | **Render** or **Railway** for the simplest start, or a small VPS (DigitalOcean or Lightsail, 2 vCPU / 4 GB) with Docker | Managed platforms handle HTTPS and deploys; a VPS is cheaper but you run Nginx and updates |
| PostgreSQL | Managed Postgres 16 (**Supabase**, Render, Railway, RDS or DO Managed) with daily backups and point-in-time recovery. Supabase is ready: set `DATABASE_URL`, plus `DB_TRANSACTION_POOLER=True` when using its port-6543 pooler (docs/Deployment.md) | Don't run the production database in the app container |
| File/media storage | S3 or an S3-compatible bucket (**Supabase Storage**, DO Spaces, Cloudflare R2), **private**; `django-storages` (supported: `AWS_S3_ENDPOINT_URL`, `AWS_S3_ADDRESSING_STYLE=path`) | Needed for R2 uploads |
| Domain | e.g. `awards.<your-org>.in`; DNS A/CNAME | n/a |
| SSL/HTTPS | Platform-managed, or Let's Encrypt (certbot) on a VPS | `SECURE_SSL_REDIRECT`, HSTS already in `prod.py` |
| Email | Amazon SES, Postmark or SendGrid over SMTP; SPF, DKIM and DMARC on the domain | `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` |

### 4.2 Production settings and environment variables

`config/settings/prod.py` already sets `DEBUG=False`, requires `SECRET_KEY` and `ALLOWED_HOSTS`, and turns on the HTTPS redirect, secure cookies, HSTS, nosniff and frame deny.

| Variable | Production value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `SECRET_KEY` | 50+ random characters, from the secret store |
| `JWT_SIGNING_KEY` | Separate 32+ character secret |
| `ALLOWED_HOSTS` | `awards.example.org` |
| `CSRF_TRUSTED_ORIGINS` | `https://awards.example.org` |
| `CORS_ALLOWED_ORIGINS` | Empty (same-origin templates); a frontend origin only if an SPA is added |
| `DATABASE_URL` | Managed Postgres URL with `?sslmode=require` |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | 15 / 1 |
| `THROTTLE_LOGIN` / `THROTTLE_ANON` / `THROTTLE_USER` | `10/minute` / `60/minute` / `1000/hour` |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | From the email provider (all read by `base.py`) |
| `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` | From Sentry; Sentry starts only when the DSN is set |
| `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL` | Private bucket for uploads; leave the bucket empty to use the local media folder |
| `LOG_LEVEL` | `INFO` |
| `DEMO_PASSWORD` | **Not set**: the seed must never run in production |

### 4.3 Backend deployment

✅ **Now in the repository** (see [docs/Deployment.md](docs/Deployment.md)):

- `requirements/prod.txt`: Gunicorn, Sentry and django-storages; WhiteNoise is in `base.txt`.
- `Dockerfile.prod`: Gunicorn, static files collected at build time, non-root user `app`.
- `docker-compose.prod.yml` and `deploy/nginx.conf`: HTTPS, HTTP→HTTPS redirect, 12 MB uploads, web-login rate limit.
- `config/settings/prod.py`: WhiteNoise compressed static files, S3 uploads when `AWS_STORAGE_BUCKET_NAME` is set, logs to stdout, Sentry when `SENTRY_DSN` is set, database connection reuse.
- `.env.production.example`: every variable, with placeholders.

Checked locally on 14 Oct 2026: the image builds, migrates a fresh database and serves through Gunicorn as user `app`; HTTP redirects to HTTPS; HSTS, nosniff and frame-deny headers are sent; hashed, gzip-compressed static files are served; debug pages are off; `check --deploy` reports only the HSTS-preload warning.

**Release steps (every deploy):**
1. Build the image.
2. Run `python manage.py migrate --noinput`.
3. Run `python manage.py check --deploy`.
4. Start the new containers.
5. Run the smoke test (`/api/v1/health/`).

### 4.4 Frontend build and hosting

- **Current frontend (Django templates):** no separate build. Static files are collected into the image and served by WhiteNoise, optionally behind a CDN (Cloudflare) with long cache headers; file names are hashed by the manifest storage.
- **If an SPA is added later:** build with `npm run build` and host it on static hosting or a CDN (Netlify, Vercel, S3 + CloudFront). Set the API URL through an environment variable at build time, e.g. `VITE_API_BASE_URL=https://awards.example.org/api/v1`. Add its origin to `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

### 4.5 CI/CD pipeline (GitHub Actions)

**Exists today** (`.github/workflows/ci.yml`): ruff → `makemigrations --check` → pytest on Postgres 16 → `pip-audit` (report only), and a `prod-image` job that builds `Dockerfile.prod`, runs `check --deploy` and checks it runs as non-root, on every push and PR.

**Add:**
- [x] `pip-audit` (dependency scan, report only for now)
- [ ] Newman (Postman collection against a CI server with seed data)
- [x] A **build** job for `Dockerfile.prod` with `check --deploy`
- [ ] Push that image to GHCR, tagged with the commit SHA (needs the hosting decision)
- [ ] A **deploy** job on `main` only, after tests pass: trigger the Render/Railway deploy hook, or SSH to the VPS (`docker compose -f docker-compose.prod.yml pull && up -d`, then `migrate`).
- [ ] A required **manual approval** (GitHub environment `production`) before deploy.
- [ ] A smoke check after deploy: `curl -f https://awards.example.org/api/v1/health/`.

### 4.6 Database

- [ ] Daily automated backups, kept 30 days, plus point-in-time recovery if the provider offers it.
- [ ] **Restore test** before launch and then monthly: restore into a scratch database, run `check` and log in.
- [ ] Migration strategy: additive first (new nullable columns, then backfill, then constraints); never edit an applied migration; back up before each release that has migrations.
- [ ] **No seed or test data in production:** never run `seed_data` or `seed_demo`, and leave `DEMO_PASSWORD` unset.
- [ ] **First leader/admin account:** run `python manage.py createsuperuser` once in a one-off container, which gets the leader role by default. Use a unique email and a password from a password manager; enable 2FA when R7 lands. Create all other staff, judge and leader accounts from the portal or API, never by sharing one account.

### 4.7 Monitoring and logging

- [ ] **Sentry** (`sentry-sdk[django]`, `SENTRY_DSN`) for errors and slow transactions; scrub personal data.
- [ ] **Uptime check** every minute on `/api/v1/health/` (UptimeRobot or Better Stack), with alerts to email or Slack.
- [ ] **Logs:** the app already uses a `RotatingFileHandler`. In containers, also log to stdout and let the platform collect it; keep 30 days.
- [ ] Database metrics (connections, slow queries) from the provider dashboard.

### 4.8 Security checklist

- [ ] Rate limiting active (DRF throttles in place; add Nginx or platform limits for the web login form).
- [ ] Password policy: Django validators (in place); consider a minimum of 10 characters for staff, judges and leaders.
- [ ] JWT lifetimes: access 15 min, refresh 1 day, rotation and blacklist (in place); flush expired tokens with a nightly `flushexpiredtokens`.
- [ ] Secrets in the platform's secret store or a `.env.production` file that is not in git; rotate `SECRET_KEY` and `JWT_SIGNING_KEY` if leaked.
- [ ] Dependency scan (`pip-audit`, Dependabot) in CI.
- [ ] `python manage.py check --deploy` passes with no warnings.
- [ ] **Re-test role access in production** with real accounts: the wrong role gets 403, another user's id gets 404, `/admin/` is admin-only.
- [ ] Upload safety (R2): type allow-list, size limit, private bucket, signed URLs.

### 4.9 Pre-launch checklist and rollback plan

**Pre-launch**
- [ ] All tests, Newman and the ZAP baseline pass on the release commit.
- [ ] Staging (a copy of production settings) passes the UAT checklist.
- [ ] Backups on, and a restore tested.
- [ ] DNS, HTTPS, email (SPF/DKIM) verified; a password-reset email received.
- [ ] Sentry and uptime alerts fire on a test error.
- [ ] First leader account created; demo data absent.
- [ ] Privacy notice and terms published (applicant data includes GSTIN/PAN).

**Rollback**
1. Keep the previous image tag. To roll back, redeploy that tag; with the platform's "rollback to previous deploy" this takes about 2 minutes.
2. If the release had migrations, they are additive (see §4.6), so the old code still runs. If not, restore the pre-release backup (taken automatically before `migrate`).
3. Announce a short status note to users; open an incident note with the cause and the fix.

### 4.10 Post-launch

| Item | Schedule |
|---|---|
| Backups | Daily automatic; monthly restore test |
| Dependency and security updates | Weekly Dependabot review; monthly patch release |
| Monitoring review (Sentry, uptime, slow queries) | Daily during award season, weekly otherwise |
| Expired-token flush, log cleanup | Nightly job |
| Support | Shared inbox (`awards@…`); reply within 1 working day; urgent issues during judging windows within 4 hours |
| Retrospective and roadmap update | After each award cycle (Phase 6) |

---

## 5. Risks and mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Blind judging leaks identity (new fields, uploads, exports) | Medium | High | All hiding in `report_for_judge()`; tests for every new field; check exports for judges |
| Wrong role sees data after new screens are added | Medium | High | `role_required` and `visible_to()` on every view; parametrised role tests in CI |
| No launch date chosen, so the real launch slips (hosting is chosen and a demo site runs) | High | Medium | Pick the date; the remaining work in §7 is about 4 weeks |
| Demo accounts with a shared password stay on the live site when real users join | Medium | High | Before sharing the link with real users: create a real leader, remove or lock the demo accounts, load real data with `import_csv` |
| Email deliverability (verification and results land in spam) | Medium | Medium | SES/Postmark with SPF/DKIM/DMARC; test inboxes |
| Uploads: large files, malware, storage cost | Medium | Medium | 10 MB limit, type allow-list, private bucket, scan |
| Data loss | Low | High | Managed Postgres, daily backups, restore tests, PROTECT and soft delete |
| Performance at 80 awards × thousands of reports | Medium | Medium | R9 fixes, indexes, load test before launch |
| Single developer and a short timeline | High | Medium | Small phases with "done when" checks; CI catches regressions |

---

## 6. Definition of Done (whole application)

- [x] All five roles can do their complete job in the browser with no `/admin/` or API use: apply with uploads, verify and accept, assign, grade, change scores with approval, decide entries, approve and publish award results.
- [ ] The two demo awards **and** a newly created award work differently purely from staff settings.
- [x] Rules 1–4 are enforced on the server and covered by passing tests (no skipped rule tests).
- [ ] No sample data feeds any page (`demo_data.py` is retired).
- [x] Notifications and emails are sent for every status change that matters to a user (real delivery needs an email provider).
- [ ] Search, filters, and CSV/PDF export are available to staff and leaders.
- [ ] Automated tests, Newman, `pip-audit` and ZAP pass in CI; UAT is signed off.
- [ ] WCAG 2.1 AA and mobile layouts are checked.
- [ ] Deployed on HTTPS with backups, monitoring, alerts and a tested rollback; `check --deploy` is clean.
- [ ] Docs are updated (Setup, API, runbook) and handed over.

---

## 7. Timeline

### Done so far

| Dates | Work |
|---|---|
| 11–13 Oct | Planning, clickable skeleton, client reviews |
| 14 Oct | Phase 3 (R0), R1 award administration, R2 uploads, R4 notifications, R5 people, production setup and hosting configs |
| 15 Oct | R11 award managers, R14 CSV import, R8 duplicates, R12 entry checks, R13 results board and re-evaluation; **demo site live** |
| 16 Oct | R13 award-level result approval; leaders' notifications and pages trimmed to what they decide; Form builder for staff only |

### Remaining work (counting back from launch day **D**; fill in real dates)

About **20 working days** (6 focused hours a day, one developer). If D is sooner, cut the PDF export, the public pages and the optional SPA first.

| Work | Wk 1 (D−20…D−16) | Wk 2 (D−15…D−11) | Wk 3 (D−10…D−6) | Wk 4 (D−5…D) |
|---|---|---|---|---|
| R3 Round-2 shortlist and scoring guidance | ██ | | | |
| R6 CSV/PDF export of award results, search | ██ | █ | | |
| R7 Password self-service in production, 2FA for staff and leaders | █ | | | |
| R8 Public pages from the database | | ██ | | |
| R9 Performance (indexes, N+1 queries, load-test database) | | ██ | | |
| R10 Accessibility and phones | | | ██ | |
| Testing: load, OWASP ZAP, UAT with real staff, a manager and a leader | | | ██ | █ |
| Real-user set-up: domain, email (SPF/DKIM), storage bucket, backups and restore test, Sentry and uptime alerts | █ (decide) | █ | █ | |
| Real data: a real leader, `import_csv` for people and awards, demo accounts removed | | | █ | █ |
| Launch and hypercare | | | | ███ (D) |
