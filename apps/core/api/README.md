# apps/core/api/

**Shared API building blocks.**

| File | What it does |
|---|---|
| `renderers.py` | Wraps every successful response as `{success, data, message, errors}` |
| `exceptions.py` | Turns every error (validation, 401, 403, 404, broken business rule, crash) into the same shape |
| `pagination.py` | `?page=` and `?page_size=` (max 100) |
| `permissions.py` | `IsApplicant`, `IsStaff`, `IsJudge`, `IsLeader`, `IsStaffOrLeader`, `IsOwner` |
| `views.py` | `/api/v1/health/` |
