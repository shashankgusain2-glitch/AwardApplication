# apps/core/management/commands/

**Custom commands for the project.**

| File | Command | What it does |
|---|---|---|
| `seed_data.py` | `python manage.py seed_data` | Loads demo data **through the service layer**: 1 leader, 2 staff, 3 judges, 5 applicant organisations, the two demo awards (rounds, form v1, criteria), 10 reports at different stages, judge assignments and some finished evaluations. Safe to run again. Prints the test logins (password: `DEMO_PASSWORD`) |
| `seed_demo.py` | `python manage.py seed_demo` | Old name; runs `seed_data` |

Test data only: never run these on a real deployment.
