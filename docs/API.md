# REST API (v1)

- **Base URL:** `http://localhost:8000/api/v1/`
- **Interactive docs (Swagger UI):** http://localhost:8000/api/docs/ · **OpenAPI schema:** `/api/schema/`
- **Auth:** JWT. Send `Authorization: Bearer <access token>`. Access tokens last 30 minutes, refresh tokens 1 day (rotated on refresh; old ones are blacklisted).

## Response format (every endpoint)

```json
{ "success": true,  "data": { ... },  "message": "", "errors": null }
{ "success": false, "data": null,     "message": "Only staff, award managers or leaders can assign judges.", "errors": null }
{ "success": false, "data": null,     "message": "This field is required.", "errors": { "report": ["This field is required."] } }
```

Lists are paginated inside `data`: `{ "count", "next", "previous", "results": [...] }`. Use `?page=2&page_size=50` (max 100).
Most lists also accept **filters** (e.g. `?status=submitted&award=kaizen`), **search** (`?search=...`) and **ordering** (`?ordering=-created_at`).

## Endpoints and who can use them

**Award managers** can use every endpoint marked *staff*. **Staff and award managers only ever get data for the awards they are on** (applications, assignments, evaluations, score-change requests, organisation profiles, files and the dashboard summary); another award's record returns 404. Leaders see every award.

| Endpoint | Method | Who | What |
|---|---|---|---|
| `/auth/login/` | POST | anyone | `{email, password, role?}` → `{access, refresh, user}`. Token claims include `role`, `email`, `name`. If `role` is sent and doesn't match the account, login is refused. Limited to 10/minute |
| `/auth/refresh/` | POST | anyone | `{refresh}` → new `{access, refresh}` |
| `/auth/logout/` | POST | logged in | `{refresh}`: blacklists the refresh token |
| `/auth/register/` | POST | anyone | Applicant sign-up `{email, name, password, organisation_name?}`. Always creates an **applicant** |
| `/auth/me/` | GET / PATCH | everyone | Who am I (`id, email, name, role`). PATCH changes only `name` |
| `/users/` | GET | staff, leader | List users (`?role=judge`, `?search=`) |
| `/users/` | POST | **leader** | Create staff, judge or leader accounts (`{email, name, role, password?, expertise?, priority?, max_open_assignments?}`). Without a password, the person is emailed a set-your-password link |
| `/users/{id}/` | GET / PATCH | staff, leader / **leader** | Read / change (role, active, name). A leader can't change their own role or deactivate themselves |
| `/users/{id}/deactivate/` · `/activate/` | POST | **leader** | Turn an account off or on (nothing is deleted). Deactivating blacklists the user's refresh tokens at once |
| `/users/me/` | GET / PATCH | everyone | Your own account (only `name` can change) |
| `/profiles/mine/` | GET / PUT / PATCH | applicant | Your organisation profile (GSTIN and PAN format-checked) |
| `/profiles/` · `/profiles/{id}/verify/` | GET · POST | staff, leader | List organisations; verify or reject `{approve, note}` |
| `/awards/` · `/awards/{slug}/` | GET | anyone | Awards with rounds, criteria and the current form |
| `/applications/` | GET / POST | applicant (own), staff & award manager (their awards), leader (all) | Applicants create `{award: slug, title}` |
| `/applications/{id}/` | GET / PATCH / DELETE | applicant (own) | Save answers `{content: {...}}` (partial is fine); delete drafts only |
| `/applications/{id}/submit/` | POST | applicant (own) | Checks required answers, then locks it |
| `/applications/{id}/request-edit/` | POST | applicant (own) | `{reason}`: ask staff to allow changes |
| `/applications/{id}/decide-edit/` | POST | staff, leader | `{allow}` |
| `/applications/{id}/change-status/` | POST | staff, leader | `{status: rejected\|approved, note}` (approve: leader only) |
| `/applications/{id}/attachments/` | POST (multipart) | applicant (own, while editable) | `{question_key, file}`: PDF/JPG/PNG up to 10 MB on a file question; replaces an earlier file. Returns `download_url` |
| `/attachments/{id}/download/` | GET | owner, staff, leader, judges assigned to the report | The file. Blind rounds give judges a neutral file name; anyone else gets 404 |
| `/applications/{id}/eligible-judges/` | GET | staff, leader | Judges who may take it: panel, no conflict, under limit, best first |
| `/assignments/` | GET | judge (own only), staff, leader | |
| `/assignments/` | POST | **staff, leader** | `{report, judge, round?}`: checks verified organisation, role, conflict, workload |
| `/assignments/bulk/` | POST | staff, leader | `{items: [{report, judge}], round?}` assigns exact pairs, or `{reports: [ids]}` fills each report with the best eligible judges. All or nothing: one broken rule and nothing is saved (the 400 names the item) |
| `/assignments/{id}/reassign/` | POST | staff, leader | `{judge}` |
| `/assignments/{id}/accept/` · `/decline/` | POST | judge (own) | Declined reports go back to the pool |
| `/judge/my-assignments/` | GET | judge | Your reports only (judge taken from your token): title, applicant name, submission date, report status, assignment status and the criteria to score. **Blind awards hide identity** in desk rounds |
| `/conflicts/` | GET / POST | staff, leader | Record a conflict `{judge, applicant_profile, reason}`; open assignments are withdrawn |
| `/evaluations/` | GET | judge (own), staff, leader | |
| `/evaluations/` | POST | judge (own assignments only) | `{assignment, scores: {criterion_key: 1-10}, feedback?, submit?}`. `submit=false` saves midway |
| `/evaluations/{id}/` | PATCH | judge (own) | More scores / submit |
| `/evaluations/{id}/request-change/` | POST | judge (own) | `{reason}`: ask staff to change a submitted evaluation |
| `/evaluations/{id}/change-scores/` | POST | judge (own) | `{scores, reason}`: needs an approved request; every change is recorded |
| `/score-change-requests/` · `/{id}/decide/` | GET · POST | staff, leader | `{approve}` |
| `/notifications/` · `/{id}/read/` | GET · POST | everyone (own) | |
| `/dashboard/summary/` | GET | everyone | Counts by status for **your** role: applicants their own reports, judges their own assignments, staff and award managers their own awards, leaders the whole event, plus per-award progress |
| `/lookups/` | GET | everyone | Codes and labels for drop-downs and badges (roles, statuses, round kinds, score range) |
| `/health/` | GET | anyone | `{status, database}` |

