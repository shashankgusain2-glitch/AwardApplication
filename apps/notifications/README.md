# apps/notifications/

**In-app notifications** (for example "New report to judge").

| File | What it does |
|---|---|
| `models.py` | `Notification` (user, kind, message, link, read or not) |
| `services.py` | `notify()` and `mark_read()`; email or SMS can be added here later |
| `api.py` | `/api/v1/notifications/`: each user sees and marks their own |
| `admin.py` | Notifications list |
| [migrations/](migrations/) | Database tables for this app |
