# Project Roadmap

**Status key:** ✅ Done · 🔄 In progress · ⏳ Not started

## Contents

- [Overview](#overview)
- [Phase 1 · Planning](#phase-1--planning)
- [Phase 2 · Skeleton](#phase-2--skeleton and frontend)
- [Phase 3 · Core Development](#phase-3--core-development)
- [Phase 4 · Testing](#phase-4--testing)
- [Phase 5 · Deployment](#phase-5--deployment)
- [Phase 6 · Maintenance and Updates](#phase-6--maintenance-and-updates)

## Overview

| Phase | Name | Status | Milestone |
|---|---|---|---|
| 1 | Planning | ✅ Done | Workflows mapped, roadmap drafted |
| 2 | Skeleton | 🔄 In progress | Skeleton app ready for review |
| 3 | Core Development | ✅ Done | All main features working on real data |
| 4 | Testing | ⏳ Ongoing (after each Phase 3 milestone) | All tests pass, no critical bugs |
| 5 | Deployment | ⏳ Not started | App live in production |
| 6 | Maintenance and Updates | ⏳ Not started | Steady support and regular updates |

---

## Phase 1 · Planning

**Status:** ✅ Done

**Goal:** Understand the users and their workflows.

**Work:**

- [x] User workflow analysis
- [x] Roadmap draft

**Milestone:** Workflows mapped, roadmap drafted.

---

## Phase 2 · Skeleton

**Status:** 🔄 In progress

**Goal:** Show the user flow visually, also moving with the frontend

**Work:**

- [ ] Skeleton app with the full user flow
- [ ] Review of flows and gaps in both frontend and users workflow

**Milestone:** Skeleton app ready for review.

---

## Phase 3 · Core Development

**Status:** ✅ Done (14 Oct 2026). Steps 3.1 to 3.8 are done; see the notes under each step.

**Goal:** Build the real features and connect the screens to real logic.

**Estimated time:** 4 working days (about 32 hours)

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

- [x] Decide what information the app keeps (users, tasks, statuses) and how the pieces connect.
- [x] Create the database.

> **Why first:** changing the data model later breaks everything built on top of it.

### 3.2 Backend foundation (2 hours)

- [x] Set up the server: folder structure, settings, error handling, and the database connection.
- [x] Add a health-check endpoint that confirms the server is running and can reach the database.

### 3.3 Authentication and roles (3 hours)

- [x] Build login and logout.
- [x] Give each user type a role. Roles decide who can see and do what, so a normal user can't open admin pages.

> **Why before features:** every feature needs to know who is using it.

> **Done (14 Oct 2026):** one login form sends each role to its own home page, and each home shows only that user's real data from the database (applicant: own applications; judge: own assignments, with Accept and Decline; staff: work waiting today; leadership: every award's progress). Other roles' pages give 403, and only admins can open `/admin/`. Tested in `tests/test_role_homes.py`. The remaining screens move to real data in 3.5.

### 3.4 Core API (6 hours)

- [x] Build the endpoints the frontend uses to talk to the backend, such as *create item*, *get list* and *update status*.
- [x] Test each endpoint on its own with Postman.

> **Done (14 Oct 2026):** the API gaps were filled (`/auth/me/`, deactivate and activate users, bulk assign, dashboard summary, lookups, fuller judge rows) and six bugs found while testing were fixed. [postman/](../postman/README.md) has a ready-to-import collection (116 requests, with tests on each, including no token, wrong role, another judge's report and invalid data) and a checklist. It passes in full on fresh seed data. Details: [API.md](API.md).

### 3.5 Frontend and backend integration (4 hours)

- [x] Replace the fake data in the skeleton with real data from the API.
- [x] Add loading spinners, error messages and empty-state screens.
- [ ] Hold a quick review (1 hour) before the big feature work, to catch problems early.

> **Result:** the skeleton works for real.

> **Done (14 Oct 2026):** every applicant, judge, staff and leadership screen now reads and writes the real database through the same services as the API (the pages are server-rendered Django templates, so there is no separate loading state; each page has empty and error states). The whole flow (apply → verify → assign → grade → approve) was run end to end on the seed data, in the browser and in `tests/test_web_workflow.py`. Still sample content: the public marketing pages and the duplicate-review screen (no duplicate model yet). Writing new form versions in the form builder is part of 3.6.

### 3.6 Feature slices (8 hours)

The biggest step.

- [ ] Build one complete feature at a time: screen, logic and data together.
- [ ] Start with the most important user flow, so something works early.

> If time runs short, drop the least important slices.

> **Done (14 Oct 2026):** the main flows work start to finish on real data: apply (with file uploads) → verify → assign → grade → approve, email notifications, and staff creating and opening a new award (`tests/test_web_workflow.py`, `tests/test_award_admin.py`). Quick review: closed a Rule 3 gap (permanent records could be bulk-deleted), replaced the placeholder Rule 2/3 tests with real ones. 3.7: every web form was sent junk input; two crashes found and fixed (`tests/test_bad_input.py`). 3.8: code tidied, docs and plan files updated; the main README is maintained by the project owner.

### 3.7 Validation and edge cases (3 hours)

Make the app handle bad situations without crashing:

| Situation | How the app handles it |
|---|---|
| Empty fields | Show a clear message so the user can fix and resubmit |
| Wrong input | Validate it and show what is wrong |
| Lost connection | Save the user's data locally and retry when the connection is back |
| Expired session | Ask the user to log in again without losing their work |

### 3.8 Mid-point review and cleanup (2 hours)

- [ ] Demo the app against the user flows from Phase 1.
- [ ] Tidy the code and hold a code review.
- [ ] Update the README.
- [ ] List the shortcuts taken so they can be fixed later.

**Milestone:** all main features work on real data, with roles, validation and error handling in place.

## Phase 4 · Testing(1 day)

**Status:** ⏳ Not started

**Goal:** Make sure everything we build works correctly.

Testing happens in two ways:

1. **Continuous testing:** after each Phase 3 milestone (3.1 to 3.8), test what was just built before moving on.
2. **Full testing phase:** once Phase 3 is complete, test the whole app end to end:
  - [ ] Each user flow from start to finish
  - [ ] Every role and its permissions
  - [ ] The edge cases from 3.7
  - [ ] Fix bugs and test again

**Milestone:** all test cases pass and no critical bugs are open.

---

## Phase 5 · Deployment

**Status:** ⏳ Not started

**Goal:** Put the app live for real users.

**Work:**

- [ ] Set up the production server and database
- [ ] Configure the domain, security settings and backups
- [ ] Deploy and run a final smoke test on the live app

**Milestone:** the app is live and reachable by users.

---

## Phase 6 · Maintenance and Updates

**Status:** ⏳ Not started

**Goal:** Keep the app running smoothly and keep improving it.

**Work:**

- [ ] Fix bugs reported by users
- [ ] Release regular updates and improvements
- [ ] Take support requests and send update notices by email
- [ ] Watch the app's performance and backups

**Milestone:** ongoing, with a regular update cycle.