# tests/

**Automatic checks.** Each test uses the website the way a person would, then checks the result. One command checks everything in a few seconds.

## What it does

| File / folder | What it checks |
|---|---|
| `test_smoke.py` | Every page opens for both awards; wrong addresses give "not found"; the sector filter works |
| `test_award_settings.py` | The two awards really work differently; saving settings changes the screens; one award doesn't affect the other; bad values are rejected; blind judging is refused when every round is in person |
| [rules/](rules/) | One file per rule from the brief |
| `__init__.py` | Empty. Marks the folder as a Python package |

## Run them

```bash
docker compose exec web pytest
```

GitHub also runs them on every push. **Skipped** tests are written before their feature exists and switch on once it's built. What the tests check, and what they don't: [docs/testing.md](../docs/testing.md).
