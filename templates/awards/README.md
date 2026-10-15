# templates/awards/

**Programme staff and award manager pages** (built by `apps/awards/views.py`). Each person only sees the awards they are on.

| File | Page |
|---|---|
| `award_list.html` | The awards this person is on, with readiness and team (managers get a Team button) |
| `award_form.html` | Create (leaders, with the award manager) or edit an award (details, dates, rounds, blind judging) |
| `_award_steps.html` | The set-up checklist (details → form → criteria → panel → team for managers), what's missing, and the status control |
| `award_criteria.html` | Scoring criteria per round with live totals |
| `award_panel.html` | Pick the judges for the award's panel |
| `award_team.html` | Who runs the award: the award manager (leaders choose), its staff, and invite a new staff member onto the team |
| `staff_home.html` | Real work waiting today: organisations to verify, submitted reports with no judges, open requests, and every award's counts |
| `settings.html` | **Award settings** for both awards side by side: round types, blind judging, judges per entry, who applies, fee, closing date |
| `form_builder.html` | An award's published form versions and their questions, which are required and which are hidden in blind judging |
| `form_edit.html` | Edit the questions (text, section, type, required, hidden in blind judging, remove, add new) and publish as a new version |
| `entries.html` | Every application (search, filter) plus the decisions waiting: verify organisations, edit requests, score-change requests |
| `assign_list.html` | Reports that still need judges |
| `reevaluations.html` | Re-evaluation requests waiting for the award manager (reason, result, judges' totals; approve and choose new judges, or refuse), entries being re-evaluated (with a link to choose judges), and recent decisions |
| `assign.html` | The eligible judges for one report, best first; assign the ones ticked or fill with the best. Conflicted judges are never shown |
| `duplicates.html` | Possible duplicate organisations, one tab per award (only pairs that both entered it), with Merge / Keep separate / Undo; `_duplicate_side.html` is one organisation with its entries and a *Decline as duplicate* button |
