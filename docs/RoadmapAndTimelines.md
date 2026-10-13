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
| 3 | Core Development | ⏳ Not started | All main features working on real data |
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

**Status:** ⏳ Not started

**Goal:** Build the real features and connect the screens to real logic.

**Estimated time:** 4 working days (about 32 hours)

| # | Step | Time | Day | Done when |
|---|---|---|---|---|
| 3.1 | Data model and database | 3 hours | Day 1 | Database created with all tables and relationships |
| 3.2 | Backend foundation | 2 hours | Day 1 | Health-check endpoint shows the server is up and connected to the database |
| 3.3 | Authentication and roles | 3 hours | Day 1 | Login and logout work, and each role sees only its own pages |
| 3.4 | Core API | 6 hours | Day 2 | Every endpoint tested on its own in Postman |
| 3.5 | Frontend and backend integration | 4 hours | Day 2–3 | Skeleton runs on real data |
| 🔍 | *Quick review* | *1 hour* | *Day 3* | *Problems caught before feature work starts* |
| 3.6 | Feature slices | 8 hours | Day 3–4 | Most important flows work from start to finish |
| 3.7 | Validation and edge cases | 3 hours | Day 4 | Bad situations show a clear message instead of crashing |
| 3.8 | Mid-point review and cleanup | 2 hours | Day 4 | Demo done, code tidied, README updated |

### Day-by-day plan

| Day | Work |
|---|---|
| **Day 1** | 3.1 Data model and database → 3.2 Backend foundation → 3.3 Authentication and roles |
| **Day 2** | 3.4 Core API → start 3.5 Integration |
| **Day 3** | Finish 3.5 Integration → Quick review → start 3.6 Feature slices |
| **Day 4** | Finish 3.6 Feature slices → 3.7 Validation and edge cases → 3.8 Review and cleanup |

### 3.1 Data model and database (3 hours)

- [ ] Decide what information the app keeps (users, tasks, statuses) and how the pieces connect.
- [ ] Create the database.

> **Why first:** changing the data model later breaks everything built on top of it.

### 3.2 Backend foundation (2 hours)

- [ ] Set up the server: folder structure, settings, error handling, and the database connection.
- [ ] Add a health-check endpoint that confirms the server is running and can reach the database.

### 3.3 Authentication and roles (3 hours)

- [ ] Build login and logout.
- [ ] Give each user type a role. Roles decide who can see and do what, so a normal user can't open admin pages.

> **Why before features:** every feature needs to know who is using it.

### 3.4 Core API (6 hours)

- [ ] Build the endpoints the frontend uses to talk to the backend, such as *create item*, *get list* and *update status*.
- [ ] Test each endpoint on its own with Postman.

### 3.5 Frontend and backend integration (4 hours)

- [ ] Replace the fake data in the skeleton with real data from the API.
- [ ] Add loading spinners, error messages and empty-state screens.
- [ ] Hold a quick review (1 hour) before the big feature work, to catch problems early.

> **Result:** the skeleton works for real.

### 3.6 Feature slices (8 hours)

The biggest step.

- [ ] Build one complete feature at a time: screen, logic and data together.
- [ ] Start with the most important user flow, so something works early.

> If time runs short, drop the least important slices.

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