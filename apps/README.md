# apps/

**The application itself.** All the Python code that makes the website work lives here, split into small parts called **Django apps**, one per job.

| Folder | Job | Who it serves |
|---|---|---|
| [core/](core/) | Public website, shared helpers, sample data | Everyone |
| [accounts/](accounts/) | Users and login | Everyone |
| [awards/](awards/) | Award setup: settings, form builder, entries, judge assignment | Programme staff |
| [entries/](entries/) | Applications: dashboard, organisation profile, form, status | Applicants |
| [judging/](judging/) | Assignments and scoring | Judges |
| [dashboard/](dashboard/) | One view of all awards, review queue, approvals | Leadership |

**Why split it this way:** each part matches one user from the brief, so code is easy to find. A judging problem lives in `judging/`.

**Every app has the same basic files:**

| File | What it does |
|---|---|
| `__init__.py` | Empty. Tells Python this folder is a package |
| `apps.py` | Registers the app with Django |
| `models.py` | Database tables for this app (most are still planned) |
| `views.py` | Functions that build each page |
| `urls.py` | Which web address runs which view |
| `admin.py` | Shows this app's tables on the `/admin/` screen |
| `migrations/` | Instructions that build and change this app's database tables |
