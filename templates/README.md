# templates/

**The HTML pages.** Each page is HTML with gaps (like `{{ award.name }}`) that the Python views fill in.

## What it does in the application

| File / folder | What it holds |
|---|---|
| `base.html` | **Layout for the public website**: banner, top menu, footer. Public pages slot into it |
| `portal_base.html` | **Layout for every portal** (applicant, judge, staff, award manager, leadership): sidebar menu for the current role, notifications count, messages, page heading |
| [core/](core/) | Public website pages |
| [entries/](entries/) | Applicant pages |
| [judging/](judging/) | Judge pages |
| [awards/](awards/) | Programme staff pages |
| [dashboard/](dashboard/) | Leadership pages |
| [partials/](partials/) | Small pieces reused on several pages |

Each sub-folder is named after the app whose views use it.
