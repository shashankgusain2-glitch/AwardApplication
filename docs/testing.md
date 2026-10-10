# Testing: what our tests check, and what they don't

> **Status:** test list written before the code. Tests marked *planned* are skipped until the feature is built.

Run all tests:

```bash
pytest
```

## What the tests check

| Rule / area | Test file | Checks | Status |
|---|---|---|---|
| App starts | `tests/test_smoke.py` | Home page loads | ✅ Running |
| **R1 Blind judging** | `tests/rules/test_rule1_blind_judging.py` | Identifying answers hidden from judges; organisation not in judge data; non-blind awards show it; live Round 2 is not blind | ⏳ Planned |
| **R2 Conflict of interest** | `tests/rules/test_rule2_conflict_of_interest.py` | Conflicted judge never suggested; staff can't force it; conflicts match merged duplicate organisations; late conflict removes and reassigns | ⏳ Planned |
| **R3 Score audit** | `tests/rules/test_rule3_score_audit.py` | Change needs a reason; records who, when, old and new value; records can't be edited or deleted; Leader can't change scores | ⏳ Planned |
| **R4 Form versions** | `tests/rules/test_rule4_form_versions.py` | Published form can't be edited; edits create a new version; old applications open with their own version; removed questions still show on old applications | ⏳ Planned |

## What the tests don't check

- **Uploaded files:** we don't check that PDFs or images contain no company names (blind judging can't redact file contents automatically).
- **Real GST/PAN verification:** only the format is checked.
- **Emails:** we check an email is created, not that it is delivered.
- **Load:** no test for many applicants submitting on deadline day.
- **Security:** no penetration testing.
- **Browsers and screens:** no automated tests of how pages look.
