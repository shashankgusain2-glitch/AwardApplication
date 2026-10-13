# tests/

**Automatic checks.** Run with `pytest` (or `docker compose exec web pytest`). GitHub runs them, plus `ruff check .`, on every push.

| File / folder | What it checks |
|---|---|
| `conftest.py` | Shared helpers for the web-page tests: logged-in clients per role; fast password hashing |
| `factories.py` | factory_boy factories for users, awards, profiles and applications |
| [api/](api/) | The REST API: auth, permissions and object-level security, workflows, data rules |
| `test_authentication.py` | Web login, sign-up, logout, password reset, 403 for the wrong role, own data only |
| `test_smoke.py` | Every web page opens |
| `test_award_settings.py` | The two awards work differently via staff settings (saved in the Award tables and audited) |
| [rules/](rules/) | One file per rule from the brief |

What the tests check, and what they don't: [docs/testing.md](../docs/testing.md).
