# apps/accounts/

**Users and login.**

## What it does in the application

- Defines the **User** table: everyone who uses the platform (applicants, judges, staff, leadership).
- Each user has a unique **email** and an `is_leader` flag for leadership.
- Users can be managed on the admin screen at `/admin/`.

## Files

| File | What it does |
|---|---|
| `models.py` | Our own `User`, built on Django's standard user. Set up before the first migration, because changing it later is very hard |
| `admin.py` | Shows users on `/admin/` |
| [migrations/](migrations/) | `0001_initial.py` creates the user table (the only real table so far) |

**Planned:** email-based login (a code or link sent to the user's email, no password).
