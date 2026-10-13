# Testing: what our tests check, and what they don't

> **Status:** test list written before the code. Tests marked *planned* are skipped until the feature is built.

Run all tests:

```bash
pytest
```

## What the tests check

| Rule / area | Test file | Checks | Status |
|---|---|---|---|
| Screens load | `tests/test_smoke.py` | Every page opens for both awards, every form section opens, unknown awards and entries give 404, sector filter works, Kaizen shows its own criteria | ✅ Running |
| **Two awards, no code** | `tests/test_award_settings.py` | The two awards differ in settings, criteria, eligibility and form; weights add up to 100; saving settings changes the public page; one award's settings don't affect the other; bad values are rejected; reset works | ✅ Running |
| **R1 Blind judging** | `tests/rules/test_rule1_blind_judging.py` + `tests/test_award_settings.py` | ✅ Identifying answers and file names hidden on blind awards; ✅ non-blind awards show the organisation; ✅ assignment list hides applicant only for blind awards; ✅ staff turning blind on/off changes what judges see; ✅ live presentation and site visit rounds are never blind; ✅ blind is rejected when every round is in person. ⏳ Judge API planned | ✅ running, ⏳ 1 planned |
| **R2 Conflict of interest** | `tests/rules/test_rule2_conflict_of_interest.py` | Staff record conflicts (judges don't declare them); a conflicted judge is never suggested; staff can't force it; conflicts match merged duplicate organisations; a conflict recorded after assignment removes it and reassigns | ⏳ Planned |
| **R3 Score audit** | `tests/rules/test_rule3_score_audit.py` | Change needs a reason; records who, when, old and new value; records can't be edited or deleted; Leader can't change scores | ⏳ Planned |
| **R4 Form versions** | `tests/rules/test_rule4_form_versions.py` | Published form can't be edited; edits create a new version; old applications open with their own version; removed questions still show on old applications | ⏳ Planned |

## What the tests don't check

- **Settings are kept in the browser session, not the database (yet).** Tests check that screens follow saved settings, not that they survive a restart.
- **Blind judging is tested on demo data.** The tests prove the hiding logic works; they move to the real tables when judging is built.

- **Uploaded files:** we don't check that PDFs or images contain no company names (blind judging can't redact file contents automatically).
- **Real GST/PAN verification:** only the format is checked.
- **Emails:** we check an email is created, not that it is delivered.
- **Load:** no test for many applicants submitting on deadline day.
- **Security:** no penetration testing.
- **Browsers and screens:** no automated tests of how pages look.
