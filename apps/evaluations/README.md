# apps/evaluations/

**Judges' scores, and the permanent record of every score change.**

| File | What it does |
|---|---|
| `models.py` | `Evaluation` (one per assignment; weighted total), `CriterionScore` (1–10, enforced by the database), `ScoreChangeRequest`, `ScoreChange` (can't be edited or deleted; Rule 3) |
| `services.py` | Save scores midway, submit (needs every criterion), mark the report scored when enough judges finish, ask/allow a change, change scores with a reason |
| `api/` | `/api/v1/evaluations/`, `/api/v1/score-change-requests/` |
| `admin.py` | Evaluations with scores; score changes are read-only |
| [migrations/](migrations/) | Database tables for this app |
