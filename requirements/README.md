# requirements/

| File | What it holds |
|---|---|
| `base.txt` | What the app needs to run (Django, DRF, SimpleJWT, django-filter, CORS, drf-spectacular, PostgreSQL driver) |
| `dev.txt` | `base.txt` plus tests and code quality (pytest, pytest-django, factory_boy, ruff) |

The root `requirements.txt` and `requirements-dev.txt` just point here, so older instructions still work.
