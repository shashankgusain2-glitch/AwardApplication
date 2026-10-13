# apps/

**The application itself**, split into Django apps. Each app keeps its data (`models.py`), its business rules (`services.py`), and its part of the REST API (`api/`).

## Data, business logic and API

| Folder | Job |
|---|---|
| [core/](core/) | Shared base models (timestamps, soft delete), API building blocks, validators, demo data commands, public website pages |
| [accounts/](accounts/) | Users (email login, one role), applicant and judge profiles, web login/sign-up, JWT auth API |
| [awards/](awards/) | Awards, rounds, versioned forms, criteria; staff portal screens |
| [applications/](applications/) | Applications ("reports") and attachments |
| [assignments/](assignments/) | Judge assignments and staff-recorded conflicts |
| [evaluations/](evaluations/) | Scores and the permanent record of score changes |
| [notifications/](notifications/) | In-app notifications |
| [audit/](audit/) | Append-only audit trail |

## Server-rendered portal screens (sample data until Phase 3)

| Folder | Who |
|---|---|
| [entries/](entries/) | Applicant pages |
| [judging/](judging/) | Judge pages |
| [dashboard/](dashboard/) | Leadership pages |

**Rule:** views and serializers stay thin; business rules live in each app's `services.py`, which also writes the audit log.
