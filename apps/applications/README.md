# apps/applications/

**Applications (the applicant's "report") and their attachments.**

| File | What it does |
|---|---|
| `models.py` | `Application` (reference, applicant, award, form version, answers, status, edit request flags; soft delete; one live report per applicant per award) and `Attachment` (max 10 MB) |
| `services.py` | Create a draft, save answers midway, submit (checks required answers), ask staff to allow changes, staff allow/refuse, status changes (reject; leaders approve). Every change is audited |
| `api/` | `/api/v1/applications/`: applicants see only their own; staff and leaders see all |
| `admin.py` | Applications with attachments inline (shows soft-deleted ones too) |
| [migrations/](migrations/) | Database tables for this app |
