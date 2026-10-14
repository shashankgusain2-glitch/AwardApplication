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
| **REST API: auth** | `tests/api/test_auth_api.py` | JWT login with role, email and name in the claims; a wrong role is rejected on the server; consistent errors; refresh rotation; logout blacklists the refresh token; register always creates an applicant; validation; login rate limit (429) | ✅ Running |
| **REST API: security** | `tests/api/test_permissions_api.py` | A judge can't read another judge's assignment or evaluation (404); an applicant can't read or change another applicant's report (404); only staff/leaders assign (403 otherwise); a judge can score only assigned reports; judges can't use /applications/; only leaders create staff/judge/leader accounts; users can't change their own role; blind judging hides identity; conflicts block assignment | ✅ Running |
| **REST API: workflows and data rules** | `tests/api/test_workflows_api.py` | Draft → submit; judging to "scored" with weighted totals; score changes need staff permission and a reason and are recorded; declined → pool; verified organisation required; leaders approve; scores outside 1–10 rejected by API and database; one judge per report per round; soft delete; audit entries can't be changed; published forms can't be changed; response format, pagination, filters, search; health; docs; seed data | ✅ Running |
| **Login and access (RBAC)** | `tests/test_authentication.py` | Passwords hashed; one login form sends each role to its own area; a role sent with the form is ignored; one error message for unknown email and wrong password; email not case-sensitive; inactive accounts blocked; session holds user id and role; safe "next" redirect; applicant sign-up (always an applicant) with validation; logout; logged-out users sent to log in; every portal page gives 403 to the other three roles; tampered session role logs out; judges open only their own scoring pages; forgot-password email and reset; seed creates every role | ✅ Running |
| **Role home pages on real data (step 3.3)** | `tests/test_role_homes.py` | Each role logs in and lands on its own home; logout ends access; every role gets 403 on the other homes; only admins open `/admin/`; applicants see only their own real applications and their verification status; judges see only their own assignments, blind awards hide the applicant, Accept and Decline work and declined reports go back to the pool, and a judge can't answer another judge's assignment (404); staff see organisations to verify and reports with no judges; leadership sees whole-event counts; a deactivated user is logged out; with the seed data every judge sees exactly their own assignments | ✅ Running |
| **REST API: core (step 3.4)** | `tests/api/test_core_api.py` | `/auth/me/`; leaders deactivate and reactivate users (tokens stop working at once; staff get 403; nobody can lock themselves out); bulk assign by exact pairs or "fill with the best judges", all or nothing; judge rows carry title, applicant, submission date, status and criteria; blind awards hide the applicant; dashboard summary counts only what each role may see; lookups; the bugs found in Postman (empty 204, broken refresh token, `?round=abc`, `true` as a score, field names in error messages) | ✅ Running |
| **Postman collection** | `postman/` (run with Newman) | 116 requests, 259 checks: every endpoint with status code and response shape, plus no token (401), wrong role (403), wrong role at login (401), another judge's report (404), invalid data (400). Passes on fresh seed data and can be run again | ✅ Passing |
| **Screens on real data (step 3.5)** | `tests/test_smoke.py`, `tests/test_web_workflow.py` | Every role's menu and every detail page opens on the seed data; screens show seed data, not samples; new applicants see empty states. Full flow through the web pages: sign up → organisation → apply and submit → staff verify and assign two judges → judges accept, save midway, submit → scored → leader approves → applicant sees Approved. Wrong role gets 403, another judge's or applicant's record 404; missing answers and a bad GSTIN show clear errors | ✅ Running |
| **Notifications and email (R4)** | `tests/test_notifications.py` | The right person is notified and emailed (verification, submit, edit request and decision, result, assignment, decline, score-change request and decision); emails go out after the change is saved; a broken email server never undoes the action; the seed sends no email; the notifications page shows only your own, opens only internal links, marks read | ✅ Running |
| **Document upload (R2)** | `tests/test_uploads.py` | Upload from the form and the API; .exe, fake PDF, empty and over-10 MB files refused with a clear message; re-upload replaces and deletes the old file; only file questions, only while editable, only the owner; download by owner, staff, leader and assigned judge; other applicants, unassigned and declined judges get 404; blind rounds give judges a neutral file name; no raw storage path in the API | ✅ Running |
| **Two awards, no code** | `tests/test_award_settings.py` | The two awards differ in settings, criteria, eligibility and form; weights add up to 100; saving settings changes the public page; one award's settings don't affect the other; bad values are rejected; reset works | ✅ Running |
| **R1 Blind judging** | `tests/rules/test_rule1_blind_judging.py` + `tests/test_award_settings.py` | On the real scoring page and the API (seed data): ✅ identifying answers, the title and uploaded file names hidden on blind awards; ✅ non-blind awards show the organisation; ✅ staff turning blind on/off changes what judges see; ✅ live presentation and site visit rounds are never blind; ✅ removing Round 2 closes its scoring page; ✅ blind is rejected when every round is in person | ✅ Running |
| **R2 Conflict of interest** | `tests/rules/test_rule2_conflict_of_interest.py` | Staff record conflicts (judges don't declare them); a conflicted judge is never suggested; staff can't force it; conflicts match merged duplicate organisations; a conflict recorded after assignment removes it and reassigns | ⏳ Planned |
| **R3 Score audit** | `tests/rules/test_rule3_score_audit.py` | Change needs a reason; records who, when, old and new value; records can't be edited or deleted; Leader can't change scores | ⏳ Planned |
| **R4 Form versions** | `tests/rules/test_rule4_form_versions.py` | Published versions can't be changed; staff editing questions publish a new version and the old one is untouched; old applications open with their own version; a removed question still shows on old applications; new applications use the new version; empty question text rejected; only staff can publish | ✅ Running |

## What the tests don't check

- **Repeated failed logins** are not limited yet (no brute-force protection), so nothing tests it.
- **Show/hide password and the loading state** are checked only by their presence on the page; the JavaScript itself was checked by hand in the browser.
- **Real email delivery** for password reset: tests read the email from the test outbox.
- **Blind judging is tested on demo data.** The tests prove the hiding logic works; they move to the real tables when judging is built.

- **Uploaded files:** we don't check that PDFs or images contain no company names (blind judging can't redact file contents automatically).
- **Real GST/PAN verification:** only the format is checked.
- **Emails:** we check an email is created, not that it is delivered.
- **Load:** no test for many applicants submitting on deadline day.
- **Security:** no penetration testing.
- **Browsers and screens:** no automated tests of how pages look.
