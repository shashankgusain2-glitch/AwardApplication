# Code Guide: every file, what it does, and why it's there

> **Updated 13 Oct 2026** for the applicant workflow. Older mock screens were removed (restore point: git tag `v0.2-skeleton-ui`).

## How a page reaches your screen

```text
Browser asks for /events/
  → config/urls.py          "/" addresses go to the entries app
  → apps/entries/urls.py    "events/" runs the events view
  → apps/entries/views.py   events(): loads the 2 events from the database
  → templates/entries/events.html   fills the page
  → templates/base.html             adds the header and messages
  → static/css/main.css             makes it look good
```

Django's pattern: **Model** (database table) → **View** (Python function) → **Template** (HTML).

## The tree

```text
AwardApplication/
├── README.md, manage.py, requirements*.txt, pytest.ini
├── .env.example, .gitignore, .gitattributes, .dockerignore
├── Dockerfile, docker-compose.yml      run the app + PostgreSQL with one command
├── .github/workflows/ci.yml            GitHub runs the tests on every push
├── config/                             settings and the top-level address map
├── apps/
│   ├── accounts/   users + email verification
│   ├── awards/     events (awards) + versioned forms
│   ├── entries/    organisations + applications + applicant pages + staff page
│   ├── core/       home page, shared bits, demo staff account
│   ├── judging/    planned
│   └── dashboard/  planned
├── templates/      HTML pages
├── static/         CSS (and a placeholder JS file)
├── tests/          automatic checks
└── docs/           all documents
```

## Root files

| File | What it does |
|---|---|
| `README.md` | What the project is, what works, how to run it |
| `manage.py` | Django's command tool (`runserver`, `migrate`, `seed_demo`) |
| `requirements.txt` / `requirements-dev.txt` | Packages to install (Django, PostgreSQL driver, settings reader; pytest for tests) |
| `.env.example` | Template for local settings; real values go in `.env` (never committed) |
| `Dockerfile`, `docker-compose.yml` | Build and run the app and database; on start it migrates and creates the demo staff account |
| `.github/workflows/ci.yml` | Runs migrations check and tests on GitHub for every push |

## `config/`

| File | What it does |
|---|---|
| `settings.py` | Apps switched on, database, login page (`LOGIN_URL`), emails printed instead of sent, `SHOW_DEMO_EMAIL_CODE` |
| `urls.py` | `/admin/`, `/verify/...` (accounts), the entries pages, and the home page |

## `apps/accounts/`: who you are

| File | What it does | Why |
|---|---|---|
| `models.py` | Custom **User** with a unique email | Set before the first migration; hard to change later |
| `views.py` | **verify_email** (sends a 6-digit code), **verify_code** (checks it: expires in 10 minutes, 5 tries max, then logs you in), **logout** | No passwords to forget; matches "verify themselves first" from the 12 Oct meeting |
| `urls.py` | `/verify/`, `/verify/code/`, `/verify/logout/` | |

## `apps/awards/`: events and their forms

| File | What it does | Why |
|---|---|---|
| `models.py` | **Award** (an event: name, summary, deadline, open or not). **FormVersion** (the questions, stored as data, numbered v1, v2…) | Staff change questions by adding a new version; old applications keep theirs (**Rule 4**) |
| `migrations/0002_two_events.py` | Creates the **2 events** with 5 simple questions each | So the demo works straight after `migrate` |
| `admin.py` | Shows events and forms in `/admin/` | Staff can edit without code until a form editor exists |

## `apps/entries/`: the applicant workflow

| File | What it does | Why |
|---|---|---|
| `models.py` | **Organisation** (name, GSTIN unique, holder's PAN, owner). **Application** (organisation, event, form version, answers, status, edit request) | One report per organisation per event (database rule); status from the 12 Oct meeting |
| `validators.py` | Checks GSTIN and PAN **format** | Stops typos and fake-looking IDs; real verification later |
| `forms.py` | Email, code, organisation and edit-request forms; builds each event's form from its stored questions | Required answers are checked only on Submit, so drafts can be saved half done |
| `views.py` | **register**, **events**, **start** (one application per event), **application** (save, submit, status), **request_edit**, and staff **staff** / **staff_action** | The whole applicant workflow, plus the staff confirmation it needs |
| `urls.py` | `/register/`, `/events/`, `/events/<event>/apply/`, `/applications/<id>/`, `/staff/` | |
| `admin.py` | Organisations and applications in `/admin/` | Handy for staff while screens are minimal |

## `apps/core/`

| File | What it does |
|---|---|
| `views.py`, `urls.py` | The home page |
| `context_processors.py` | Organisation name on every page; version number on CSS/JS links so browsers don't use old copies |
| `models.py` | `TimeStampedModel`, a shared building block for later |
| `management/commands/seed_demo.py` | Creates the demo staff account `staff@awards.example` |

## `templates/`

| File | Page |
|---|---|
| `base.html` | Layout: header, menu (changes when logged in), messages |
| `partials/field.html` | One form field with its label, hint and errors |
| `core/home.html` | Home: the 2 events and the Apply button |
| `accounts/verify_email.html`, `verify_code.html` | Step 1: email and code (demo shows the code on screen) |
| `entries/register.html` | Step 2: organisation, GSTIN, PAN |
| `entries/events.html` | Step 3: choose an event |
| `entries/application.html` | Step 4: the form, status tracker, and edit request |
| `entries/staff.html` | Staff: approve edits, move status |

## `tests/`

| File | What it checks |
|---|---|
| `conftest.py` | Helpers: a logged-in applicant with an organisation, and a staff user |
| `test_smoke.py` | Home shows the 2 events; private pages send you to verification |
| `test_applicant_workflow.py` | The whole applicant workflow (see [testing.md](testing.md)) |
| `rules/test_rule4_form_versions.py` | Old applications keep and show their own form version ✅ |
| `rules/test_rule1/2/3_*.py` | Planned, for when judging is built |
