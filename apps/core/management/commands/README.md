# apps/core/management/commands/

**Custom commands for the project.**

| File | Command | What it does |
|---|---|---|
| `seed_data.py` | `python manage.py seed_data` | Loads demo data **through the service layer**: 1 leader, 1 award manager (`manager@awards.example`, runs both demo awards), 2 staff (`staff@` on both awards, `staff2@` on Kaizen only), 3 judges, 5 applicant organisations, the two demo awards (rounds, form v1, criteria), 10 reports at different stages, judge assignments and some finished evaluations. Safe to run again. Prints the test logins (password: `DEMO_PASSWORD`) |
| `seed_judges.py` | `python manage.py seed_judges [--award <slug>]` | Adds 12 spare demo judges (different expertise, priority 4–8, 10 open assignments each) and puts them on **every award's panel** without removing anyone, so new awards have free judges. Run it again after creating an award. Safe to run again |
| `seed_managers.py` | `python manage.py seed_managers` | Adds 5 spare demo **award managers** (`manager.<name>@awards.example`) who manage nothing yet, so a leader can pick one for each new award. Safe to run again |
| `seed_demo.py` | `python manage.py seed_demo` | Old name; runs `seed_data` |

Test data only: never run the seed commands on a real deployment.

| File | Command | What it does |
|---|---|---|
| `import_csv.py` | `python manage.py import_csv <folder> --by <leader email> [--commit] [--invite]` | **For the live site.** Imports real staff, managers, judges, leaders and awards (rounds, team, judge panel, criteria, form questions) from `people.csv`, `awards.csv`, `criteria.csv` and `questions.csv` through the service layer, audited under the leader. A dry run unless `--commit`; one bad row means nothing is saved and every problem is listed by file and line. `--invite` emails new accounts a set-your-password link. Safe to run again (people matched by email, awards by name; nobody is removed). Templates: [deploy/import-templates/](../../../../deploy/import-templates/) |
