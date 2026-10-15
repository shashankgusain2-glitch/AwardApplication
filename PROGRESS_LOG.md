# Progress Log: Awards Platform

> **Snapshot:** 14 Oct 2026 · `main` at `8477b62` ("steps 3.4 and 3.5").
> Written from the code, settings, migrations, tests and git history. Where your summary and the code differ, the code wins and the difference is flagged with ⚠️.
> **Since that snapshot** (branch `feature/form-editor-and-prod-setup`): the staff **form-version editor** with 6 real Rule 4 tests, and the **production setup** (Gunicorn, WhiteNoise, `Dockerfile.prod`, Nginx, Sentry, S3 option, SMTP settings, CI production-image check). Then **email notifications (R4)** and **document upload (R2)**. Then **award administration (R1)** , the **Phase 3 wrap-up (R0)** and **people and audit log (R5)**. Full suite: **340 passed, 1 skipped**.

---

## 1. Project overview

**Purpose.** One platform that runs many award programmes (about 80). Two demo awards work differently purely through staff settings, with no code changes:

| Award | Rounds | Blind judging | Judges per report |
|---|---|---|---|
| **Business Excellence** | Desk review → live presentation | On | 3 |
| **Kaizen Competition** | Desk review → site visit | Off | 2 |

The four rules from the brief:
1. **Blind judging:** judges can't see who applied.
2. **No conflict of interest:** conflicted judges are never assigned.
3. **Recorded score changes:** every score change is recorded with who changed it and why.
4. **Form versions:** old applications still open with their own questions.

**Roles**

| Role | What they do | How the account is created |
|---|---|---|
| Applicant | Organisation profile, apply, submit, follow status | Self sign-up (always created as an applicant) |
| Staff | Verify organisations, assign judges, award settings, approve edit and score-change requests | By a leader (API `POST /users/`), `/admin/`, or `seed_data` |
| Judge | Accept or decline assignments; grade **only their own** reports | By a leader, `/admin/`, or `seed_data` |
| Leader | Oversees everything, approves results, manages accounts; never changes scores | By a leader, `createsuperuser`, or `seed_data` |

