# .github/workflows/

**Automatic checks that run on GitHub (CI).**

## What it does

| File | What it does |
|---|---|
| `ci.yml` | On **every push and pull request**, GitHub starts a fresh computer with Python and PostgreSQL, installs the packages, checks the database migrations are up to date, and runs all the tests |

You see the result as ✅ or ❌ next to each commit on GitHub. Your reviewer can check the code works without running it.
