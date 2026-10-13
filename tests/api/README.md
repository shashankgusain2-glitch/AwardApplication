# tests/api/

**Tests for the REST API** (`/api/v1/`).

| File | What it checks |
|---|---|
| `conftest.py` | Fixtures: an API client, a logged-in client for any user, and a small "world" (award, staff, two judges, two assigned reports) |
| `test_auth_api.py` | Login gives JWTs with the role in the claims; a wrong role is rejected; refresh; logout blacklists; register always makes an applicant; validation; rate limiting |
| `test_permissions_api.py` | A judge can't read another judge's assignment or evaluation; an applicant can't read or change another's report; only staff/leaders assign; judges score only their own; leaders create accounts; blind judging hides identity; conflicts block assignment |
| `test_workflows_api.py` | Draft → submit; full judging to "scored"; score changes need permission and a reason; declined → back to pool; verified organisation required; leader approves; database checks; response format, pagination, filters; health; docs; seed data |
