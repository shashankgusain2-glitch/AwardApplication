# apps/accounts/migrations/

**Step-by-step instructions that build and change this app's database tables.**

## What it does in the application

When `models.py` changes, `python manage.py makemigrations` writes a numbered file here (`0001`, `0002`...) describing the change. `python manage.py migrate` applies those files to the database, so every computer (yours, Docker, GitHub CI) ends up with the same tables.

## In this app

`0001_initial.py` creates the **User** table; `0002_user_role.py` adds each user's **role** (applicant, staff, judge, leader) and replaces the old `is_leader` flag.

**Rule:** never edit or delete a migration that has already been applied. Make a new one instead.
