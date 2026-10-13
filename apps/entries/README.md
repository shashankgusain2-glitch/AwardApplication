# apps/entries/

**Applications: the applicant's screens.** Every page reads and writes the real database through `apps/applications/services.py` and `apps/accounts/services.py`, the same functions the API uses.

## What it does in the application

| Page | Address | What the applicant does |
|---|---|---|
| Dashboard | `/applicant/` | See **their own applications**, their organisation's verification status, unsent drafts, and open awards they can enter |
| Organisation profile | `/applicant/organisation/` | Fill company details once: GSTIN and PAN (format-checked), sector, size, turnover, contact. A verified organisation's GSTIN is locked |
| Application form | `/applicant/application/` | Pick one of their applications, or start one for an open award |
| | `/applicant/application/<award>/` | Start, then fill the form section by section (saved on every Save / Next / Back), submit, or ask staff to edit after submitting. Each award has its own questions, from the form version the application was started on (Rule 4) |
| Application status | `/applicant/status/` | Each application's steps with dates (from the audit log): draft, submitted, judges assigned, being judged, scored, decision |
| Delete a draft | `/applicant/application/draft/<id>/delete/` | Drafts only (soft delete) |

An applicant only ever reaches their own applications: another applicant's gives 404.

## Files

| File | What it does |
|---|---|
| `views.py` | The applicant pages: profile form, application form (start, save, submit, ask to edit), status timeline |
| `urls.py` | The `/applicant/...` addresses |
| `models.py` | No tables here: applications live in `apps/applications/`, profiles in `apps/accounts/` |
| [migrations/](migrations/) | Empty: this app has no tables |
