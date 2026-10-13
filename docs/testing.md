# Testing: what our tests check, and what they don't

> **Updated 13 Oct 2026**: all workflows from the 12 Oct meeting. 81 tests pass, 4 planned.

Run all tests: `pytest` (or `docker compose exec web pytest`).

## What the tests check

| Area | File | Checks |
|---|---|---|
| Pages and access | `test_smoke.py` | Home shows the 2 events; applicant, staff, judge and leadership pages need the right login |
| Applicant | `test_applicant_workflow.py` | Email code (right, wrong, too many tries, expired); GSTIN/PAN format; a GSTIN registered once; 2 events with their own forms; one report per event; save midway; submit needs required answers; submitted report locked; can't open others' reports; staff confirm → pool; staff reject → applicant told; edit only after staff allow; resubmitting keeps its place |
| Judge | `test_judge_workflow.py` | Email link logs in and opens the judging tab; tampered link refused; judge sees only their reports; accept → being judged; decline → back to pool and not offered again; must accept before opening; can't open others' assignments; partial grading saved; submit needs every part; judged when all judges submit (weighted average checked); graded report locked; grade page in every state |
| Score changes | `test_judge_workflow.py` | No change without staff permission; ask → staff allow → change with reason → recorded (who, old, new, why); permission is used up; refused request keeps scores |
| Round 2 | `test_judge_workflow.py` | Shortlist → meeting with link and a group of judges → judges grade → "Round 2 graded" with its own average |
| Staff | `test_staff_and_leadership.py` | Auto-assign by priority; full judges skipped; equal priority goes to lighter load; judges per report set by staff; add judge with priority and events; form change makes a new version and old reports keep theirs; actions logged; every staff page and every report stage loads; non-staff blocked |
| Leadership | `test_staff_and_leadership.py` | Dashboard counts pool, rejected and under evaluation; only leadership can open it |
| **R2 Conflicts** | `rules/test_rule2_conflict_of_interest.py` | Conflicted judge never suggested, never auto-assigned, can't be forced, can't be in Round 2, conflict covers every report of that organisation |
| **R3 Score audit** | `rules/test_rule3_score_audit.py` | Change needs permission and a reason; records who, when, old, new, why; records can't be edited or deleted |
| **R4 Form versions** | `rules/test_rule4_form_versions.py` | New reports use the newest form; old reports keep and show their own questions and answers |
| R1 Blind judging | `rules/test_rule1_blind_judging.py` | ⏳ Planned: not part of the 12 Oct workflows |

## What the tests don't check

- **Real email delivery:** emails are printed, not sent.
- **Real GSTIN/PAN verification:** only the format is checked.
- **The Round 2 meeting itself:** we store the link; the video call happens outside the system.
- **How pages look** on different screens or browsers.
- **Load:** many applicants submitting on deadline day.
- **Security testing** beyond access rules and the signed judge login link.
