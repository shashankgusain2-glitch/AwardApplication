# Phase 2: Data Modeling & Backend Foundation: Plan and Checklist

> **Assumption** (placeholders in the brief): Phase 2 of the roadmap, **10 working days**.
> Status as of **14 Oct 2026**, with the remaining items updated on **16 Oct**. ✅ done · 🟡 partly · ⏳ remaining.

## Checklist

| Area | Item | Status |
|---|---|---|
| **Data model** | Model reviewed and approved ([Data-Model.md](Data-Model.md)) | ✅ |
| | Custom `User` (email login, `name`, `role`, timestamps) | ✅ |
| | `ApplicantProfile` (incl. staff verification), `JudgeProfile` (priority, workload) | ✅ |
| | `Award`, `AwardRound`, `FormVersion` (Rule 4), `Criterion` | ✅ |
| | `Application`, `Attachment` | ✅ |
| | `JudgeAssignment`, `ConflictOfInterest` (Rule 2) | ✅ |
| | `Evaluation`, `CriterionScore`, `ScoreChangeRequest`, `ScoreChange` (Rule 3) | ✅ |
| | `Notification`, `AuditLog` | ✅ |
| | `TimeStampedModel`, `SoftDeleteModel` + managers | ✅ |
| **Database** | Migrations committed (incl. data migration for existing users) | ✅ |
| | Constraints (unique, check: score 1–10, weights, dates) and indexes | ✅ |
| | `seed_data`: 1 leader, 2 staff, 3 judges, 5 applicants, 10 reports, assignments, scores | ✅ |
| **Structure** | Apps: accounts, awards, applications, assignments, evaluations, notifications, audit, core | ✅ |
| | Settings split base/dev/test/prod, `.env.example`, no hard-coded secrets | ✅ |
| | Business logic in `services.py`; thin views | ✅ |
| | Requirements split `requirements/base.txt`, `dev.txt` | ✅ |
| **API** | DRF + routers under `/api/v1/` | ✅ |
| | JWT (access + refresh, rotation, blacklist on logout), role in claims, optional role check at login | ✅ |
| | Permissions: IsApplicant, IsStaff, IsJudge, IsLeader, IsStaffOrLeader, IsOwner | ✅ |
| | Object-level security in `get_queryset()` (404 for others' records) | ✅ |
| | Consistent `{success, data, message, errors}` responses | ✅ |
| | Pagination, filtering, search, ordering | ✅ |
| | CORS, throttling (login 10/min), password validators, prod HTTPS settings | ✅ |
| | Logging (console + rotating file), `/api/v1/health/` | ✅ |
| | Audit logging in the service layer | ✅ |
| | Admin for every model | ✅ |
| | Swagger docs at `/api/docs/` | ✅ |
| **Quality** | pytest + pytest-django + factory_boy; 227 tests | ✅ |
| | Required security tests (judge/applicant isolation, wrong-role login, only staff/leader assign, judges score only own) | ✅ |
| | ruff (lint + isort + format) configured; lint in CI | ✅ |
| **Remaining** (status on 16 Oct) | Attachment upload endpoint | ✅ Done 14 Oct (R2) |
| | Round 2 meeting details (date/link) on assignments | ⏳ |
| | Switch the server-rendered portal screens from sample data to these models | ✅ Done 14 Oct (step 3.5) |
| | Email sending for notifications | ✅ Done 14 Oct (R4); real delivery needs an email provider |
| | Real GSTIN/PAN verification service | ⏳ (later phase) |
| | Leaderboard / reporting for dashboards | 🟡 Leader overview and results board done (15–16 Oct); CSV/PDF export ⏳ (R6) |

## Day-by-day (10 working days)

| Day | Focus | Output | Status |
|---|---|---|---|
| 1 | Review existing code; draft data model + ER diagram | Data-Model.md approved | ✅ |
| 2 | Settings split, requirements split, core base models | `config/settings/*`, `requirements/*`, `core/models.py` | ✅ |
| 3 | Models and migrations for all apps; migrate existing data | 17 models, migrations | ✅ |
| 4 | Service layer: applications, assignments, evaluations, audit, notifications | `services.py` per app | ✅ |
| 5 | `seed_data` through the services; admin for every model | Demo data, admin | ✅ |
| 6 | API: auth (JWT), users, profiles, awards | `/api/v1/auth/`, `/users/`, `/profiles/`, `/awards/` | ✅ |
| 7 | API: applications, assignments, my-assignments, evaluations, conflicts, notifications | Remaining endpoints | ✅ |
| 8 | Response envelope, errors, pagination, filters, throttling, CORS, logging, health, Swagger | Cross-cutting pieces | ✅ |
| 9 | Tests (factories, security, workflows, data rules), ruff, CI | 227 tests passing, lint clean | ✅ |
| 10 | Attachment upload API, Round 2 meeting fields, docs polish, buffer | Remaining items above | ⏳ |

*Days 1–9 were completed in one working session on 14 Oct 2026. Day 10 is the buffer for the remaining items.*
