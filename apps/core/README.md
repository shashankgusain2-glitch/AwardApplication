# apps/core/

**The public website and the shared parts every other app uses.**

## What it does in the application

- Shows the **public pages**: Home, About us, Awards list (with sector filter), each Award's page, and Log in.
- Holds the **sample data** that fills every screen until real database tables are built.
- Adds the organisation name and the portal menus to **every page** automatically.

## Files

| File / folder | What it does |
|---|---|
| `views.py` | Builds the public pages (home, about, awards, award detail, login) |
| `urls.py` | Addresses: `/`, `/about/`, `/awards/`, `/awards/<name>/`, `/login/` |
| `demo_data.py` | **All sample data**: the organisation, 8 awards (2 fully built), applications, judges, scores, and the award settings staff can change (kept in the browser session for now) |
| `context_processors.py` | Sends the organisation details, portal menus and a CSS/JS version number to every page |
| `models.py` | `TimeStampedModel`: a shared building block that adds "created" and "updated" times |
| [templatetags/](templatetags/) | A small helper for templates |
| [management/commands/](management/commands/) | Custom commands you run with `python manage.py ...` |
| [migrations/](migrations/) | Database changes for this app (none yet) |
