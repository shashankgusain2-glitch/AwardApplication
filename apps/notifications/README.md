# apps/notifications/

**Notifications: in the app and by email** (for example "New report to judge").

| File | What it does |
|---|---|
| `models.py` | `Notification` (user, kind, message, link, read or not) |
| `services.py` | `notify()` creates the notification and emails it after the change is saved (a failed email is logged, never undoes the action); `notify_role()` tells every active user with a role (e.g. all staff); `emails_off()` for the demo seed; `mark_read()`, `mark_all_read()` |
| `views.py` · `urls.py` | `/notifications/`: each user's own list, open (marks read, follows only links inside the site), mark all read |
| `api.py` | `/api/v1/notifications/`: each user sees and marks their own |
| `admin.py` | Notifications list |
| [migrations/](migrations/) | Database tables for this app |

**Who is told what:** applicants (organisation verified or not, application submitted, edit allowed or refused, final result); judges (new assignment, score-change decision); staff (a judge declined, an applicant asks to edit, a judge asks to change a score). Email links start with `SITE_URL`.
