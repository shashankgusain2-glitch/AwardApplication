# apps/applications/

**Applications (the applicant's "report") and their uploaded files.**

| File | What it does |
|---|---|
| `models.py` | `Application` (reference, applicant, award, form version, answers, status, edit request flags; soft delete; one live report per applicant per award) and `Attachment` (PDF/JPG/PNG, max 10 MB) |
| `services.py` | Create a draft, save answers midway, submit (checks required answers), ask staff to allow changes, staff allow/refuse, status changes (reject; leaders approve). Every change is audited and the right people are notified |
| `files.py` | Uploads on file questions (type checked by the file's first bytes, size, only while editable, one file per question) and who may download: the owner, staff, leaders, and judges with a live assignment. Blind rounds give judges a neutral file name |
| `views.py` · `urls.py` | `/files/<id>/`: download, permission-checked (others get 404) |
| `api/` | `/api/v1/applications/` (applicants see only their own; staff and leaders see all), `/applications/{id}/attachments/` (upload), `/api/v1/attachments/{id}/download/` |
| `admin.py` | Applications with attachments inline (shows soft-deleted ones too) |
| [migrations/](migrations/) | Database tables for this app |
