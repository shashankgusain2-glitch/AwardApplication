# deploy/import-templates/

**Example CSV files for `python manage.py import_csv`.** Copy them, replace the rows with real data, and keep the header row. Open and save them in Excel as **CSV UTF-8**.

| File | Columns (* = required) | Notes |
|---|---|---|
| `people.csv` | email*, name*, role*, expertise, priority, max_open_assignments | role: `staff`, `manager`, `judge` or `leader` (applicants sign up themselves). The last three columns are for judges only (priority 1 = first choice; defaults 5 and 10) |
| `awards.csv` | name*, rounds*, sector, summary, opens_on, closes_on, applicant_type, judges_per_report, blind_judging, entry_fee, manager, staff, judges | rounds: `desk`, `site` or `live`, up to 2, separated by `;`. Dates `2027-03-31` or `31 Mar 2027`. applicant_type: `organisation`, `team` or `unit`. blind_judging: yes/no. manager, staff, judges: emails from people.csv (several separated by `;`) |
| `criteria.csv` | award*, round*, label*, weight* | award = the award's name. Weights must add up to 100 in each round |
| `questions.csv` | award*, label*, type*, section, subsection, required, identifying | type: `text`, `textarea` or `file`. identifying = yes hides the answer from judges on blind awards. Rows stay in this order on the form |

Any file can be left out. The real files contain people's emails: don't commit them to the repository.
