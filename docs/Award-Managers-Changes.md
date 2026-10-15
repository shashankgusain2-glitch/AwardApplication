# Award managers and award-only staff access: what changed

**Date:** 15 Oct 2026 · Decision record: [D9 in the decision log](decisions/decision-log.md)

## What you asked for

1. Staff should only reach the awards **allocated to them**, not every award.
2. A new kind of user, the **award manager**, works under leadership. Each award is assigned to one manager, and the manager only reaches that award (or those awards).
3. **Leaders** still see every award.
4. **Creating a new award** moves from the staff area to the leader.
5. Add whatever else is needed to make that work.

## How it works now

| Who | Sees | Can do |
|---|---|---|
| **Leader** | Every award | Create awards and pick each award's manager; choose any award's staff; add people (including award managers); everything leaders did before (approve results, confirm requests, audit log) |
| **Award manager** *(new role)* | Only the awards they manage | Everything staff do, on those awards (details, form, criteria, judge panel, entries, verify organisations, assign judges, first step of requests); choose the award's staff; invite a new staff member onto the team |
| **Programme staff** | Only the awards they are allocated to | The same staff work as before, limited to those awards |
| Judges, applicants | Unchanged | Unchanged |

Anything on another award (its pages, reports, files, requests) gives **404 Not Found**, so ids in a URL can't be used to look at it.

## New pages

| Page | Address | Who |
|---|---|---|
| **Awards and managers** | `/leadership/awards/` | Leader: every award with its manager and staff, a warning for awards without an active manager, **+ New award**, and **Team** per award |
| **New award** | `/leadership/awards/new/` | Leader only. The usual award form plus an **Award manager** picker; after saving, it goes to the Team page |
| **Team** | `/staff/awards/<award>/team/` | Award manager of that award, or a leader. Tick the staff on the team; a leader also picks the manager. "Invite a new staff member" creates a staff account, puts it on the team and emails a set-your-password link |

## Changed pages

- **Staff portal** (`/staff/...`): opens for staff **and** award managers. My awards, Awards, Award settings, Form builder, Entries, Assign judges and the requests list only show their own awards. Managers' sidebar reads "Awards and teams", and each award's set-up steps gain **5. Team**.
- **Removed "+ New award"** from the staff home page and the staff Awards list. `/staff/awards/new/` no longer exists.
- **Organisations to verify**: staff and managers see the organisations that have applied to one of their awards (leaders still see all).
- **Leadership overview**: each award shows its manager.
- **People page**: "Award manager" is a new role in the Add person form; staff and managers are listed with the awards they are on.

## Behind the scenes

| Area | Change |
|---|---|
| Data | New role `manager` ("Award manager") on users. `Award.manager` (one per award) and `Award.staff` (the allocated staff). Migrations: `accounts/0005_award_manager_role`, `awards/0003_award_manager_award_staff` |
| The rule | New `apps/awards/access.py`: `awards_for(user)` says which awards someone may work on. Every list and check below uses it |
| Services | Reports, assignments, evaluations and file downloads are filtered by it. Assigning judges, recording a manual reject and the staff step of two-step requests check that the person is on that award. Only leaders can create awards. `set_team()` saves an award's team (audited; new members are notified) |
| Notifications | An applicant's edit or re-evaluation request and a judge's score-change request now go to **that award's staff and manager**, not to every staff member |
| Accounts | Leaders can create award manager accounts. Managers can create **staff** accounts only (for their own team) |
| API | Award managers can use every staff endpoint. Applications, profiles, score-change requests and the dashboard summary are filtered to the person's awards |
| Demo data (`seed_data`) | New login **manager@awards.example** (manages both demo awards). `staff@awards.example` is on both awards; `staff2@awards.example` is on Kaizen only, to show the restriction |
| Tests | New `tests/test_award_access.py` (13 tests: who sees what, pages, API, requests, notifications, creating awards, teams, invites). Existing tests updated for the leader-only award creation; test factories put test staff on every award unless a test says otherwise. **393 passed, 1 skipped** |
| Docs | Updated: `apps/awards`, `apps/accounts`, `apps/dashboard`, `apps/core` and the `templates` READMEs, `docs/API.md`, `docs/Data-Model.md`, `docs/User-Workflows.md`, the seed command README, and decision **D9** |

## What you need to do on your own database

The upgrade gives nobody extra access, so after it:

- **Existing staff see no awards** until they are allocated. For example, `one@staff.example` (shanky) has none yet. Allocate them on **Leadership → Awards and managers → Team**.
- **DemoAward has no manager yet.** Pick one on its Team page. You first need an award manager account: add one on the People page with the role "Award manager", or use the demo `manager@awards.example`.
- The dev database was already migrated and re-seeded during this change.

## Not changed

- Leaders still give the final confirmation on two-step requests and approve results. Managers take the first (staff) step.
- Judges, applicants, blind judging, conflicts of interest and the score audit work as before.
- The conflicts list and the user list in the API are still not filtered by award; they hold people and organisations, not award data.
