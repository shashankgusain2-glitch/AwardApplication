# apps/awards/

**Award setup: the programme staff's screens.**

## What it does in the application

Staff run each award from here, with no code changes:

| Page | Address | What staff do |
|---|---|---|
| My awards | `/staff/` | Today's to-do and their two awards |
| Award settings | `/staff/settings/` | Set round types (desk review, site visit, live presentation), blind judging, judges per entry, who applies, fee, closing date. **This is where the two awards are made to work differently.** Blind judging is blocked if every round is in person |
| Form builder | `/staff/form-builder/<award>/` | See each award's questions, which ones are hidden in blind judging, and locked form versions |
| Entries | `/staff/entries/` | Check new entries |
| Duplicate review | `/staff/duplicates/` | Merge or separate companies with similar names |
| Assign judges | `/staff/assign/` | Pick judges; conflicted judges are not offered |

## Files

| File | What it does |
|---|---|
| `views.py` | Builds the staff pages; checks and saves award settings |
| `urls.py` | The `/staff/...` addresses |
| `models.py` | **Planned** tables: Award, AwardCycle, FormVersion, Criterion, AwardStaff (described in comments) |
| [migrations/](migrations/) | Database changes for this app (none yet) |

Settings staff save are stored in the database (`AwardSetting` in `models.py`), so judges and the public site see them too. Every page here needs a **Staff** login.
