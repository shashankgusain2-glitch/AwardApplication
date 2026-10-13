# apps/core/templatetags/

**Small helpers that HTML templates can use.**

## What it does in the application

Django templates can't look up a value in a dictionary by a variable key on their own. This folder adds that.

| File | What it does |
|---|---|
| `ui.py` | The `get_item` filter: `{{ portal_nav|get_item:role }}` picks the right sidebar menu for the current user (applicant, judge, staff or leader) |
| `__init__.py` | Empty. Marks the folder as a Python package |

It's switched on for every template in `config/settings.py` (the `builtins` setting), so templates don't need to load it.
