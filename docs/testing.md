# Testing: what our tests check, and what they don't

> **Updated 13 Oct 2026** for the applicant workflow.

Run all tests: `pytest` (or `docker compose exec web pytest`).

## What the tests check

| Area | Test file | Checks | Status |
|---|---|---|---|
| Pages | `tests/test_smoke.py` | Home shows the 2 events; events, register and staff pages need verification first | ✅ |
| Email verification | `tests/test_applicant_workflow.py` | Right code logs you in; wrong code doesn't; more than 5 wrong codes start over; expired code is rejected | ✅ |
| Organisation | same | Valid GSTIN and PAN accepted (cleaned to upper case); bad formats rejected; the same GSTIN can't be registered twice | ✅ |
| Events and form | same | Only 2 events; each has its own form; one report per organisation per event; save midway keeps answers; submit needs required answers; submitted report is locked; can't open another organisation's report | ✅ |
| Edit with staff confirmation | same | Edit request → staff approve → applicant can edit and resubmit → locked again; declined request keeps it locked; applicants can't use staff actions | ✅ |
| Status | same | Applicant sees "judged" after staff move the report along | ✅ |
| **R4 Form versions** | `tests/rules/test_rule4_form_versions.py` | New applications use the newest form; old ones keep their version and still show their own questions and answers | ✅ (1 planned) |
| R1, R2, R3 | `tests/rules/` | Blind judging, conflicts, score changes | ⏳ Planned (judging not built) |

## What the tests don't check

- **Real email delivery:** emails are printed, not sent.
- **Real GSTIN/PAN verification:** only the format is checked.
- **How pages look** on different screens or browsers.
- **Load:** many applicants submitting on deadline day.
- **Security testing** beyond access rules (who can open what).
