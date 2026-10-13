# apps/accounts/migrations/

**Step-by-step instructions that build and change this app's database tables.**

## What it does in the application

When `models.py` changes, `python manage.py makemigrations` writes a numbered file here (`0001`, `0002`...) describing the change. `python manage.py migrate` applies those files to the database, so every computer (yours, Docker, GitHub CI) ends up with the same tables.

## In this app

Has `0001_initial.py`, which creates the **User** table. This is the only real database table so far.

**Rule:** never edit or delete a migration that has already been applied. Make a new one instead.
