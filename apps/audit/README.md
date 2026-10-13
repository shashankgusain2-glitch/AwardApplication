# apps/audit/

**Who did what, to which record, and when.** Append-only.

| File | What it does |
|---|---|
| `models.py` | `AuditLog` (user, action, entity, entity id, before/after changes, IP, time). Refuses edits and deletes |
| `services.py` | `record()`: called by every service for logins, assignments, scores, score changes, status changes, verifications |
| `admin.py` | Read-only audit trail with filters |
| [migrations/](migrations/) | Database tables for this app |
