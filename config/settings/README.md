# config/settings/

**Settings, split by environment.** Pick one with `DJANGO_SETTINGS_MODULE`.

| File | Used for |
|---|---|
| `base.py` | Everything shared: apps, database, auth, REST API, JWT, CORS, throttling, logging. Values that differ per machine come from `.env` |
| `dev.py` | Local development (default): debug on, local frontends allowed |
| `test.py` | Tests: fast password hashing, no rate limits, emails kept in memory |
| `prod.py` | Production: requires `SECRET_KEY` and `ALLOWED_HOSTS`; HTTPS, secure cookies, HSTS |
