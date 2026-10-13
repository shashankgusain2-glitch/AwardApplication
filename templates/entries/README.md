# templates/entries/

**Applicant pages** (built by `apps/entries/views.py`).

| File | Page |
|---|---|
| `dashboard.html` | The applicant's own applications with their status, their organisation's verification status, unsent drafts, and open awards they can enter |
| `organisation.html` | The organisation profile form, with field errors and the verification status |
| `_field.html` | One labelled text field with its error (used by `organisation.html`) |
| `application_pick.html` | Pick one of your applications, or start one for an open award |
| `application_start.html` | Start an application: give it a title |
| `application_form.html` | One section of the form, with the section list and progress; Save / Next / Back / Submit; read-only once submitted, with "ask to edit" |
| `application_status.html` | Each application's steps with dates |
