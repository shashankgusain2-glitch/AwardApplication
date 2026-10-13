# apps/accounts/

**Users, login, sign-up and access control.**

## What it does in the application

- **One login form for everyone** (`/login/`): email + password. The **role stored on the account** decides where the person goes (applicant, staff, judge or leader area). The role is never chosen by the person logging in.
- **Sign up** for applicants only (`/signup/`). Staff, judge and leader accounts are created by an admin at `/admin/` (or by `python manage.py seed_demo` for the demo).
- **Forgot password** (`/password-reset/`): emails a link that works for 1 hour (printed in the server log in the demo).
- **Log out** (`/logout/`, POST).
- **Access control** for every portal page: logged-out users go to the login page; the wrong role gets **403 Access Denied**.

## Files

| File | What it does |
|---|---|
| `models.py` | `User` with a unique email and one **role** (applicant, staff, judge, leader) |
| `backends.py` | Log in with email + password (case-insensitive email) |
| `forms.py` | Login form (email + password), sign-up form (validation, always creates an applicant) |
| `views.py` | Login, sign-up, logout, and the forgot-password pages |
| `urls.py` | `/login/`, `/signup/`, `/logout/`, `/password-reset/...` |
| `permissions.py` | `@role_required("judge")` and friends: protects every portal view; each role's home page |
| `admin.py` | Users on `/admin/`, with the role shown and editable |
| [migrations/](migrations/) | `0001` creates users; `0002` adds the role (and replaces the old `is_leader` flag) |

**Security:** passwords are stored hashed (PBKDF2-SHA256, salted), never as plain text. The session cookie is HttpOnly and SameSite=Lax (and HTTPS-only outside local development); the session stores the user id and role. See decision D6 in `docs/decisions/decision-log.md`.
