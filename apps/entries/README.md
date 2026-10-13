# apps/entries/

**Applications: the applicant's screens.**

## What it does in the application

| Page | Address | What the applicant does |
|---|---|---|
| Dashboard | `/applicant/` | See **their own real applications** from the database, their organisation's verification status, and open awards they can enter. The other pages still use sample data until step 3.5 |
| Organisation profile | `/applicant/organisation/` | Company details once: GSTIN, PAN, sector, size, turnover, contact |
| Application form | `/applicant/application/<award>/` | Fill the form section by section; each award has its own questions |
| Application status | `/applicant/status/` | Timeline of where the entry is |

## Files

| File | What it does |
|---|---|
| `views.py` | Builds the applicant pages and works out progress per section |
| `urls.py` | The `/applicant/...` addresses |
| `models.py` | **Planned** tables: Organisation, DuplicateCandidate, Application (remembers its form version, for Rule 4), Evidence |
| [migrations/](migrations/) | Database changes for this app (none yet) |
