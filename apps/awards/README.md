# apps/awards/

**Award setup: the programme staff's screens**, on the real database.

## What it does in the application

Staff run each award from here, with no code changes:

| Page | Address | What staff do |
|---|---|---|
| Awards | `/staff/awards/` | Every award with its status, rounds, panel and whether it's ready to open; **+ New award** |
| | `/staff/awards/new/` · `/staff/awards/<award>/` | Create or edit an award: name, sector, dates, who applies, fee, judges per report, blind judging, up to 5 rounds. A set-up checklist shows what's missing; the status control won't open an award without a form, criteria totalling 100 per round and at least one judge |
| | `/staff/awards/<award>/criteria/` | Scoring criteria per round (weights total 100); locked once judges have scored |
| | `/staff/awards/<award>/panel/` | Which judges may be assigned this award's reports |
| My awards | `/staff/` | Real work waiting today: organisations to verify, reports with no judges yet, open requests, and every award's counts |
| Award settings | `/staff/settings/` | Set round types (desk review, site visit, live presentation), blind judging, judges per entry, who applies, fee, closing date. **This is where the two awards are made to work differently.** Blind judging is blocked if every round is in person |
| Form builder | `/staff/form-builder/<award>/` | Each award's published form versions and their questions (which are required, which are hidden in blind judging, how many applications use each version). Published versions are read-only (Rule 4) |
| Edit questions | `/staff/form-builder/<award>/new-version/` | Change, add or remove questions and publish them as the **next version**. The current version never changes; applications already started keep their version (Rule 4) |
| Entries | `/staff/entries/` | Every application (search and filter by status and award), plus the decisions waiting: **verify organisations**, **allow or refuse edit requests**, **allow or refuse judges' score-change requests**, reject an ineligible report |
| Assign judges | `/staff/assign/` | Reports that still need judges |
| | `/staff/assign/<id>/` | The eligible judges for one report, best first (on the panel, no recorded conflict, under their workload limit). Assign the ones ticked, or "fill with the best". Conflicted judges are never offered |
| Duplicate review | `/staff/duplicates/` | Merge or separate companies with similar names. **Still sample data**: there is no duplicate-detection model yet |

## Files

| File | What it does |
|---|---|
| `views.py` | The staff pages and their actions (verify, decide edit, decide score change, reject, assign) |
| `urls.py` | The `/staff/...` addresses |
| `models.py` | `Award` (settings incl. blind judging, judges per report; soft delete), `AwardRound` (desk, site, live), `FormVersion` (read-only once published; Rule 4), `Criterion` (weights) |
| `services.py` | Award settings from the staff screen, form versions, criteria checks |
| `api/` | `/api/v1/awards/` (read-only, public) |
| [migrations/](migrations/) | Database changes for this app |

Settings staff save are stored in the `Award` and `AwardRound` tables, so judges and the public site see them too, and every change is audited. Every page here needs a **Staff** login.