**Security rules:** a user's role always comes from their account, never from the request. Every list is limited in `get_queryset()`, so another user's record returns **404** (not someone else's data). A wrong role returns **403**.

## Postman

A ready-to-import collection (116 requests in 12 folders, with tests) and a testing checklist are in [postman/](../postman/README.md).

## Sample requests (curl)

The demo password for all seeded accounts is `DEMO_PASSWORD` in `.env.example`.

```bash
# Log in as a judge (role is optional; if sent it must match)
curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "kapoor@judges.example", "password": "<DEMO_PASSWORD>", "role": "judge"}'

# Use the access token
TOKEN=<access token from the response>
curl -s http://localhost:8000/api/v1/judge/my-assignments/ -H "Authorization: Bearer $TOKEN"

# Accept an assignment, save scores midway, then submit
curl -s -X POST http://localhost:8000/api/v1/assignments/15/accept/ -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:8000/api/v1/evaluations/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assignment": 15, "scores": {"leadership-and-strategy": 8}, "submit": false}'

# Staff: assign a judge to a report
curl -s -X POST http://localhost:8000/api/v1/assignments/ -H "Authorization: Bearer $STAFF_TOKEN" \
  -H "Content-Type: application/json" -d '{"report": 9, "judge": 7}'

# Applicant: sign up, then create and submit an application
curl -s -X POST http://localhost:8000/api/v1/auth/register/ -H "Content-Type: application/json" \
  -d '{"email": "new@company.example", "name": "New Applicant", "password": "A-strong-pass-123", "organisation_name": "New Co"}'
```

In Swagger UI: log in with `/auth/login/`, copy `access`, click **Authorize**, paste it, then try any endpoint.
