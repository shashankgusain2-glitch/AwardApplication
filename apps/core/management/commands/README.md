# apps/core/management/commands/

**Custom commands for the project.**

| File | Command | What it does now |
|---|---|---|
| `seed_demo.py` | `python manage.py seed_demo` | **Nothing yet.** It prints "No demo data yet". The website's sample data comes from `apps/core/demo_data.py`, not the database. When real tables are built, this command will fill them with fake demo data (two awards, judges, organisations including duplicates) in one go. |

Each file here becomes a command named after the file.
