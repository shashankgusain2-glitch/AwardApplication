# apps/core/

**The public website and the shared parts every other app uses.**

## What it does in the application

- Shows the **public pages**: Home, About us, Awards list (with sector filter), each Award's page, and Log in.
- Holds the **sample content** for the public pages (award descriptions, stats, past winners) and the duplicate-review screen. Every portal screen for the five roles reads the real database.
- Adds the organisation name and the portal menus to **every page** automatically.

## Files

| File / folder | What it does |
|---|---|
| `views.py` | Builds the public pages (home, about, awards, award detail, login) |
| `urls.py` | Addresses: `/`, `/about/`, `/awards/`, `/awards/<name>/`, `/login/` |
| `overview.py` | Real counts for the staff home and the leadership overview (per award: drafts, submitted, being judged, scored, approved, rejected, judging progress), and `summary_for(user)` behind `GET /api/v1/dashboard/summary/` |
| `demo_data.py` | Sample content: the organisation, the 8-award catalogue for the public pages (2 fully built, used by `seed_data`), the portal menus, and the duplicate-review examples. Award settings staff change are saved in the database, not here |
| `context_processors.py` | Sends the organisation details, portal menus and a CSS/JS version number to every page |
| `models.py` | `TimeStampedModel`: a shared building block that adds "created" and "updated" times |
| [templatetags/](templatetags/) | A small helper for templates |
| [management/commands/](management/commands/) | Custom commands you run with `python manage.py ...` |
| [migrations/](migrations/) | Database changes for this app (none yet) |

## Added in the backend foundation (14 Oct 2026)

| File / folder | What it does |
|---|---|
| `models.py` | `TimeStampedModel` and `SoftDeleteModel` (with `objects` hiding deleted rows and `all_objects` showing all) |
| `services.py` | `BusinessRuleError`: services raise it; the API turns it into a clear 400 message |
| `validators.py` | GSTIN and PAN format checks |
| [api/](api/) | Shared API pieces: response format, error handler, pagination, role permissions, health |
