# Project Roadmap

**Status key:** ✅ Done · 🔄 In progress · ⏳ Not started

**Last updated:** 16 Oct 2026 (`main` at `04d5ee8`). The day-by-day record is in [PROGRESS_LOG.md](../PROGRESS_LOG.md); the remaining work and launch plan are in [FUTURE_GOALS_AND_DEPLOYMENT.md](../FUTURE_GOALS_AND_DEPLOYMENT.md).

## Contents

- [Overview](#overview)
- [Timeline](#timeline)
- [Phase 1 · Planning](#phase-1--planning)
- [Phase 2 · Skeleton](#phase-2--skeleton)
- [Phase 3 · Core Development](#phase-3--core-development)
- [Phase 3+ · Changes after the client reviews](#phase-3--changes-after-the-client-reviews)
- [Phase 4 · Testing](#phase-4--testing)
- [Phase 5 · Deployment](#phase-5--deployment)
- [Phase 6 · Maintenance and Updates](#phase-6--maintenance-and-updates)

## Overview

| Phase | Name | Status | Milestone |
|---|---|---|---|
| 1 | Planning | ✅ Done (11–12 Oct) | Workflows mapped, roadmap drafted |
| 2 | Skeleton | ✅ Done (11–13 Oct) | Clickable screens for every role, reviewed |
| 3 | Core Development | ✅ Done (14 Oct) | All main features working on real data |
| 3+ | Changes after the client reviews | ✅ Done (15–16 Oct) | Award managers, duplicates, entry checks, results board, award-level approval |
| 4 | Testing | 🔄 In progress | 441 automated tests and the Postman collection pass; load, security and UAT still to do |
| 5 | Deployment | 🔄 Demo site live (15 Oct) | Live for real users: domain, email, backups, real accounts |
| 6 | Maintenance and Updates | ⏳ Not started | Steady support and regular updates |

## Timeline

| Date | What happened |
|---|---|
| 30 Sep – 9 Oct | Research, client meetings and daily reports (`docs/reports/`) |
| 11 Oct | User workflows, product roadmap, git workflow, Django skeleton, architecture and test plan, clickable screens for every role, code guide |
| 12 Oct | Pre-coding roadmap; the two demo awards made correct; round types (desk / site / live) with blind judging only in desk review; abstraction doc |
| 13 Oct | A day's workflow build was reverted (owner's decision); renamed *Awards Platform*; a README in every folder |
| 14 Oct | Phase 3 end to end: login and roles, data model and services, REST API and Postman, every screen on real data, form versions (Rule 4), uploads, notifications by email, award administration, people management, production setup, Render / Railway / Supabase configs |
| 15 Oct | Award managers and award-only access; CSV import for real data; duplicate organisations end to end; staff accept or decline each entry; judging progress for applicants; results board and re-evaluation by the award manager; **demo site live** on Render + Supabase |
| 16 Oct | Leaders only get notifications they act on; edit requests stay with staff and the award manager; leaders approve each award's result as a whole; Audit log page and leaders' work queues removed; Form builder for programme staff only |

---

## Phase 1 · Planning

**Status:** ✅ Done (11–12 Oct)

**Goal:** Understand the users and their workflows.

- [x] User workflow analysis ([User-Workflows.md](User-Workflows.md))
- [x] Roadmap draft ([Product-Roadmap.md](Product-Roadmap.md))
- [x] Decision log started ([decisions/decision-log.md](decisions/decision-log.md))

**Milestone:** Workflows mapped, roadmap drafted.

---

## Phase 2 · Skeleton

**Status:** ✅ Done (11–13 Oct). The sample-data screens were then replaced by real data in step 3.5.

**Goal:** Show the user flow visually, together with the frontend.

- [x] Skeleton app with the full user flow (clickable screens for the website and every portal, commit `d8a51db`)
- [x] Review of flows and gaps in both the frontend and the users' workflows (12 and 13 Oct meetings; changes recorded in the decision log)

**Milestone:** Skeleton app ready for review.

---

## Phase 3 · Core Development

**Status:** ✅ Done (14 Oct 2026). Steps 3.1 to 3.8 are done; see the notes under each step.

**Goal:** Build the real features and connect the screens to real logic.

**Estimated time:** 4 working days (about 32 hours). **Actual:** done on 14 Oct, building on the skeleton and the planning work.

| # | Step | Time | Day | Done when |
|---|---|---|---|---|
| 3.1 | ✅ Data model and database | 3 hours | Day 1 | Database created with all tables and relationships |
| 3.2 | ✅ Backend foundation | 2 hours | Day 1 | Health-check endpoint shows the server is up and connected to the database |
| 3.3 | ✅ Authentication and roles | 3 hours | Day 1 | Login and logout work, and each role sees only its own pages |
| 3.4 | ✅ Core API | 6 hours | Day 2 | Every endpoint tested on its own in Postman |
| 3.5 | ✅ Frontend and backend integration | 4 hours | Day 2–3 | Skeleton runs on real data |
| 🔍 | ✅ *Quick review* | *1 hour* | *Day 3* | *Problems caught before feature work starts* |
| 3.6 | ✅ Feature slices | 8 hours | Day 3–4 | Most important flows work from start to finish |
| 3.7 | ✅ Validation and edge cases | 3 hours | Day 4 | Bad situations show a clear message instead of crashing |
| 3.8 | ✅ Mid-point review and cleanup | 2 hours | Day 4 | Demo done, code tidied, README updated |

### Day-by-day plan

| Day | Work |
|---|---|
| **Day 1** | 3.1 Data model and database → 3.2 Backend foundation → 3.3 Authentication and roles |
| **Day 2** | 3.4 Core API → start 3.5 Integration |
| **Day 3** | Finish 3.5 Integration → Quick review → start 3.6 Feature slices |
| **Day 4** | Finish 3.6 Feature slices → 3.7 Validation and edge cases → 3.8 Review and cleanup |

### 3.1 Data model and database (3 hours)

- [x] Decide what information the app keeps (users, awards, applications, assignments, scores, statuses) and how the pieces connect ([Data-Model.md](Data-Model.md)).
- [x] Create the database.

> **Why first:** changing the data model later breaks everything built on top of it.

### 3.2 Backend foundation (2 hours)

- [x] Set up the server: folder structure, settings, error handling, and the database connection.
- [x] Add a health-check endpoint that confirms the server is running and can reach the database (`/api/v1/health/`).

### 3.3 Authentication and roles (3 hours)

- [x] Build login and logout.
- [x] Give each user type a role. Roles decide who can see and do what, so a normal user can't open admin pages.

> **Why before features:** every feature needs to know who is using it.

> **Done (14 Oct 2026):** one login form sends each role to its own home page, and each home shows only that user's real data. Other roles' pages give 403, and only admins can open `/admin/`. A fifth role, the **award manager**, was added on 15 Oct (D9). Tested in `tests/test_authentication.py` and `tests/test_role_homes.py`.

### 3.4 Core API (6 hours)

- [x] Build the endpoints the frontend uses to talk to the backend, such as *create item*, *get list* and *update status*.
- [x] Test each endpoint on its own with Postman.

> **Done (14 Oct 2026):** the API gaps were filled and six bugs found while testing were fixed. [postman/](../postman/README.md) has a ready-to-import collection (now 124 requests, 280 checks, with tests on each, including no token, wrong role, another judge's report and invalid data) and a checklist. It passes in full on the seed data. Details: [API.md](API.md).

### 3.5 Frontend and backend integration (4 hours)

- [x] Replace the fake data in the skeleton with real data from the API.
- [x] Add loading spinners, error messages and empty-state screens.
- [x] Hold a quick review (1 hour) before the big feature work, to catch problems early.

> **Done (14 Oct 2026):** every applicant, judge, staff and leadership screen reads and writes the real database through the same services as the API (server-rendered Django templates, so there is no separate loading state; each page has empty and error states). The whole flow ran end to end on the seed data, in the browser and in `tests/test_web_workflow.py`. Duplicate review became real on 15 Oct; only the public marketing pages still use sample content.

### 3.6 Feature slices (8 hours)

The biggest step.

- [x] Build one complete feature at a time: screen, logic and data together.
- [x] Start with the most important user flow, so something works early.

> **Done (14 Oct 2026):** apply (with file uploads) → verify → assign → grade → decide works on real data, with email notifications, form versions and award administration (`tests/test_web_workflow.py`, `tests/test_award_admin.py`). Quick review: closed a Rule 3 gap (permanent records could be bulk-deleted) and replaced the placeholder Rule 2/3 tests with real ones.

### 3.7 Validation and edge cases (3 hours)

Make the app handle bad situations without crashing:

| Situation | How the app handles it |
|---|---|
| Empty fields | Show a clear message so the user can fix and resubmit |
| Wrong input | Validate it and show what is wrong (every web form was sent junk input: `tests/test_bad_input.py`) |
| Lost connection | Answers are saved section by section on the server, so nothing typed before the last save is lost |
| Expired session | The user is asked to log in again and returns to the page they were on |

### 3.8 Mid-point review and cleanup (2 hours)

- [x] Demo the app against the user flows from Phase 1.
- [x] Tidy the code and hold a code review.
- [x] Update the README (the main README is maintained by the project owner; folder READMEs updated).
- [x] List the shortcuts taken so they can be fixed later ([PROGRESS_LOG.md](../PROGRESS_LOG.md), known gaps).

**Milestone:** all main features work on real data, with roles, validation and error handling in place.

---

## Phase 3+ · Changes after the client reviews

**Status:** ✅ Done (15–16 Oct). Each change has a decision record (D9–D16).

| Change | Decision |
|---|---|
| Award managers: one per award, chosen by leadership; staff and managers only reach their own awards | D9 |
| Duplicate organisations found automatically, reviewed per award by programme staff (merge / keep separate / undo) | D10, D13 |
| Staff accept or decline each submitted entry; only accepted entries go to judges | D10 |
| Applicants see judging progress (counts only) | D10 |
| Results board for every role; re-evaluation asked from the board and decided by the award manager, who chooses fresh judges | D11 |
| Edit requests: staff check, the award manager confirms; never leadership | D12, D14 |
| Leaders only get notifications they act on; Audit log page, Requests to confirm, Re-evaluations, All applications and Duplicate review removed from leaders | D13, D14, D15 |
| The award manager decides each entry; **leadership approves each award's result as a whole**, which publishes it | D16 |
| `import_csv` command to load real staff, judges and awards | progress log, 15 Oct |
| Form builder for programme staff only | progress log, 16 Oct |

---

## Phase 4 · Testing

**Status:** 🔄 In progress

**Goal:** Make sure everything we build works correctly.

Testing happens in two ways:

1. **Continuous testing:** after each change, the automated tests run (441 passing, 0 skipped) and CI runs lint, the migration check and the tests on every push.
2. **Full testing phase**, before real users:
   - [x] Each user flow from start to finish (`tests/test_web_workflow.py`, `tests/test_award_admin.py`, `tests/test_reevaluation.py`)
   - [x] Every role and its permissions (parametrised role tests; the Postman collection's wrong-role and no-token checks)
   - [x] The edge cases from 3.7 (`tests/test_bad_input.py`)
   - [ ] Load test (many applicants submitting near the deadline)
   - [ ] Security scan (OWASP ZAP baseline; `pip-audit` already runs in CI)
   - [ ] User acceptance test with real staff, a judge, an award manager and a leader
   - [ ] Fix bugs and test again

**Milestone:** all test cases pass and no critical bugs are open.

---

## Phase 5 · Deployment

**Status:** 🔄 Demo site live since 15 Oct 2026 (Render free plan + Supabase PostgreSQL), deploying `main` automatically. It holds demo data and demo accounts on purpose.

**Goal:** Put the app live for real users.

- [x] Production settings, image and runbook ([Deployment.md](Deployment.md))
- [x] Set up the production server and database (Render + Supabase)
- [x] Deploy and run a smoke test on the live app
- [ ] Own domain, real email sending (SPF/DKIM), file storage bucket, backups with a tested restore
- [ ] Replace the demo accounts with a real leader, and load real people and awards (`import_csv`)
- [ ] Monitoring (Sentry, uptime alerts)

**Milestone:** the app is live and reachable by real users.

---

## Phase 6 · Maintenance and Updates

**Status:** ⏳ Not started (begins after the real launch)

**Goal:** Keep the app running smoothly and keep improving it.

- [ ] Fix bugs reported by users
- [ ] Release regular updates and improvements
- [ ] Take support requests and send update notices by email
- [ ] Watch the app's performance and backups

**Milestone:** ongoing, with a regular update cycle.