**Tech stack** (from `requirements/base.txt`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`)

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.12 (Docker image `python:3.12-slim`, CI) |
| Web framework | Django | ≥5.2, <5.3 |
| API | Django REST Framework | ≥3.15 |
| API auth | djangorestframework-simplejwt (with the blacklist app) | ≥5.3 |
| Filtering / CORS / docs | django-filter ≥24, django-cors-headers ≥4.4, drf-spectacular ≥0.27 (Swagger at `/api/docs/`) | |
| Database | PostgreSQL (psycopg 3) | 16 (`postgres:16` in docker-compose and CI) |
| Config | django-environ, `.env` | |
| Frontend | **Server-rendered Django templates** plus `static/css/main.css` and `static/js/main.js` | ⚠️ No React/Vue/Next app exists |
| Tests / lint | pytest 8, pytest-django, factory-boy, ruff | |
| Dev runtime | Docker Compose (`db` and `web`, `runserver`) | |

---

## 2. Summary table

| Roadmap task | Status | Est. hours | Timeline | Evidence |
|---|---|---|---|---|
| Phase 1 Planning (workflows, roadmap) | Done | n/a | 11–12 Oct | `docs/Project-Roadmap.md`, `docs/User-Workflows.md`, `docs/decisions/decision-log.md` |
| Phase 2 Skeleton (clickable screens) | Done (later replaced by real data) | n/a | 11–13 Oct | commit `d8a51db`; `templates/` |
| 3.1 Data model and database | Done | 3 | Day 1 | 11 migrations across 7 apps; `docs/Data-Model.md` |
| 3.2 Backend foundation | Done | 2 | Day 1 | `config/settings/{base,dev,test,prod}.py`; `GET /api/v1/health/` |
| 3.3 Authentication and roles | Done | 3 | Day 1 | `apps/accounts/`, `apps/accounts/permissions.py` (`role_required`), `tests/test_authentication.py`, `tests/test_role_homes.py` |
| 3.4 Core API | Done | 6 | Day 2 | `config/api_urls.py`, `postman/` (116 requests, 259 checks, 0 failures), `tests/api/` |
| 3.5 Frontend–backend integration | Done | 4 | Day 2–3 | `apps/{entries,judging,awards,dashboard}/views.py`, `tests/test_web_workflow.py` |
| 🔍 Quick review | Not started | 1 | Day 3 | n/a |
| 3.6 Feature slices | Partial (form-version editor done) | 8 | Day 3–4 | `apps/awards/views.py` `form_edit`, `tests/rules/test_rule4_form_versions.py` |
| 3.7 Validation and edge cases | Partial (service-layer validation exists; no dedicated pass) | 3 | Day 4 | `apps/*/services.py` (`BusinessRuleError`) |
| 3.8 Mid-point review and cleanup | Not started | 2 | Day 4 | n/a |
| Phase 4 Testing | Partial (automated tests running in CI) | n/a | ongoing | `.github/workflows/ci.yml`, `docs/testing.md` |
| Phase 5 Deployment | Not started | n/a | n/a | only `config/settings/prod.py` exists |
| Phase 6 Maintenance | Not started | n/a | n/a | n/a |

---

## 3. Detailed work done

### 3.1 Authentication and authorization

| Item | Status | Evidence / notes |
|---|---|---|
| Login form | Done, ⚠️ **one form, not four role tabs** | Four tabs were built in `507414a`, then replaced on 14 Oct by **one form** at the user's request (`e8fa138`). The account's stored role decides where the user goes; a role sent with the form is ignored |
| Applicant sign-up (applicants only) | Done | `/signup/` (web), `POST /api/v1/auth/register/` (always creates an applicant, even if another role is sent) |
| Logout | Done | Web `POST /logout/`; API `POST /auth/logout/` blacklists the refresh token |
| Password reset | Done (web) | `/password-reset/…` (Django tokens). Emails are printed to the console in development |
| JWT for the API | Done | SimpleJWT: access 30 min, refresh 1 day, rotation, blacklist after rotation; claims include `role`, `email`, `name` |
| Role check on the backend (API) | Done | `apps/core/api/permissions.py`: `IsApplicant`, `IsStaff`, `IsJudge`, `IsLeader`, `IsStaffOrLeader` (the role comes from `request.user`, never the request body) |
| Wrong role at API login | Done | Optional `role` field; a mismatch returns 401 |
| Role check on the web pages | Done | `@role_required(...)`; other roles get a 403 page; a tampered session role logs the user out |
| Role-based redirect after login | Done | applicant → `/applicant/`, staff → `/staff/`, judge → `/judge/`, leader → `/leadership/` |
| Judge lands on their assigned reports | Done | `/judge/` (web), `GET /api/v1/judge/my-assignments/` (API), both only the logged-in judge's |
| `/admin/` for admins only | Done | Tested in `tests/test_role_homes.py` |
| Deactivated users lose access | Done | Web: next request logs them out. API: tokens blacklisted (`/users/{id}/deactivate/`) |

### 3.2 Data model and database

All models are in PostgreSQL, created by migrations. Shared base classes: `TimeStampedModel` (`created_at`, `updated_at`) and `SoftDeleteModel` (`is_deleted`, `objects` / `all_objects`).

| Model (app) | Key fields | Relationships | Constraints |
|---|---|---|---|
| **User** (accounts) | email (login, unique), name, role, is_active | n/a | `user_role_valid` check; index on (role, is_active) |
| **ApplicantProfile** (accounts) | organisation_name, gstin, holder_pan, sector, size, turnover band, address, contact, verification_status, verified_at/by | 1–1 User | GSTIN unique when set; established year 1800–2100 |
| **JudgeProfile** (accounts) | expertise, priority, max_open_assignments | 1–1 User; M–M Award (panel) | priority 1–99; max open ≥1 |
| **Award** (awards, soft delete) | slug, name, status, opens/closes, applicant_type, judges_per_report, blind_judging, entry_fee | n/a | judges per report 1–7; closes after opens |
| **AwardRound** (awards) | number, kind (desk / site / live) | FK Award | unique (award, number); number 1–5 |
| **FormVersion** (awards) | version, questions (JSON), published_at | FK Award (PROTECT) | unique (award, version); **cannot be changed once published** (enforced in `save()`) |
| **Criterion** (awards) | round_number, key, label, weight, order | FK Award | unique (award, round, key); weight 1–100 |
| **Application / "report"** (applications, soft delete) | reference, title, content (JSON answers), status (draft → submitted → assigned → in_review → scored → approved/rejected), submitted_at, edit_requested / allowed / reason | FK User (applicant), Award, FormVersion (all PROTECT) | one per applicant per award (non-deleted); submitted ⇒ has a date |
| **Attachment** (applications) | file, original_name, size, content_type | FK Application | ≤10 MB; PDF/JPG/PNG checked by content (`apps/applications/files.py`) |
| **JudgeAssignment** (assignments) | round, status (pending / in_review / completed / declined), assigned_by | FK judge, FK report (PROTECT) | unique (judge, report, round); round ≥1 |
| **ConflictOfInterest** (assignments) | reason, recorded_by | FK judge, FK ApplicantProfile | unique (judge, profile) |
| **Evaluation** (evaluations) | status (draft / submitted), total_score, feedback, submitted_at | 1–1 JudgeAssignment | total 0–10; submitted ⇒ has a date |
| **CriterionScore** (evaluations) | score, comment | FK Evaluation, FK Criterion | unique (evaluation, criterion); score 1–10 |
| **ScoreChangeRequest** / **ScoreChange** (evaluations) | reason, status / old → new, changed_by | FK Evaluation | ScoreChange is append-only (Rule 3) |
| **Notification** (notifications) | kind, message, link, is_read | FK User | n/a |
| **AuditLog** (audit) | user, action, entity, entity_id, changes (JSON), ip, timestamp | FK User (SET_NULL) | append-only; indexes on entity and on (user, time) |

**Migrations:** accounts (4), awards (2), applications, assignments, audit, evaluations and notifications (1 each). `accounts/0003` is hand-written: it copies names and lower-cases emails before dropping username, first and last name. CI fails if migrations are missing (`makemigrations --check`).

**Seed command:** `python manage.py seed_data` (alias `seed_demo`). It goes through the service layer, so the rules and audit entries apply, and it is safe to re-run. It creates:
- 1 leader, 2 staff, 3 judges and 5 applicants, all with `DEMO_PASSWORD`
- the 2 awards, with rounds, form v1 and criteria
- 1 recorded conflict (Rao ↔ Shri Ganesh)
- 10 reports at every stage, with assignments and evaluations

Only questions marked identifying (and file names) mention the organisation.

### 3.3 Backend foundation and Core API

**Foundation:**
- **Settings:** split into `base`, `dev`, `test` and `prod`; env via django-environ.
- **Response format:** every response is `{success, data, message, errors}` (renderer plus exception handler). Errors name the field.
- **Pagination:** `?page`, `page_size`, 20 by default, up to 100.
- **Filtering and docs:** filtering, search and ordering; OpenAPI schema with 0 warnings.
- **Throttling:** anonymous 60/min, logged-in users 1000/h, login 10/min (60/min in development).
- **Logging:** rotating file logs.
- **Health:** `GET /api/v1/health/` checks the server and the database.
- **Object-level security:** each `get_queryset()` filters through `services.visible_to(user)`, so another user's id gives **404**.

**Endpoint table** (base `/api/v1/`; "Postman" = covered by `postman/Awards-Platform.postman_collection.json`)

| Method | URL | Role | Purpose | Postman |
|---|---|---|---|---|
| GET | `health/` | anyone | Server and database up | Y |
| POST | `auth/login/` | anyone | Email + password (+ optional role) → access, refresh, user | Y |
| POST | `auth/refresh/` | anyone | Rotate the refresh token | Y |
| POST | `auth/logout/` | logged in | Blacklist the refresh token | Y |
| POST | `auth/register/` | anyone | Applicant sign-up | Y |
| GET / PATCH | `auth/me/` · `users/me/` | logged in | Own account (name only) | Y |
| GET / POST | `users/` | staff + leader / leader | List / create staff, judge or leader accounts | Y |
| GET / PATCH | `users/{id}/` | staff + leader / leader | Read / update a user | Y |
| POST | `users/{id}/deactivate/` · `activate/` | leader | Turn an account off or on | Y |
| GET / PUT / PATCH | `profiles/mine/` | applicant | Own organisation profile | Y |
| GET | `profiles/` | staff, leader | List organisations | Y |
| GET | `profiles/{id}/` | staff, leader | One organisation | N |
| POST | `profiles/{id}/verify/` | staff, leader | Verify or reject an organisation | Y |
| GET | `awards/` · `awards/{slug}/` | anyone | Awards with rounds, criteria, current form | Y |
| GET / POST | `applications/` | applicant (own) · staff, leader (all) | List / create a draft | Y |
| GET / PATCH / DELETE | `applications/{id}/` | applicant (own); GET also staff and leader | Read / save answers / delete a draft | Y (PUT not tested) |
| POST | `applications/{id}/submit/` | applicant | Submit (required answers checked) | Y |
| POST | `applications/{id}/request-edit/` · `decide-edit/` | applicant · staff, leader | Ask for / decide an edit | Y |
| POST | `applications/{id}/change-status/` | staff, leader (approve: leader only) | Reject or approve | Y |
| GET | `applications/{id}/eligible-judges/` | staff, leader | Judges who may take the report, best first | Y |
| GET / POST | `assignments/` | judge (own) + staff + leader / staff + leader | List / assign | Y |
| GET | `assignments/{id}/` | judge (own), staff, leader | One assignment (blind view for judges) | Y |
| POST | `assignments/bulk/` | staff, leader | Exact pairs, or fill with the best judges (all or nothing) | Y |
| POST | `assignments/{id}/reassign/` | staff, leader | Move to another judge | Y |
| POST | `assignments/{id}/accept/` · `decline/` | judge (own) | Accept / decline | Y |
| GET | `judge/my-assignments/` | judge | Own reports: title, applicant (hidden if blind), submitted date, status, criteria | Y |
| GET / POST | `conflicts/` | staff, leader | Record conflicts (Rule 2) | Y |
| GET / POST | `evaluations/` | judge (own) + staff + leader / judge | List / score own assignment | Y |
| GET | `evaluations/{id}/` | judge (own), staff, leader | One evaluation | N (list only) |
| PATCH | `evaluations/{id}/` | judge (own) | More scores / submit | Y |
| POST | `evaluations/{id}/request-change/` · `change-scores/` | judge (own) | Rule 3 change flow | Y |
| GET / POST | `score-change-requests/` · `{id}/decide/` | staff, leader | Allow or refuse a change | Y (retrieve N) |
| GET / POST | `notifications/` · `{id}/read/` | logged in (own) | In-app notifications | Y |
| GET | `dashboard/summary/` | logged in | Counts by status for your role | Y |
| GET | `lookups/` | logged in | Codes and labels | Y |
| GET | `/api/schema/` · `/api/docs/` | anyone | OpenAPI / Swagger | N |

### 3.4 Frontend integration

⚠️ **The frontend is server-rendered Django templates, not a separate SPA.** The screens call the same `services.py` functions as the API, so the rules are identical. The table maps your requirements onto what exists:

| Requirement | What exists |
|---|---|
| Separate frontend app (React / Next / Vue) | **Planned / not found in code** |
| API client (axios/fetch wrapper with JWT refresh) | **Not found in code**. Not needed for templates; Postman covers the JWT API |
| Route guards | `@role_required` on every portal view (403 for other roles, login redirect when logged out) |
| CORS | `django-cors-headers` configured (`CORS_ALLOWED_ORIGINS`) for a future frontend |

**Screens on real data** (no sample data on any role's portal):

| Role | Screens |
|---|---|
| Applicant | Dashboard; organisation profile (GSTIN/PAN checks; GSTIN locked once verified); pick or start an application; form by section (save, next, back, submit, ask to edit); status timeline with dates; delete draft |
| Judge | My assignments (accept / decline); grading page (save midway, submit, ask to change, change with reason, change history); blind view |
| Staff | Home; entries (search, filter, verify organisations, decide edit and score-change requests, reject); assign judges (tick or fill with the best; conflicted judges hidden); award settings (saved to DB, audited); form builder (published versions read-only; edit questions → publish a new version) |
| Leader | Overview counts; all applications with average and spread; approve / reject results |
| Still sample content | Public marketing pages (home, about, award catalogue text) |

### 3.5 Security measures in place

| Area | Measure |
|---|---|
| Passwords | Hashed (PBKDF2); Django validators (length, common, numeric, similarity) |
| Login abuse | Login and sign-up throttle (10/min in production) |
| Accounts | Self sign-up can only create applicants; staff, judge and leader accounts are created by a leader or admin |
| Authorization | Role checked on the server for every API call and web page; ids filtered in `get_queryset()` (404, not 403, for other users' records) |
| Blind judging | Hiding is done on the server (identifying answers, title, applicant, file names) before the HTML or JSON is built |
| Tokens | JWT rotation, blacklist on logout and on deactivation; short access lifetime |
| Web | CSRF on every form; session cookies; `/admin/` for admins only |
| Production settings | `DEBUG=False`, required `SECRET_KEY` and `ALLOWED_HOSTS`, HTTPS redirect, secure cookies, HSTS, nosniff, `X-Frame-Options: DENY` (in `config/settings/prod.py`, **not yet deployed**) |
| Audit | Append-only `AuditLog` for logins, status changes, assignments, scores, score changes, verification and settings |
| Data | Soft delete for Award and Application; PROTECT on judging history |

### 3.6 Testing done

| Kind | Where | Result |
|---|---|---|
| Automated tests | `tests/` (pytest; runs in GitHub Actions with Postgres 16 and ruff) | **440 passed, 0 skipped** (15 Oct) |
| Postman | `postman/` (collection, environment, `CHECKLIST.md`) | **123 requests, 279 checks, 0 failures** with Newman on fresh seed data; repeatable |
| End-to-end | `tests/test_web_workflow.py` and a manual browser run | Sign up → organisation → submit → staff verify and assign → both judges grade → scored → leader approves → applicant sees "Approved" |
| Rules | `tests/rules/` | Rule 1: 8 tests running. ⚠️ Rule 2 and Rule 3 files are **skipped placeholders**, although those behaviours are tested in `tests/api/`. Rule 4: 6 tests running |

---

## 4. Change log

| Date | Change | Why | Main files |
|---|---|---|---|
| 11 Oct 2026 | Roadmap, git workflow guide; docs moved to `docs/` | Plan the 10 days | `docs/` |
| 11 Oct | Django skeleton, architecture, test plan; clickable UI for the website and all four portals (sample data) | See the workflows before building | `apps/`, `templates/`, `static/` |
| 11 Oct | Code guide, undo guide | Beginner-friendly repo | `docs/Code-Guide.md`, `docs/Git-Workflow.md` |
| 12 Oct | Pre-coding roadmap; two awards made correct; round types (desk / site / live), blind only in desk review; abstraction doc | Brief: two awards differ by settings | `apps/core/demo_data.py`, `apps/awards/` |
| 13 Oct | Applicant workflow and all-workflows builds, then **reverted** (user decision); renamed "Awards Platform"; folder READMEs | Back to a known-good state | many |
| 14 Oct | Authentication with four role tabs, then **replaced by one login form** | User asked for one form; role comes from the account | `apps/accounts/` |
| 14 Oct | Phase 2 backend: data model, service layer, DRF + JWT API, seed data, tests, ruff, CI | Real data and rules | `apps/*/models.py`, `services.py`, `api/`, `config/` |
| 14 Oct | Step 3.3: role home pages on real data; `/admin/` locked | Each role sees only its own data | `apps/core/overview.py`, `tests/test_role_homes.py` |
| 14 Oct | Demo accounts documented | Easy testing | `docs/Setup.md` |
| 14 Oct | Step 3.4: API gaps filled, 6 bugs fixed, Postman collection | Roadmap "done when" | `config/api_urls.py`, `postman/`, `tests/api/test_core_api.py` |
| 14 Oct | Step 3.5: every role's screens on real data; blind leak fixed | Roadmap "done when" | `apps/{entries,judging,awards,dashboard}/`, `templates/`, `tests/test_web_workflow.py` |
| 14 Oct | Form-version editor and Rule 4 tests | Staff edit questions as a new version | `apps/awards/`, `templates/awards/form_edit.html` |
| 14 Oct | Email notifications and a Notifications page (R4); document upload with permission-checked downloads (R2) | Applicants can attach evidence; everyone hears about changes | `apps/notifications/`, `apps/applications/files.py`, `tests/test_notifications.py`, `tests/test_uploads.py` |
| 14 Oct | **Render / Railway / Supabase ready**: `render.yaml`, `railway.json`, `deploy/start.sh` (platform `$PORT`, optional migrations on start), platform addresses picked up automatically, health check exempt from the HTTPS redirect, `SHOW_INVITE_LINKS` stop-gap until email works, step-by-step guide | Hosting decision: Supabase + Render or Railway. Simulated both platforms locally: health 200, HTTPS redirect, unknown host 400, migrations on start, `check --deploy` clean | `render.yaml`, `railway.json`, `deploy/start.sh`, `Dockerfile.prod`, `config/settings/{base,dev,prod}.py`, `apps/dashboard/views.py`, `docs/Deployment.md` |
| 14 Oct | Fix: the owner's meeting note and Day 10 report were committed by mistake in `e83f722`; removed from git (files kept on disk) | Owner keeps them out of the repo | n/a |
| 14 Oct | **R5 People and audit log**: leaders add staff, judges and leaders from the portal (*People*); each gets an email with a one-time set-your-password link; deactivate, reactivate, resend invite; an *Audit log* page with filters. Accounts created through the API without a password also get the invite | So real people can be added after launch without `/admin/` | `apps/accounts/services.py` (`invite`), `apps/dashboard/views.py`, `templates/dashboard/people.html`, `audit.html`, `tests/test_people_and_audit.py` |
| 14 Oct | **R0 Phase 3 wrap-up**: real Rule 2 and Rule 3 tests replace the placeholders; junk-input sweep of every web form; `seed_data` refuses to run with production settings; `pip-audit` is clean and now blocks CI | Roadmap 3.6–3.8 and launch safety | `tests/rules/`, `tests/test_bad_input.py`, `apps/core/models.py`, `apps/audit/models.py`, `apps/evaluations/models.py`, `apps/awards/views.py`, `apps/awards/services.py`, `seed_data.py`, `.github/workflows/ci.yml` |
| 14 Oct | **R1 Award administration**: an *Awards* menu for staff: create an award (name, dates, who applies, fee, judges per report, blind judging, up to 5 rounds), a scoring-criteria editor (weights must total 100 per round; locked once judges have scored), a judge-panel picker, and status control that refuses to open an award until it has a form, criteria and judges. Rounds with judges can't be removed | Brief: run many programmes with no code; verified in the browser (a third award created and opened) and in `tests/test_award_admin.py` | `apps/awards/services.py`, `apps/awards/views.py`, `apps/awards/urls.py`, `templates/awards/award_*.html`, `_award_steps.html`, `apps/core/templatetags/ui.py` |
| 14 Oct | Fix: the staff home listed only *submitted* reports as needing judges, so a report short of judges after a decline or a conflict never showed | Bug reported by the user | `apps/core/overview.py`, `templates/awards/staff_home.html` |
| 14 Oct | Supabase-ready: transaction-pooler setting (`DB_TRANSACTION_POOLER`), S3 path-style option, fixed connection reuse in production (`CONN_MAX_AGE` was set where Django ignores it), Supabase steps in the runbook | Staging on Supabase | `config/settings/{base,prod}.py`, `docs/Deployment.md` |
| 14 Oct | Production setup: Gunicorn, WhiteNoise, `Dockerfile.prod` (non-root), `docker-compose.prod.yml`, `deploy/nginx.conf`, Sentry, S3 option, SMTP settings, CI production-image job, runbook | Ready to deploy once hosting is chosen | `requirements/prod.txt`, `config/settings/{base,prod}.py`, `docs/Deployment.md`, `.github/workflows/ci.yml` |
| 15 Oct | **Duplicate organisations, end to end**: `DuplicateCandidate` found on every profile save (same PAN, same cleaned name, similar name); Duplicate review with one tab per award (only pairs that both entered it), merge / keep separate / undo, *Decline as duplicate* on the card; conflicts and verification follow the main record after a merge; demo seed adds 3 second registrations | The screen was sample data | `apps/accounts/duplicates.py`, `apps/awards/views.py`, `templates/awards/duplicates.html` |
| 15 Oct | **Staff accept or decline each entry**: new status *Accepted for judging*; only accepted entries go to judges; declining needs a reason the applicant sees | Entries went straight to judges | `apps/applications/services.py`, `templates/awards/entries.html` |
| 15 Oct | **Applicant sees judging progress** ("1 of 3 judges finished · 1 reviewing now"), counts only | It looked stuck on *Assigned to judges* | `apps/evaluations/services.py`, `templates/entries/` |
| 15 Oct | **Results board** for every role (`/results/`): decided results per award, ranked; applicants see the successful entries and their own, staff/managers the full ranking of their awards | Nobody could see results once they were out | `apps/core/results.py`, `templates/core/results.html` |
| 15 Oct | **Re-evaluation goes to the award manager**: one step (a leader if there's no manager), then straight to choosing new judges; the result is decided again and the board shows "Re-evaluated · was …" | The request; it was staff check then leader confirm | `apps/applications/services.py`, `apps/core/approvals.py`, `templates/awards/reevaluations.html` |
| 15 Oct | Fixes found while testing: the API couldn't accept entries (`change-status` now takes `accepted`); entries declined at the staff check counted as results; only high duplicate matches block accepting; Postman verifies the organisation after it applies (staff only see organisations on their awards) and decides re-evaluations as the award manager | Postman run and browser check | `apps/applications/api/serializers.py`, `postman/build_collection.py` |
| 15 Oct | **Edit requests: staff check, then the award manager confirms** (not a leader; a leader only for an award with no manager). Staff on the award take the first step (the manager only if the award has no staff); the manager sees *Waiting for you to confirm* on Entries and on their home page; the applicant's status page, form and notifications name the award manager. Judges' score changes still go to leadership | The request | `apps/core/approvals.py`, `templates/awards/entries.html`, `templates/entries/` |
| 15 Oct | **Duplicate review is staff-only; leaders' *All applications* page removed**: menu items gone for leaders and award managers, Duplicate review refuses them (403), the overview button opens *Approve results* | The request | `apps/core/demo_data.py`, `apps/awards/views.py`, `apps/dashboard/` |

---

## 5. Key decisions and assumptions (see `docs/decisions/decision-log.md`, D1–D8)

- **One login form**; the role is stored on the account and never chosen at login. The API's optional `role` must match the account.
- **Self sign-up creates applicants only.** Staff, judges and leaders are created by a leader (API), an admin, or the seed command.
- **Service layer** (`apps/*/services.py`) holds every rule. It is used by the API, the web screens, the admin and the seed, so they can't disagree.
- **Judge access is enforced in `get_queryset()`**: another judge's report returns **404**, so ids can't be probed.
- **Soft delete** for Award and Application; **PROTECT** on assignments and evaluations so history survives.
- **Scores are stored as rows** (`CriterionScore`), so the database enforces 1–10. The weighted total is out of 10.
- **Judges don't declare conflicts**; staff record them (12 Oct meeting). Recording a conflict withdraws open assignments.
- **Declined reports go back to the pool**; organisations must be verified before judges are assigned (13 Oct meeting).
- **Bulk assign is all or nothing**; **only leaders deactivate accounts**.
- **Django templates rather than a separate SPA** for the 3.5 time box; JWT is for API clients.
- **Assumption:** the seed data and demo awards stand in for real programmes; nothing real has been imported.

---

## 6. Bugs found and fixed

| Bug | Fix | Where |
|---|---|---|
| The users migration needed a default for `created_at` | Hand-written data migration | `accounts/migrations/0003` |
| Tests hit the login throttle and used the wrong settings | `--ds=config.settings.test`; throttles off in tests | `pytest.ini`, `config/settings/test.py` |
| JWT signing key too short | Longer default; `JWT_SIGNING_KEY` falls back to `SECRET_KEY` | `config/settings/base.py` |
| Failed logins were written to the audit log | Only successful logins are recorded | `apps/accounts/api/views.py` |
| OpenAPI warnings (duplicate names, enum collisions) | Renamed serializers, overrides | `api/serializers.py`, settings |
| Seed skipped users with an empty password | Set the password when unusable | `seed_data.py` |
| **204 responses had a JSON body** (breaks HTTP clients) | Empty body on 204 | `apps/core/api/renderers.py` |
| Logout with a broken refresh token → 500 | 400 with a message | `apps/accounts/api/serializers.py` |
| `eligible-judges?round=abc` → 500 | 400 | `apps/applications/api/views.py` |
| `true` accepted as a score of 1 | Booleans rejected | `apps/evaluations/services.py` |
| Field errors said only "Request failed." | The message names the field | `apps/core/api/exceptions.py` |
| Login limit blocked a full Postman run | 60/min in development only | `config/settings/dev.py` |
| **Blind judging leaked the title and file names** | Hidden in blind rounds | `apps/assignments/services.py` |
| **Permanent records could be bulk-deleted** (`ScoreChange`, `AuditLog`: queryset `.delete()` / `.update()` skipped the model checks) | Append-only queryset blocks bulk changes | `apps/core/models.py` |
| Judge panel and criteria editor crashed (500) on a non-number id or round | Ignored or explained | `apps/awards/views.py`, `apps/awards/services.py` |
| Award settings page crashed after the move to real data (old demo link) | Link removed | `templates/awards/settings.html` |

---

## 7. Known issues, limitations and technical debt

| # | Item | Impact |
|---|---|---|
| 1 | ~~Form-version editor uncommitted~~ Done | n/a |
| 2 | ~~No document upload~~ Done (R2): PDF/JPG/PNG uploads with permission-checked downloads. Files are stored locally until an S3 bucket is configured | n/a |
| 3 | ~~Notifications in-app only~~ Done (R4): email for every notification and a Notifications page. Real delivery needs an SMTP account (development prints emails to the console) | n/a |
| 4 | ~~Duplicate review~~ Real since 15 Oct. The **public marketing pages** still use sample content (`apps/core/demo_data.py`) | Not real data |
| 5 | ~~No screen to create awards~~ Done (R1). Remaining: the older *Award settings* screen still edits only the 2 demo awards and overlaps with the new award page (both save to the same tables); merge in R8. New awards don't appear on the public marketing pages yet (they do for applicants) | Two places to edit the demo awards |
| 6 | ~~No account screen or audit viewer~~ Done (R5). Invites need a real email service in production to arrive | n/a |
| 7 | No search/export to CSV or PDF; no results publication to applicants beyond status | Reporting gap |
| 8 | ~~Rule 2/3 placeholder tests~~ Done (real tests), including conflicts across merged duplicate organisations (15 Oct) | n/a |
| 9 | Some N+1 queries (`report_for_judge` per row, per-award counts) | Slow at scale |
| 10 | Not deployed yet: production image, settings and runbook exist (`docs/Deployment.md`), but no hosting, domain, bucket or email account is chosen | Can't go live until those are picked |
| 11 | Dev database on port 8000 holds older seed answers and one probe-modified draft evaluation | Demo looks leakier than the code is |
| 12 | `Application.title` is shown to staff and leaders and is free text | Fine; noted because judges' view hides it |
| 13 | ~~Stray `package-lock.json` in the repo root (no Node app)~~ Removed | n/a |

---

## 8. Project structure

```
AwardApplication/
├── manage.py                     Django entry point
├── Dockerfile · docker-compose.yml   Dev image (runserver) and db + web services
├── Dockerfile.prod · docker-compose.prod.yml · deploy/nginx.conf   Production: Gunicorn, Nginx, HTTPS
├── .env.production.example   Every production variable (placeholders)
├── render.yaml · railway.json · deploy/start.sh   Render / Railway deploy config and container start-up
├── requirements/{base,dev,prod}.txt   Runtime, dev and production-server dependencies
├── pyproject.toml · pytest.ini   ruff config; pytest uses config.settings.test
├── .env.example                  Every environment variable with a safe default
├── .github/workflows/ci.yml      Lint, migration check, tests on Postgres 16
├── config/
│   ├── settings/{base,dev,test,prod}.py   Split settings
│   ├── urls.py                   Web routes, /admin/, /api/docs/
│   └── api_urls.py               All /api/v1/ routes
├── apps/
│   ├── accounts/    User, ApplicantProfile, JudgeProfile; login/sign-up/reset; role_required; api/
│   ├── awards/      Award, AwardRound, FormVersion, Criterion; staff screens; api/
│   ├── applications/ Application, Attachment; services (draft→submit→status); api/
│   ├── assignments/ JudgeAssignment, ConflictOfInterest; eligible judges, blind view; api/
│   ├── evaluations/ Evaluation, CriterionScore, ScoreChangeRequest, ScoreChange; api/
│   ├── notifications/ Notification + API
│   ├── audit/       AuditLog + record()
│   ├── core/        Public pages, shared models, API envelope/permissions/pagination, overview counts, seed_data
│   ├── entries/     Applicant screens (no tables)
│   ├── judging/     Judge screens (no tables)
│   └── dashboard/   Leadership screens (no tables)
├── templates/       Page templates per app + portal_base.html, partials/
├── static/          css/main.css, js/main.js
├── tests/           pytest: api/, rules/, smoke, auth, role homes, web workflow, settings
├── postman/         Collection, environment, CHECKLIST.md, build_collection.py
└── docs/            Roadmap, API, Data model, Setup, testing, decisions, meetings, reports
```

---

## 9. How to run locally

```bash
cp .env.example .env
```
```bash
docker compose up -d
```
This starts PostgreSQL and the app, runs the migrations, loads the seed data and serves http://localhost:8000. To reload the demo data later:
```bash
docker compose exec web python manage.py seed_data
```
Tests and lint:
```bash
docker compose exec web pytest -q
```
```bash
docker compose exec web ruff check .
```
Without Docker, see `docs/Setup.md` (venv, `pip install -r requirements-dev.txt`, `migrate`, `seed_data`, `runserver`).

**Key environment variables:** `DJANGO_SETTINGS_MODULE`, `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `JWT_SIGNING_KEY`, `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS`, `CORS_ALLOWED_ORIGINS`, `THROTTLE_*`, `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`, `LOG_LEVEL`, `DEMO_PASSWORD`.

**Test logins** (password = `DEMO_PASSWORD` in your `.env`):

| Role | Email | Lands on |
|---|---|---|
| Leader | `leader@awards.example` | `/leadership/` |
| Staff | `staff@awards.example`, `staff2@awards.example` | `/staff/` |
| Judge | `kapoor@judges.example`, `rao@judges.example`, `iyer@judges.example` | `/judge/` |
| Applicant | `priya@acme.example` (+4 more, see `docs/Setup.md`) | `/applicant/` |

API docs: http://localhost:8000/api/docs/ · Postman: `postman/README.md`.
