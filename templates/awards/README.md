# templates/awards/

**Programme staff pages** (built by `apps/awards/views.py`).

| File | Page |
|---|---|
| `award_list.html` | All awards, with readiness and a New award button |
| `award_form.html` | Create or edit an award (details, dates, rounds, blind judging) |
| `_award_steps.html` | The set-up checklist (details → form → criteria → panel), what's missing, and the status control |
| `award_criteria.html` | Scoring criteria per round with live totals |
| `award_panel.html` | Pick the judges for the award's panel |
| `staff_home.html` | Real work waiting today: organisations to verify, submitted reports with no judges, open requests, and every award's counts |
| `settings.html` | **Award settings** for both awards side by side: round types, blind judging, judges per entry, who applies, fee, closing date |
| `form_builder.html` | An award's published form versions and their questions, which are required and which are hidden in blind judging |
| `form_edit.html` | Edit the questions (text, section, type, required, hidden in blind judging, remove, add new) and publish as a new version |
| `entries.html` | Every application (search, filter) plus the decisions waiting: verify organisations, edit requests, score-change requests |
| `assign_list.html` | Reports that still need judges |
| `assign.html` | The eligible judges for one report, best first; assign the ones ticked or fill with the best. Conflicted judges are never shown |
| `duplicates.html` | Possible duplicate companies, with Merge or Keep separate (sample data) |
