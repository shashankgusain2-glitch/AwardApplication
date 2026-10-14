# Postman testing checklist

Generated from `build_collection.py`, in run order. Tick **Pass/Fail** as you run each request (the Collection Runner also checks status and response shape automatically).

| # | Folder | Request | Method | Endpoint | Role | Expected | Pass/Fail |
|---|---|---|---|---|---|---|---|
| 1 | 0. Health | Health check | GET | `/api/v1/health/` | anyone | 200 | ☐ |
| 2 | 1. Auth | Login as applicant | POST | `/api/v1/auth/login/` | applicant | 200 | ☐ |
| 3 | 1. Auth | Login as staff | POST | `/api/v1/auth/login/` | staff | 200 | ☐ |
| 4 | 1. Auth | Login as judge | POST | `/api/v1/auth/login/` | judge | 200 | ☐ |
| 5 | 1. Auth | Login as judge2 | POST | `/api/v1/auth/login/` | judge2 | 200 | ☐ |
| 6 | 1. Auth | Login as leader | POST | `/api/v1/auth/login/` | leader | 200 | ☐ |
| 7 | 1. Auth | Login with the WRONG role (judge account, role=staff) → 401 | POST | `/api/v1/auth/login/` | judge | 401 | ☐ |
| 8 | 1. Auth | Login with a wrong password → 401 | POST | `/api/v1/auth/login/` | anyone | 401 | ☐ |
| 9 | 1. Auth | Login with no password → 400 | POST | `/api/v1/auth/login/` | anyone | 400 | ☐ |
| 10 | 1. Auth | Register a new applicant | POST | `/api/v1/auth/register/` | anyone | 201 | ☐ |
| 11 | 1. Auth | Register with a weak password → 400 | POST | `/api/v1/auth/register/` | anyone | 400 | ☐ |
| 12 | 1. Auth | Register with an email that exists → 400 | POST | `/api/v1/auth/register/` | anyone | 400 | ☐ |
| 13 | 1. Auth | Me (who am I) | GET | `/api/v1/auth/me/` | any logged-in | 200 | ☐ |
| 14 | 1. Auth | Me: change my name (role can't change) | PATCH | `/api/v1/auth/me/` | any logged-in | 200 | ☐ |
| 15 | 1. Auth | Me with NO token → 401 | GET | `/api/v1/auth/me/` | nobody | 401 | ☐ |
| 16 | 1. Auth | Refresh the access token | POST | `/api/v1/auth/refresh/` | any logged-in | 200 | ☐ |
| 17 | 1. Auth | Refresh with the OLD (rotated) token → 401 | POST | `/api/v1/auth/refresh/` | anyone | 401 | ☐ |
| 18 | 1. Auth | Logout with a broken refresh token → 400 | POST | `/api/v1/auth/logout/` | any logged-in | 400 | ☐ |
| 19 | 2. Users | List users (staff) | GET | `/api/v1/users/?role=judge` | staff, leader | 200 | ☐ |
| 20 | 2. Users | List users as an applicant → 403 | GET | `/api/v1/users/` | applicant | 403 | ☐ |
| 21 | 2. Users | List users with NO token → 401 | GET | `/api/v1/users/` | nobody | 401 | ☐ |
| 22 | 2. Users | Create a judge account (leader) | POST | `/api/v1/users/` | leader | 201 | ☐ |
| 23 | 2. Users | Create an account as staff → 403 | POST | `/api/v1/users/` | staff | 403 | ☐ |
| 24 | 2. Users | Create an account with a bad role → 400 | POST | `/api/v1/users/` | leader | 400 | ☐ |
| 25 | 2. Users | Get one user (leader) | GET | `/api/v1/users/{{created_user_id}}/` | staff, leader | 200 | ☐ |
| 26 | 2. Users | Update a user's name (leader) | PATCH | `/api/v1/users/{{created_user_id}}/` | leader | 200 | ☐ |
| 27 | 2. Users | Deactivate a user (leader) | POST | `/api/v1/users/{{created_user_id}}/deactivate/` | leader | 200 | ☐ |
| 28 | 2. Users | Reactivate a user (leader) | POST | `/api/v1/users/{{created_user_id}}/activate/` | leader | 200 | ☐ |
| 29 | 2. Users | Deactivate a user as staff → 403 | POST | `/api/v1/users/{{created_user_id}}/deactivate/` | staff | 403 | ☐ |
| 30 | 2. Users | Leader deactivates themselves → 400 | POST | `/api/v1/users/{{leader_user_id}}/deactivate/` | leader | 400 | ☐ |
| 31 | 2. Users | My own account (/users/me/) | GET | `/api/v1/users/me/` | any logged-in | 200 | ☐ |
| 32 | 3. Profiles | My organisation profile (applicant) | GET | `/api/v1/profiles/mine/` | applicant | 200 | ☐ |
| 33 | 3. Profiles | Update my profile with a bad GSTIN → 400 | PATCH | `/api/v1/profiles/mine/` | applicant | 400 | ☐ |
| 34 | 3. Profiles | Update my profile with a GSTIN another organisation uses → 400 | PATCH | `/api/v1/profiles/mine/` | applicant | 400 | ☐ |
| 35 | 3. Profiles | Update my profile (applicant) | PATCH | `/api/v1/profiles/mine/` | applicant | 200 | ☐ |
| 36 | 3. Profiles | My profile as a judge → 403 | GET | `/api/v1/profiles/mine/` | judge | 403 | ☐ |
| 37 | 3. Profiles | List organisations waiting (staff) | GET | `/api/v1/profiles/?verification_status=pending` | staff, leader | 200 | ☐ |
| 38 | 3. Profiles | Verify with no body → 400 | POST | `/api/v1/profiles/{{new_profile_id}}/verify/` | staff, leader | 400 | ☐ |
| 39 | 3. Profiles | Verify the new organisation (staff) | POST | `/api/v1/profiles/{{new_profile_id}}/verify/` | staff, leader | 200 | ☐ |
| 40 | 4. Awards | List awards (public) | GET | `/api/v1/awards/` | anyone | 200 | ☐ |
| 41 | 4. Awards | One award with its form and criteria | GET | `/api/v1/awards/kaizen/` | anyone | 200 | ☐ |
| 42 | 4. Awards | Unknown award → 404 | GET | `/api/v1/awards/no-such-award/` | anyone | 404 | ☐ |
| 43 | 5. Applications | Create an application (applicant) | POST | `/api/v1/applications/` | applicant | 201 | ☐ |
| 44 | 5. Applications | Create a second one for the same award → 400 | POST | `/api/v1/applications/` | applicant | 400 | ☐ |
| 45 | 5. Applications | Create with no award → 400 | POST | `/api/v1/applications/` | applicant | 400 | ☐ |
| 46 | 5. Applications | Create as staff → 403 | POST | `/api/v1/applications/` | staff | 403 | ☐ |
| 47 | 5. Applications | Submit before answering → 400 | POST | `/api/v1/applications/{{application_id}}/submit/` | applicant | 400 | ☐ |
| 48 | 5. Applications | Answer an unknown question → 400 | PATCH | `/api/v1/applications/{{application_id}}/` | applicant | 400 | ☐ |
| 49 | 5. Applications | Save answers (applicant) | PATCH | `/api/v1/applications/{{application_id}}/` | applicant | 200 | ☐ |
| 50 | 5. Applications | Submit (applicant) | POST | `/api/v1/applications/{{application_id}}/submit/` | applicant | 200 | ☐ |
| 51 | 5. Applications | Edit after submitting → 400 | PATCH | `/api/v1/applications/{{application_id}}/` | applicant | 400 | ☐ |
| 52 | 5. Applications | Draft for a second award, then delete it | POST | `/api/v1/applications/` | applicant | 201 | ☐ |
| 53 | 5. Applications | Delete my draft (applicant) | DELETE | `/api/v1/applications/{{draft_id}}/` | applicant | 204 | ☐ |
| 54 | 5. Applications | My applications (applicant: own only) | GET | `/api/v1/applications/` | applicant | 200 | ☐ |
| 55 | 5. Applications | Open ANOTHER applicant's application → 404 | GET | `/api/v1/applications/{{other_application_id}}/` | applicant | 404 | ☐ |
| 56 | 5. Applications | All applications (staff) | GET | `/api/v1/applications/?status=submitted&search=Postman` | staff, leader | 200 | ☐ |
| 57 | 5. Applications | One application (leader) | GET | `/api/v1/applications/{{application_id}}/` | staff, leader | 200 | ☐ |
| 58 | 5. Applications | Applications as a judge → 403 | GET | `/api/v1/applications/` | judge | 403 | ☐ |
| 59 | 5. Applications | Applications with NO token → 401 | GET | `/api/v1/applications/` | nobody | 401 | ☐ |
| 60 | 5. Applications | Bad status filter → 400 | GET | `/api/v1/applications/?status=bogus` | staff, leader | 400 | ☐ |
| 61 | 5. Applications | Judges who may take it (staff) | GET | `/api/v1/applications/{{application_id}}/eligible-judges/` | staff, leader | 200 | ☐ |
| 62 | 5. Applications | Eligible judges with a bad round → 400 | GET | `/api/v1/applications/{{application_id}}/eligible-judges/?round=abc` | staff, leader | 400 | ☐ |
| 63 | 6. Assignments | Assign a judge (staff) | POST | `/api/v1/assignments/` | staff, leader | 201 | ☐ |
| 64 | 6. Assignments | Assign the same judge again → 400 | POST | `/api/v1/assignments/` | staff, leader | 400 | ☐ |
| 65 | 6. Assignments | Assign with a missing report → 400 | POST | `/api/v1/assignments/` | staff, leader | 400 | ☐ |
| 66 | 6. Assignments | Assign as a judge → 403 | POST | `/api/v1/assignments/` | judge | 403 | ☐ |
| 67 | 6. Assignments | Bulk assign exact pairs (staff) | POST | `/api/v1/assignments/bulk/` | staff, leader | 201 | ☐ |
| 68 | 6. Assignments | Bulk assign with nothing to do → 400 | POST | `/api/v1/assignments/bulk/` | staff, leader | 400 | ☐ |
| 69 | 6. Assignments | Bulk assign as an applicant → 403 | POST | `/api/v1/assignments/bulk/` | applicant | 403 | ☐ |
| 70 | 6. Assignments | Reassign to another judge (staff) | POST | `/api/v1/assignments/{{third_assignment_id}}/reassign/` | staff, leader | 201 | ☐ |
| 71 | 6. Assignments | Reassign to a judge already on it → 400 | POST | `/api/v1/assignments/{{assignment_id}}/reassign/` | staff, leader | 400 | ☐ |
| 72 | 6. Assignments | All assignments for the report (staff) | GET | `/api/v1/assignments/?report={{application_id}}` | staff, leader | 200 | ☐ |
| 73 | 6. Assignments | My assigned reports (judge) | GET | `/api/v1/judge/my-assignments/` | judge | 200 | ☐ |
| 74 | 6. Assignments | My assignments as staff → 403 | GET | `/api/v1/judge/my-assignments/` | staff | 403 | ☐ |
| 75 | 6. Assignments | Open ANOTHER judge's assignment → 404 | GET | `/api/v1/assignments/{{judge2_assignment_id}}/` | judge | 404 | ☐ |
| 76 | 6. Assignments | Accept ANOTHER judge's assignment → 404 | POST | `/api/v1/assignments/{{judge2_assignment_id}}/accept/` | judge | 404 | ☐ |
| 77 | 6. Assignments | Accept my assignment (judge) | POST | `/api/v1/assignments/{{assignment_id}}/accept/` | judge | 200 | ☐ |
| 78 | 6. Assignments | One assignment with the report (judge) | GET | `/api/v1/assignments/{{assignment_id}}/` | judge | 200 | ☐ |
| 79 | 6. Assignments | Decline after accepting → 400 | POST | `/api/v1/assignments/{{assignment_id}}/decline/` | judge | 400 | ☐ |
| 80 | 6. Assignments | Accept (second judge) | POST | `/api/v1/assignments/{{judge2_assignment_id}}/accept/` | judge | 200 | ☐ |
| 81 | 7. Evaluations | Save scores midway (judge) | POST | `/api/v1/evaluations/` | judge | 201 | ☐ |
| 82 | 7. Evaluations | Score of 11 → 400 | POST | `/api/v1/evaluations/` | judge | 400 | ☐ |
| 83 | 7. Evaluations | Score true/false → 400 | POST | `/api/v1/evaluations/` | judge | 400 | ☐ |
| 84 | 7. Evaluations | Score ANOTHER judge's assignment → 404 | POST | `/api/v1/evaluations/` | judge | 404 | ☐ |
| 85 | 7. Evaluations | Evaluate as staff → 403 | POST | `/api/v1/evaluations/` | staff | 403 | ☐ |
| 86 | 7. Evaluations | Submit every score + feedback (judge) | PATCH | `/api/v1/evaluations/{{evaluation_id}}/` | judge | 200 | ☐ |
| 87 | 7. Evaluations | Change a submitted evaluation directly → 400 | PATCH | `/api/v1/evaluations/{{evaluation_id}}/` | judge | 400 | ☐ |
| 88 | 7. Evaluations | Second judge submits | POST | `/api/v1/evaluations/` | judge | 201 | ☐ |
| 89 | 7. Evaluations | The report is now scored (staff) | GET | `/api/v1/applications/{{application_id}}/` | staff, leader | 200 | ☐ |
| 90 | 7. Evaluations | All evaluations of the report (staff) | GET | `/api/v1/evaluations/?assignment={{assignment_id}}` | staff, leader | 200 | ☐ |
| 91 | 7. Evaluations | Evaluations as an applicant → 403 | GET | `/api/v1/evaluations/` | applicant | 403 | ☐ |
| 92 | 7. Evaluations | Ask to change a score (judge) | POST | `/api/v1/evaluations/{{evaluation_id}}/request-change/` | judge | 201 | ☐ |
| 93 | 7. Evaluations | Change scores before anyone allows it → 400 | POST | `/api/v1/evaluations/{{evaluation_id}}/change-scores/` | judge | 400 | ☐ |
| 94 | 7. Evaluations | Score-change requests (staff) | GET | `/api/v1/score-change-requests/?status=requested` | staff, leader | 200 | ☐ |
| 95 | 7. Evaluations | Leader confirms before staff check it → 400 | POST | `/api/v1/score-change-requests/{{change_request_id}}/decide/` | staff first, then leader | 400 | ☐ |
| 96 | 7. Evaluations | Check the change and pass it to leadership (staff) | POST | `/api/v1/score-change-requests/{{change_request_id}}/decide/` | staff first, then leader | 200 | ☐ |
| 97 | 7. Evaluations | Change scores with only staff's check → 400 | POST | `/api/v1/evaluations/{{evaluation_id}}/change-scores/` | judge | 400 | ☐ |
| 98 | 7. Evaluations | Confirm the change (leader) | POST | `/api/v1/score-change-requests/{{change_request_id}}/decide/` | staff first, then leader | 200 | ☐ |
| 99 | 7. Evaluations | Change a score with a reason (judge) | POST | `/api/v1/evaluations/{{evaluation_id}}/change-scores/` | judge | 200 | ☐ |
| 100 | 8. Decisions | Staff approve a result → 400 (leaders only) | POST | `/api/v1/applications/{{application_id}}/change-status/` | staff | 400 | ☐ |
| 101 | 8. Decisions | Approve the result (leader) | POST | `/api/v1/applications/{{application_id}}/change-status/` | leader | 200 | ☐ |
| 102 | 8. Decisions | Set an unknown status → 400 | POST | `/api/v1/applications/{{application_id}}/change-status/` | leader | 400 | ☐ |
| 103 | 8. Decisions | Ask to edit after judging → 400 (only before judging starts) | POST | `/api/v1/applications/{{application_id}}/request-edit/` | applicant | 400 | ☐ |
| 104 | 8. Decisions | Ask for a re-evaluation of the result (applicant) | POST | `/api/v1/applications/{{application_id}}/request-reevaluation/` | applicant | 200 | ☐ |
| 105 | 8. Decisions | Leader decides before staff check it → 400 | POST | `/api/v1/applications/{{application_id}}/decide-reevaluation/` | staff first, then leader | 400 | ☐ |
| 106 | 8. Decisions | Refuse the re-evaluation (staff) | POST | `/api/v1/applications/{{application_id}}/decide-reevaluation/` | staff first, then leader | 200 | ☐ |
| 107 | 9. Conflicts | Record a conflict (staff) | POST | `/api/v1/conflicts/` | staff, leader | 201 | ☐ |
| 108 | 9. Conflicts | Conflicted judge is no longer offered | GET | `/api/v1/applications/{{application_id}}/eligible-judges/` | staff, leader | 200 | ☐ |
| 109 | 9. Conflicts | List conflicts (staff) | GET | `/api/v1/conflicts/` | staff, leader | 200 | ☐ |
| 110 | 9. Conflicts | Record a conflict as a judge → 403 | POST | `/api/v1/conflicts/` | judge | 403 | ☐ |
| 111 | 10. Dashboards | Summary (applicant: own reports) | GET | `/api/v1/dashboard/summary/` | applicant | 200 | ☐ |
| 112 | 10. Dashboards | Summary (judge: own assignments) | GET | `/api/v1/dashboard/summary/` | judge | 200 | ☐ |
| 113 | 10. Dashboards | Summary (staff: whole event) | GET | `/api/v1/dashboard/summary/` | staff | 200 | ☐ |
| 114 | 10. Dashboards | Summary (leader: whole event) | GET | `/api/v1/dashboard/summary/` | leader | 200 | ☐ |
| 115 | 10. Dashboards | Summary with NO token → 401 | GET | `/api/v1/dashboard/summary/` | nobody | 401 | ☐ |
| 116 | 10. Dashboards | Lookups (codes and labels) | GET | `/api/v1/lookups/` | any logged-in | 200 | ☐ |
| 117 | 10. Dashboards | My notifications (judge) | GET | `/api/v1/notifications/` | any logged-in | 200 | ☐ |
| 118 | 10. Dashboards | Mark a notification read (judge) | POST | `/api/v1/notifications/{{notification_id}}/read/` | any logged-in | 200 | ☐ |
| 119 | 10. Dashboards | Mark ANOTHER user's notification → 404 | POST | `/api/v1/notifications/{{notification_id}}/read/` | judge | 404 | ☐ |
| 120 | 11. Logout | Logout (new applicant) | POST | `/api/v1/auth/logout/` | any logged-in | 200 | ☐ |
| 121 | 11. Logout | Refresh after logout → 401 | POST | `/api/v1/auth/refresh/` | anyone | 401 | ☐ |
