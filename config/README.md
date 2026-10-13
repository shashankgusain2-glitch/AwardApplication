# config/

**Project-wide settings: the same for every award.**

## What it does in the application

This is the control panel Django reads when the app starts. It says which apps are switched on, which database to use, where pages and styles live, and which web address goes to which app.

| File | What it does |
|---|---|
| `settings.py` | Apps switched on, database (from `DATABASE_URL`), templates, static files, time zone (India), emails printed instead of sent. Secrets and machine-specific values come from the `.env` file |
| `urls.py` | The **top-level address map**: `/admin/`, `/applicant/` (entries), `/judge/` (judging), `/staff/` (awards), `/leadership/` (dashboard), everything else (core) |
| `wsgi.py`, `asgi.py` | Entry points for web servers when the app goes live |
| `__init__.py` | Empty. Marks the folder as a Python package |

**Not here:** each award's own settings (rounds, blind judging, questions). Those are data that staff change on screen, not project settings.
