# apps/awards/

**Award setup: the programme staff's and award managers' screens**, on the real database.

## What it does in the application

Staff and award managers run their awards from here, with no code changes. **Everyone here only sees the awards they are on** (`access.py`): staff the awards a leader or the award's manager allocated to them, managers the awards they manage. Another award's pages, reports, files and requests give 404. **New awards are created by leaders** (`/leadership/awards/new/`), who also pick each award's manager.

| Page | Address | What staff do |
|---|---|---|
| Awards | `/staff/awards/` | The awards this person is on, with status, rounds, team, panel and whether it's ready to open |
| | `/staff/awards/<award>/` | Edit an award: name, sector, dates, who applies, fee, judges per report, blind judging, up to 2 rounds. A set-up checklist shows what's missing; the status control won't open an award without a form, criteria totalling 100 per round and at least one judge |
| | `/staff/awards/<award>/criteria/` | Scoring criteria per round (weights total 100); locked once judges have scored |
| | `/staff/awards/<award>/panel/` | Which judges may be assigned this award's reports |
| Team | `/staff/awards/<award>/team/` | **Award managers and leaders:** choose which programme staff work on this award, and invite a new staff member straight onto the team. A leader also picks the award manager here. New team members are notified |
| My awards | `/staff/` | Real work waiting today on this person's awards: organisations to verify, reports with no judges yet, open requests, and each award's counts |
| Form builder | `/staff/form-builder/<award>/` | Each award's published form versions and their questions (which are required, which are hidden in blind judging, how many applications use each version). Published versions are read-only (Rule 4). **Programme staff only** (award managers see the step as "2. Application form (staff)") |
| Edit questions | `/staff/form-builder/<award>/new-version/` | Change, add or remove questions and publish them as the **next version**. The current version never changes; applications already started keep their version (Rule 4) |
| Entries | `/staff/entries/` | Every application on this person's awards (search and filter by status and award), plus the decisions waiting: **verify organisations**, **allow or refuse edit requests**, **allow or refuse judges' score-change requests**, reject an ineligible report |
| Assign judges | `/staff/assign/` | Reports that still need judges |
| Prepare results | `/staff/results/` | One tab per award: scored entries to decide (**Successful / Not successful**, with the judges' totals), decided entries (can still change), and **Send results to leadership** once nothing is with staff or judges. The award manager acts (staff, if it has no manager); staff can follow along |
| Re-evaluations | `/staff/re-evaluations/` | Applicants' re-evaluation requests on these awards. **The award manager decides** in one step (a leader, if the award has no manager); *Approve and choose new judges* goes straight to the assign page, where the first judges aren't offered. Staff see the list and progress but don't decide |
| | `/staff/assign/<id>/` | The eligible judges for one report, best first (on the panel, no recorded conflict, under their workload limit). Assign the ones ticked, or "fill with the best". Conflicted judges are never offered |
| Duplicate review | `/staff/duplicates/` | Possible duplicate organisations (found automatically; `apps/accounts/duplicates.py`), one tab per award: a pair is listed under an award only when **both** records entered it, the rest under *Not in the same award*. **Merge** (pick the main record; conflicts and verification then cover both), **Keep separate**, **Undo**. Merging is blocked while both have an active entry in the same award: *Decline as duplicate* on the card first. **Programme staff only** (not award managers or leaders) |

## Files

| File | What it does |
|---|---|
| `views.py` | The staff pages and their actions (verify, decide edit, decide score change, reject, assign) |
| `urls.py` | The `/staff/...` addresses |
| `access.py` | **Who works on which award**: `awards_for(user)` (leader: all; manager: the ones they manage; staff: the ones they are allocated to). Every staff page, service, API view, file download and request list filters through it |
| `models.py` | `Award` (settings incl. blind judging, judges per report; its `manager` and allocated `staff`; soft delete), `AwardRound` (desk, site, live), `FormVersion` (read-only once published; Rule 4), `Criterion` (weights) |
| `services.py` | Settings the public award pages read (`screen_overrides`), form versions, criteria checks, creating awards (leaders only), choosing an award's team (`set_team`) |
| `api/` | `/api/v1/awards/` (read-only, public) |
| [migrations/](migrations/) | Database changes for this app |

Settings staff save are stored in the `Award` and `AwardRound` tables, so judges and the public site see them too, and every change is audited. Every page here needs a **Staff** or **Award manager** login (the Team page: award manager or leader).
