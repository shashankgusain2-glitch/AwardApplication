"""
Builds the Postman collection and environment for the Awards Platform API.

    python postman/build_collection.py

Writes:
    postman/Awards-Platform.postman_collection.json
    postman/Awards-Platform.postman_environment.json
    postman/CHECKLIST.md        (endpoint | method | role | expected | pass/fail)

Why a script: every request gets the same checks (status code and the
{success, data, message, errors} shape), and the checklist always matches
the collection. Edit the REQUESTS list below, then run the script again.

Run order matters: the collection is one story on the seed data. A new
applicant signs up, applies, gets verified, is assigned two judges, both
judges score, the award manager decides. Negative tests sit next to the happy path.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "Awards Platform API (v1)"

# Role → token variable. None means "send no token".
TOKEN = {"applicant": "applicant_token", "new_applicant": "new_applicant_token", "staff": "staff_token",
         "judge": "judge_token", "judge2": "judge2_token", "leader": "leader_token", "manager": "manager_token",
         None: None}

# --- Reusable test-script snippets (JavaScript, run by Postman after each request) ---

def save(var, expr):
    return f'pm.collectionVariables.set("{var}", {expr});'


def login(role_key, email_var, extra=""):
    """Login request for one demo account; saves its access + refresh tokens and user id."""
    return {
        "folder": "1. Auth", "name": f"Login as {role_key}", "method": "POST", "path": "auth/login/",
        "role": None, "expect": 200, "who": role_key,
        "body": {"email": f"{{{{{email_var}}}}}", "password": "{{demo_password}}", "role": ROLE_OF[role_key]},
        "tests": "\n".join([
            "const d = pm.response.json().data;",
            'pm.test("returns access + refresh tokens and the user", () => {',
            "  pm.expect(d.access).to.be.a('string'); pm.expect(d.refresh).to.be.a('string');",
            f"  pm.expect(d.user.role).to.eql('{ROLE_OF[role_key]}');",
            "});",
            save(TOKEN[role_key], "d.access"),
            save(f"{role_key}_refresh", "d.refresh"),
            save(f"{role_key}_user_id", "d.user.id"),
            extra,
        ]),
    }


ROLE_OF = {"applicant": "applicant", "staff": "staff", "judge": "judge", "judge2": "judge", "leader": "leader",
           "manager": "manager"}

# Each request: folder, name, method, path (after {{base_url}}/), role (whose token), expect (status),
# who (role shown in the checklist), body (dict / None), tests (extra JS), pre (pre-request JS).
REQUESTS = [
    # ------------------------------------------------------------------ 0. Health
    {"folder": "0. Health", "name": "Health check", "method": "GET", "path": "health/", "role": None,
     "expect": 200, "who": "anyone",
     "tests": 'pm.test("database ok", () => pm.expect(pm.response.json().data.database).to.eql("ok"));'},

    # ------------------------------------------------------------------ 1. Auth
    login("applicant", "applicant_email"),
    login("staff", "staff_email"),
    login("judge", "judge_email"),
    login("judge2", "judge2_email"),
    login("leader", "leader_email"),
    login("manager", "manager_email"),
    {"folder": "1. Auth", "name": "Login with the WRONG role (judge account, role=staff) → 401",
     "method": "POST", "path": "auth/login/", "role": None, "expect": 401, "who": "judge",
     "body": {"email": "{{judge_email}}", "password": "{{demo_password}}", "role": "staff"}},
    {"folder": "1. Auth", "name": "Login with a wrong password → 401", "method": "POST", "path": "auth/login/",
     "role": None, "expect": 401, "who": "anyone",
     "body": {"email": "{{applicant_email}}", "password": "not-the-password"}},
    {"folder": "1. Auth", "name": "Login with no password → 400", "method": "POST", "path": "auth/login/",
     "role": None, "expect": 400, "who": "anyone", "body": {"email": "{{applicant_email}}"}},
    {"folder": "1. Auth", "name": "Register a new applicant", "method": "POST", "path": "auth/register/",
     "role": None, "expect": 201, "who": "anyone",
     "pre": "\n".join([
         "const n = Date.now();",
         save("new_applicant_email", "`postman.${n}@example.com`"),
         save("new_gstin", "'27PMANC' + String(n % 10000).padStart(4, '0') + 'F1Z5'"),
         save("new_password", "'Zq9-' + Math.random().toString(36).slice(2, 12) + '-Wx'"),
     ]),
     "body": {"email": "{{new_applicant_email}}", "name": "Postman Tester", "password": "{{new_password}}",
              "organisation_name": "Postman Test Industries {{new_gstin}}", "role": "leader"},
     "tests": "\n".join([
         "const d = pm.response.json().data;",
         'pm.test("always an applicant, even if another role is sent", () => pm.expect(d.user.role).to.eql("applicant"));',
         save("new_applicant_token", "d.access"), save("new_applicant_refresh", "d.refresh"),
         save("new_applicant_user_id", "d.user.id"),
     ])},
    {"folder": "1. Auth", "name": "Register with a weak password → 400", "method": "POST", "path": "auth/register/",
     "role": None, "expect": 400, "who": "anyone",
     "body": {"email": "weak.{{$timestamp}}@example.com", "name": "Weak", "password": "123"}},
    {"folder": "1. Auth", "name": "Register with an email that exists → 400", "method": "POST",
     "path": "auth/register/", "role": None, "expect": 400, "who": "anyone",
     "body": {"email": "{{applicant_email}}", "name": "Copy", "password": "Strong-pass-123"}},
    {"folder": "1. Auth", "name": "Me (who am I)", "method": "GET", "path": "auth/me/", "role": "new_applicant",
     "expect": 200, "who": "any logged-in",
     "tests": 'pm.test("it is me", () => pm.expect(pm.response.json().data.email).to.eql(pm.variables.get("new_applicant_email")));'},
    {"folder": "1. Auth", "name": "Me: change my name (role can't change)", "method": "PATCH", "path": "auth/me/",
     "role": "new_applicant", "expect": 200, "who": "any logged-in",
     "body": {"name": "Postman Tester (renamed)", "role": "leader"},
     "tests": 'pm.test("role unchanged", () => pm.expect(pm.response.json().data.role).to.eql("applicant"));'},
    {"folder": "1. Auth", "name": "Me with NO token → 401", "method": "GET", "path": "auth/me/", "role": None,
     "expect": 401, "who": "nobody"},
    {"folder": "1. Auth", "name": "Refresh the access token", "method": "POST", "path": "auth/refresh/",
     "role": None, "expect": 200, "who": "any logged-in", "body": {"refresh": "{{new_applicant_refresh}}"},
     "tests": "\n".join(["const d = pm.response.json().data;",
                         save("old_refresh", 'pm.variables.get("new_applicant_refresh")'),
                         save("new_applicant_token", "d.access"), save("new_applicant_refresh", "d.refresh")])},
    {"folder": "1. Auth", "name": "Refresh with the OLD (rotated) token → 401", "method": "POST",
     "path": "auth/refresh/", "role": None, "expect": 401, "who": "anyone", "body": {"refresh": "{{old_refresh}}"}},
    {"folder": "1. Auth", "name": "Logout with a broken refresh token → 400", "method": "POST", "path": "auth/logout/",
     "role": "new_applicant", "expect": 400, "who": "any logged-in", "body": {"refresh": "not-a-token"}},

    # ------------------------------------------------------------------ 2. Users
    {"folder": "2. Users", "name": "List users (staff)", "method": "GET", "path": "users/?role=judge",
     "role": "staff", "expect": 200, "who": "staff, leader",
     "tests": "\n".join([
         "const rows = pm.response.json().data.results;",
         'pm.test("paginated list of judges", () => rows.forEach(u => pm.expect(u.role).to.eql("judge")));',
         save("third_judge_id", 'rows.find(u => u.email === "iyer@judges.example").id'),
     ])},
    {"folder": "2. Users", "name": "List users as an applicant → 403", "method": "GET", "path": "users/",
     "role": "applicant", "expect": 403, "who": "applicant"},
    {"folder": "2. Users", "name": "List users with NO token → 401", "method": "GET", "path": "users/", "role": None,
     "expect": 401, "who": "nobody"},
    {"folder": "2. Users", "name": "Create a judge account (leader)", "method": "POST", "path": "users/",
     "role": "leader", "expect": 201, "who": "leader",
     "body": {"email": "judge.{{$timestamp}}@judges.example", "name": "Postman Judge", "role": "judge",
              "expertise": "Testing", "priority": 9},
     "tests": save("created_user_id", "pm.response.json().data.id")},
    {"folder": "2. Users", "name": "Create an account as staff → 403", "method": "POST", "path": "users/",
     "role": "staff", "expect": 403, "who": "staff",
     "body": {"email": "x.{{$timestamp}}@example.com", "name": "X", "role": "leader"}},
    {"folder": "2. Users", "name": "Create an account with a bad role → 400", "method": "POST", "path": "users/",
     "role": "leader", "expect": 400, "who": "leader",
     "body": {"email": "y.{{$timestamp}}@example.com", "name": "Y", "role": "superhero"}},
    {"folder": "2. Users", "name": "Get one user (leader)", "method": "GET", "path": "users/{{created_user_id}}/",
     "role": "leader", "expect": 200, "who": "staff, leader"},
    {"folder": "2. Users", "name": "Update a user's name (leader)", "method": "PATCH",
     "path": "users/{{created_user_id}}/", "role": "leader", "expect": 200, "who": "leader",
     "body": {"name": "Postman Judge (renamed)"}},
    {"folder": "2. Users", "name": "Deactivate a user (leader)", "method": "POST",
     "path": "users/{{created_user_id}}/deactivate/", "role": "leader", "expect": 200, "who": "leader",
     "tests": 'pm.test("inactive", () => pm.expect(pm.response.json().data.is_active).to.eql(false));'},
    {"folder": "2. Users", "name": "Reactivate a user (leader)", "method": "POST",
     "path": "users/{{created_user_id}}/activate/", "role": "leader", "expect": 200, "who": "leader"},
    {"folder": "2. Users", "name": "Deactivate a user as staff → 403", "method": "POST",
     "path": "users/{{created_user_id}}/deactivate/", "role": "staff", "expect": 403, "who": "staff"},
    {"folder": "2. Users", "name": "Leader deactivates themselves → 400", "method": "POST",
     "path": "users/{{leader_user_id}}/deactivate/", "role": "leader", "expect": 400, "who": "leader"},
    {"folder": "2. Users", "name": "My own account (/users/me/)", "method": "GET", "path": "users/me/",
     "role": "judge", "expect": 200, "who": "any logged-in"},

    # ------------------------------------------------------------------ 3. Organisation profiles
    {"folder": "3. Profiles", "name": "My organisation profile (applicant)", "method": "GET", "path": "profiles/mine/",
     "role": "new_applicant", "expect": 200, "who": "applicant",
     "tests": save("new_profile_id", "pm.response.json().data.id")},
    {"folder": "3. Profiles", "name": "Update my profile with a bad GSTIN → 400", "method": "PATCH",
     "path": "profiles/mine/", "role": "new_applicant", "expect": 400, "who": "applicant",
     "body": {"gstin": "NOT-A-GSTIN"}},
    {"folder": "3. Profiles", "name": "Update my profile with a GSTIN another organisation uses → 400",
     "method": "PATCH", "path": "profiles/mine/", "role": "new_applicant", "expect": 400, "who": "applicant",
     "body": {"gstin": "27AAAAA0001A1Z5"}},
    {"folder": "3. Profiles", "name": "Update my profile (applicant)", "method": "PATCH", "path": "profiles/mine/",
     "role": "new_applicant", "expect": 200, "who": "applicant",
     "body": {"gstin": "{{new_gstin}}", "city": "Pune", "state": "Maharashtra", "contact_name": "Postman Tester"},
     "tests": 'pm.test("waits for staff", () => pm.expect(pm.response.json().data.verification_status).to.eql("pending"));'},
    {"folder": "3. Profiles", "name": "My profile as a judge → 403", "method": "GET", "path": "profiles/mine/",
     "role": "judge", "expect": 403, "who": "judge"},
    {"folder": "3. Profiles", "name": "List organisations waiting (staff)", "method": "GET",
     "path": "profiles/?verification_status=pending", "role": "staff", "expect": 200, "who": "staff, leader"},

    # ------------------------------------------------------------------ 4. Awards
    {"folder": "4. Awards", "name": "List awards (public)", "method": "GET", "path": "awards/", "role": None,
     "expect": 200, "who": "anyone"},
    {"folder": "4. Awards", "name": "One award with its form and criteria", "method": "GET",
     "path": "awards/kaizen/", "role": None, "expect": 200, "who": "anyone",
     "tests": "\n".join([
         "const form = pm.response.json().data.current_form;",
         "const answers = {};",
         "form.questions.forEach(q => { answers[q.key] = q.key === 'org' ? 'Postman Test Industries'",
         "  : (q.type === 'file' ? 'evidence.pdf' : 'Answer from Postman to: ' + q.label); });",
         save("answers_json", "JSON.stringify(answers)"),
     ])},
    {"folder": "4. Awards", "name": "Unknown award → 404", "method": "GET", "path": "awards/no-such-award/",
     "role": None, "expect": 404, "who": "anyone"},

    # ------------------------------------------------------------------ 5. Applications
    {"folder": "5. Applications", "name": "Create an application (applicant)", "method": "POST",
     "path": "applications/", "role": "new_applicant", "expect": 201, "who": "applicant",
     "body": {"award": "kaizen", "title": "Postman test entry"},
     "tests": "\n".join(['const d = pm.response.json().data;',
                         'pm.test("starts as a draft", () => pm.expect(d.status).to.eql("draft"));',
                         save("application_id", "d.id")])},
    {"folder": "5. Applications", "name": "Create a second one for the same award → 400", "method": "POST",
     "path": "applications/", "role": "new_applicant", "expect": 400, "who": "applicant",
     "body": {"award": "kaizen", "title": "Again"}},
    {"folder": "5. Applications", "name": "Create with no award → 400", "method": "POST", "path": "applications/",
     "role": "new_applicant", "expect": 400, "who": "applicant", "body": {"title": "No award"}},
    {"folder": "5. Applications", "name": "Create as staff → 403", "method": "POST", "path": "applications/",
     "role": "staff", "expect": 403, "who": "staff", "body": {"award": "business-excellence", "title": "Staff can't"}},
    {"folder": "5. Applications", "name": "Submit before answering → 400", "method": "POST",
     "path": "applications/{{application_id}}/submit/", "role": "new_applicant", "expect": 400,
     "who": "applicant"},
    {"folder": "5. Applications", "name": "Answer an unknown question → 400", "method": "PATCH",
     "path": "applications/{{application_id}}/", "role": "new_applicant", "expect": 400, "who": "applicant",
     "body": {"content": {"no_such_question": "x"}}},
    {"folder": "5. Applications", "name": "Save answers (applicant)", "method": "PATCH",
     "path": "applications/{{application_id}}/", "role": "new_applicant", "expect": 200, "who": "applicant",
     "raw_body": '{"content": {{answers_json}}}'},
    {"folder": "5. Applications", "name": "Submit (applicant)", "method": "POST",
     "path": "applications/{{application_id}}/submit/", "role": "new_applicant", "expect": 200,
     "who": "applicant",
     "tests": 'pm.test("submitted", () => pm.expect(pm.response.json().data.status).to.eql("submitted"));'},
    # Staff only see organisations that applied to one of their awards, so they verify after the entry.
    {"folder": "5. Applications", "name": "Verify with no body → 400", "method": "POST",
     "path": "profiles/{{new_profile_id}}/verify/", "role": "staff", "expect": 400, "who": "staff, leader",
     "body": {}},
    {"folder": "5. Applications", "name": "Verify the new organisation (staff)", "method": "POST",
     "path": "profiles/{{new_profile_id}}/verify/", "role": "staff", "expect": 200, "who": "staff, leader",
     "body": {"approve": True, "note": "Checked in Postman"},
     "tests": 'pm.test("verified", () => pm.expect(pm.response.json().data.verification_status).to.eql("verified"));'},
    {"folder": "5. Applications", "name": "Edit after submitting → 400", "method": "PATCH",
     "path": "applications/{{application_id}}/", "role": "new_applicant", "expect": 400, "who": "applicant",
     "body": {"title": "Too late"}},
    {"folder": "5. Applications", "name": "Draft for a second award, then delete it", "method": "POST",
     "path": "applications/", "role": "new_applicant", "expect": 201, "who": "applicant",
     "body": {"award": "business-excellence", "title": "Will be deleted"},
     "tests": save("draft_id", "pm.response.json().data.id")},
    {"folder": "5. Applications", "name": "Delete my draft (applicant)", "method": "DELETE",
     "path": "applications/{{draft_id}}/", "role": "new_applicant", "expect": 204, "who": "applicant"},
    {"folder": "5. Applications", "name": "My applications (applicant: own only)", "method": "GET",
     "path": "applications/", "role": "applicant", "expect": 200, "who": "applicant",
     "tests": "\n".join([
         "const rows = pm.response.json().data.results;",
         'pm.test("only my own", () => rows.forEach(r => pm.expect(r.applicant_email).to.eql(pm.variables.get("applicant_email"))));',
         save("other_application_id", "rows[0].id"),
     ])},
    {"folder": "5. Applications", "name": "Open ANOTHER applicant's application → 404", "method": "GET",
     "path": "applications/{{other_application_id}}/", "role": "new_applicant", "expect": 404,
     "who": "applicant"},
    {"folder": "5. Applications", "name": "All applications (staff)", "method": "GET",
     "path": "applications/?status=submitted&search=Postman", "role": "staff", "expect": 200,
     "who": "staff, leader"},
    {"folder": "5. Applications", "name": "One application (leader)", "method": "GET",
     "path": "applications/{{application_id}}/", "role": "leader", "expect": 200, "who": "staff, leader"},
    {"folder": "5. Applications", "name": "Applications as a judge → 403", "method": "GET",
     "path": "applications/", "role": "judge", "expect": 403, "who": "judge"},
    {"folder": "5. Applications", "name": "Applications with NO token → 401", "method": "GET",
     "path": "applications/", "role": None, "expect": 401, "who": "nobody"},
    {"folder": "5. Applications", "name": "Bad status filter → 400", "method": "GET",
     "path": "applications/?status=bogus", "role": "staff", "expect": 400, "who": "staff, leader"},
    {"folder": "5. Applications", "name": "Judges who may take it (staff)", "method": "GET",
     "path": "applications/{{application_id}}/eligible-judges/", "role": "staff", "expect": 200,
     "who": "staff, leader",
     "tests": 'pm.test("best judges first, my judge offered", () => pm.expect(pm.response.json().data.map(j => j.id)).to.include(Number(pm.variables.get("judge_user_id"))));'},
    {"folder": "5. Applications", "name": "Eligible judges with a bad round → 400", "method": "GET",
     "path": "applications/{{application_id}}/eligible-judges/?round=abc", "role": "staff", "expect": 400,
     "who": "staff, leader"},

    # ------------------------------------------------------------------ 6. Assignments
    {"folder": "6. Assignments", "name": "Accept the entry (staff check)", "method": "POST",
     "path": "applications/{{application_id}}/change-status/", "role": "staff", "expect": 200, "who": "staff",
     "body": {"status": "accepted"},
     "tests": 'pm.test("accepted for judging", () => pm.expect(pm.response.json().data.status).to.eql("accepted"));'},
    {"folder": "6. Assignments", "name": "Assign a judge (staff)", "method": "POST", "path": "assignments/",
     "role": "staff", "expect": 201, "who": "staff, leader",
     "body": {"report": "{{application_id}}", "judge": "{{judge_user_id}}", "round": 1},
     "tests": save("assignment_id", "pm.response.json().data.id")},
    {"folder": "6. Assignments", "name": "Assign the same judge again → 400", "method": "POST",
     "path": "assignments/", "role": "staff", "expect": 400, "who": "staff, leader",
     "body": {"report": "{{application_id}}", "judge": "{{judge_user_id}}"}},
    {"folder": "6. Assignments", "name": "Assign with a missing report → 400", "method": "POST",
     "path": "assignments/", "role": "staff", "expect": 400, "who": "staff, leader",
     "body": {"report": 999999, "judge": "{{judge_user_id}}"}},
    {"folder": "6. Assignments", "name": "Assign as a judge → 403", "method": "POST", "path": "assignments/",
     "role": "judge", "expect": 403, "who": "judge",
     "body": {"report": "{{application_id}}", "judge": "{{judge_user_id}}"}},
    {"folder": "6. Assignments", "name": "Bulk assign exact pairs (staff)", "method": "POST",
     "path": "assignments/bulk/", "role": "staff", "expect": 201, "who": "staff, leader",
     "body": {"round": 1, "items": [{"report": "{{application_id}}", "judge": "{{third_judge_id}}"}]},
     "tests": save("third_assignment_id", "pm.response.json().data[0].id")},
    {"folder": "6. Assignments", "name": "Bulk assign with nothing to do → 400", "method": "POST",
     "path": "assignments/bulk/", "role": "staff", "expect": 400, "who": "staff, leader", "body": {"items": []}},
    {"folder": "6. Assignments", "name": "Bulk assign as an applicant → 403", "method": "POST",
     "path": "assignments/bulk/", "role": "applicant", "expect": 403, "who": "applicant",
     "body": {"reports": ["{{application_id}}"]}},
    {"folder": "6. Assignments", "name": "Reassign to another judge (staff)", "method": "POST",
     "path": "assignments/{{third_assignment_id}}/reassign/", "role": "staff", "expect": 201,
     "who": "staff, leader", "body": {"judge": "{{judge2_user_id}}"},
     "tests": save("judge2_assignment_id", "pm.response.json().data.id")},
    {"folder": "6. Assignments", "name": "Reassign to a judge already on it → 400", "method": "POST",
     "path": "assignments/{{assignment_id}}/reassign/", "role": "staff", "expect": 400, "who": "staff, leader",
     "body": {"judge": "{{judge2_user_id}}"}},
    {"folder": "6. Assignments", "name": "All assignments for the report (staff)", "method": "GET",
     "path": "assignments/?report={{application_id}}", "role": "staff", "expect": 200, "who": "staff, leader"},
    {"folder": "6. Assignments", "name": "My assigned reports (judge)", "method": "GET",
     "path": "judge/my-assignments/", "role": "judge", "expect": 200, "who": "judge",
     "tests": "\n".join([
         "const rows = pm.response.json().data.results;",
         "const mine = rows.find(r => r.id === Number(pm.variables.get('assignment_id')));",
         'pm.test("the new report is in my list", () => pm.expect(mine).to.be.an("object"));',
         'pm.test("row has title, applicant, submission date, status, criteria", () => {',
         "  pm.expect(mine.report).to.include.keys('title', 'applicant', 'submitted_at', 'report_status');",
         "  pm.expect(mine.status).to.eql('pending'); pm.expect(mine.criteria.length).to.be.above(0);",
         "});",
         "const scores = {}; mine.criteria.forEach(c => scores[c.key] = 7);",
         save("scores_json", "JSON.stringify(scores)"),
         save("first_criterion", "mine.criteria[0].key"),
     ])},
    {"folder": "6. Assignments", "name": "My assignments as staff → 403", "method": "GET",
     "path": "judge/my-assignments/", "role": "staff", "expect": 403, "who": "staff"},
    {"folder": "6. Assignments", "name": "Open ANOTHER judge's assignment → 404", "method": "GET",
     "path": "assignments/{{judge2_assignment_id}}/", "role": "judge", "expect": 404, "who": "judge"},
    {"folder": "6. Assignments", "name": "Accept ANOTHER judge's assignment → 404", "method": "POST",
     "path": "assignments/{{judge2_assignment_id}}/accept/", "role": "judge", "expect": 404, "who": "judge"},
    {"folder": "6. Assignments", "name": "Accept my assignment (judge)", "method": "POST",
     "path": "assignments/{{assignment_id}}/accept/", "role": "judge", "expect": 200, "who": "judge",
     "tests": 'pm.test("in review", () => pm.expect(pm.response.json().data.status).to.eql("in_review"));'},
    {"folder": "6. Assignments", "name": "One assignment with the report (judge)", "method": "GET",
     "path": "assignments/{{assignment_id}}/", "role": "judge", "expect": 200, "who": "judge"},
    {"folder": "6. Assignments", "name": "Decline after accepting → 400", "method": "POST",
     "path": "assignments/{{assignment_id}}/decline/", "role": "judge", "expect": 400, "who": "judge"},
    {"folder": "6. Assignments", "name": "Accept (second judge)", "method": "POST",
     "path": "assignments/{{judge2_assignment_id}}/accept/", "role": "judge2", "expect": 200, "who": "judge"},

    # ------------------------------------------------------------------ 7. Evaluations
    {"folder": "7. Evaluations", "name": "Save scores midway (judge)", "method": "POST", "path": "evaluations/",
     "role": "judge", "expect": 201, "who": "judge",
     "raw_body": '{"assignment": {{assignment_id}}, "scores": {"{{first_criterion}}": 6}, "submit": false}',
     "tests": save("evaluation_id", "pm.response.json().data.id")},
    {"folder": "7. Evaluations", "name": "Score of 11 → 400", "method": "POST", "path": "evaluations/",
     "role": "judge", "expect": 400, "who": "judge",
     "raw_body": '{"assignment": {{assignment_id}}, "scores": {"{{first_criterion}}": 11}}'},
    {"folder": "7. Evaluations", "name": "Score true/false → 400", "method": "POST", "path": "evaluations/",
     "role": "judge", "expect": 400, "who": "judge",
     "raw_body": '{"assignment": {{assignment_id}}, "scores": {"{{first_criterion}}": true}}'},
    {"folder": "7. Evaluations", "name": "Score ANOTHER judge's assignment → 404", "method": "POST",
     "path": "evaluations/", "role": "judge", "expect": 404, "who": "judge",
     "raw_body": '{"assignment": {{judge2_assignment_id}}, "scores": {{scores_json}}}'},
    {"folder": "7. Evaluations", "name": "Evaluate as staff → 403", "method": "POST", "path": "evaluations/",
     "role": "staff", "expect": 403, "who": "staff",
     "raw_body": '{"assignment": {{assignment_id}}, "scores": {{scores_json}}}'},
    {"folder": "7. Evaluations", "name": "Submit every score + feedback (judge)", "method": "PATCH",
     "path": "evaluations/{{evaluation_id}}/", "role": "judge", "expect": 200, "who": "judge",
     "raw_body": '{"scores": {{scores_json}}, "feedback": "Strong evidence (Postman).", "submit": true}',
     "tests": 'pm.test("submitted with a total", () => { const d = pm.response.json().data; pm.expect(d.status).to.eql("submitted"); pm.expect(Number(d.total_score)).to.be.above(0); });'},
    {"folder": "7. Evaluations", "name": "Change a submitted evaluation directly → 400", "method": "PATCH",
     "path": "evaluations/{{evaluation_id}}/", "role": "judge", "expect": 400, "who": "judge",
     "raw_body": '{"scores": {{scores_json}}}'},
    {"folder": "7. Evaluations", "name": "Second judge submits", "method": "POST", "path": "evaluations/",
     "role": "judge2", "expect": 201, "who": "judge",
     "raw_body": '{"assignment": {{judge2_assignment_id}}, "scores": {{scores_json}}, "feedback": "Good.", "submit": true}'},
    {"folder": "7. Evaluations", "name": "The report is now scored (staff)", "method": "GET",
     "path": "applications/{{application_id}}/", "role": "staff", "expect": 200, "who": "staff, leader",
     "tests": 'pm.test("scored", () => pm.expect(pm.response.json().data.status).to.eql("scored"));'},
    {"folder": "7. Evaluations", "name": "All evaluations of the report (staff)", "method": "GET",
     "path": "evaluations/?assignment={{assignment_id}}", "role": "staff", "expect": 200, "who": "staff, leader"},
    {"folder": "7. Evaluations", "name": "Evaluations as an applicant → 403", "method": "GET",
     "path": "evaluations/", "role": "applicant", "expect": 403, "who": "applicant"},
    {"folder": "7. Evaluations", "name": "Ask to change a score (judge)", "method": "POST",
     "path": "evaluations/{{evaluation_id}}/request-change/", "role": "judge", "expect": 201, "who": "judge",
     "body": {"reason": "I misread the results section."},
     "tests": save("change_request_id", "pm.response.json().data.id")},
    {"folder": "7. Evaluations", "name": "Change scores before anyone allows it → 400", "method": "POST",
     "path": "evaluations/{{evaluation_id}}/change-scores/", "role": "judge", "expect": 400, "who": "judge",
     "raw_body": '{"scores": {"{{first_criterion}}": 9}, "reason": "Too early"}'},
    {"folder": "7. Evaluations", "name": "Score-change requests (staff)", "method": "GET",
     "path": "score-change-requests/?status=requested", "role": "staff", "expect": 200, "who": "staff, leader"},
    {"folder": "7. Evaluations", "name": "Leaders don't decide score changes → 403", "method": "POST",
     "path": "score-change-requests/{{change_request_id}}/decide/", "role": "leader", "expect": 403,
     "who": "staff, then the award manager", "body": {"approve": True}},
    {"folder": "7. Evaluations", "name": "Check the change and pass it to the award manager (staff)", "method": "POST",
     "path": "score-change-requests/{{change_request_id}}/decide/", "role": "staff", "expect": 200,
     "who": "staff first, then leader", "body": {"approve": True, "note": "Checked in Postman"},
     "tests": 'pm.test("waiting for the award manager", () => pm.expect(pm.response.json().data.status).to.eql("staff_approved"));'},
    {"folder": "7. Evaluations", "name": "Change scores with only staff's check → 400", "method": "POST",
     "path": "evaluations/{{evaluation_id}}/change-scores/", "role": "judge", "expect": 400, "who": "judge",
     "raw_body": '{"scores": {"{{first_criterion}}": 9}, "reason": "Still too early"}'},
    {"folder": "7. Evaluations", "name": "Confirm the change (award manager)", "method": "POST",
     "path": "score-change-requests/{{change_request_id}}/decide/", "role": "manager", "expect": 200,
     "who": "staff first, then leader", "body": {"approve": True},
     "tests": 'pm.test("approved", () => pm.expect(pm.response.json().data.status).to.eql("approved"));'},
    {"folder": "7. Evaluations", "name": "Change a score with a reason (judge)", "method": "POST",
     "path": "evaluations/{{evaluation_id}}/change-scores/", "role": "judge", "expect": 200, "who": "judge",
     "raw_body": '{"scores": {"{{first_criterion}}": 9}, "reason": "Re-read the results section."}',
     "tests": 'pm.test("change recorded with who and why", () => { const c = pm.response.json().data.score_changes; pm.expect(c.length).to.be.above(0); pm.expect(c[0].reason).to.include("Re-read"); });'},

    # ------------------------------------------------------------------ 8. Decisions and edit requests
    {"folder": "8. Decisions", "name": "Staff decide a result → 400 (the award manager decides)", "method": "POST",
     "path": "applications/{{application_id}}/change-status/", "role": "staff", "expect": 400,
     "who": "award manager", "body": {"status": "approved"}},
    {"folder": "8. Decisions", "name": "A leader decides a single entry → 400 (leaders approve whole awards)",
     "method": "POST", "path": "applications/{{application_id}}/change-status/", "role": "leader", "expect": 400,
     "who": "award manager", "body": {"status": "approved"}},
    {"folder": "8. Decisions", "name": "Decide the entry: successful (award manager)", "method": "POST",
     "path": "applications/{{application_id}}/change-status/", "role": "manager", "expect": 200,
     "who": "award manager", "body": {"status": "approved", "note": "Decided in Postman"},
     "tests": 'pm.test("decided, not published yet", () => pm.expect(pm.response.json().data.status).to.eql("approved"));'},
    {"folder": "8. Decisions", "name": "Set an unknown status → 400", "method": "POST",
     "path": "applications/{{application_id}}/change-status/", "role": "manager", "expect": 400,
     "who": "award manager", "body": {"status": "draft"}},
    {"folder": "8. Decisions", "name": "The applicant still sees it waiting for the decision", "method": "GET",
     "path": "applications/{{application_id}}/", "role": "new_applicant", "expect": 200, "who": "applicant",
     "tests": 'pm.test("provisional result hidden", () => pm.expect(pm.response.json().data.status).to.eql("scored"));'},
    {"folder": "8. Decisions", "name": "Ask to edit after judging → 400 (only before judging starts)",
     "method": "POST", "path": "applications/{{application_id}}/request-edit/", "role": "new_applicant",
     "expect": 400, "who": "applicant", "body": {"reason": "Wrong turnover figure."}},
    {"folder": "8. Decisions", "name": "Ask for a re-evaluation before the award's result is approved → 400",
     "method": "POST", "path": "applications/{{application_id}}/request-reevaluation/", "role": "new_applicant",
     "expect": 400, "who": "applicant", "body": {"reason": "Our energy data may have been missed."}},
    {"folder": "8. Decisions", "name": "Decide a re-evaluation nobody asked for → 400", "method": "POST",
     "path": "applications/{{application_id}}/decide-reevaluation/", "role": "manager", "expect": 400,
     "who": "award manager", "body": {"allow": True}},

    # ------------------------------------------------------------------ 9. Conflicts
    {"folder": "9. Conflicts", "name": "Record a conflict (staff)", "method": "POST", "path": "conflicts/",
     "role": "staff", "expect": 201, "who": "staff, leader",
     "body": {"judge": "{{third_judge_id}}", "applicant_profile": "{{new_profile_id}}",
              "reason": "Former consultant (Postman)"}},
    {"folder": "9. Conflicts", "name": "Conflicted judge is no longer offered", "method": "GET",
     "path": "applications/{{application_id}}/eligible-judges/", "role": "staff", "expect": 200,
     "who": "staff, leader",
     "tests": 'pm.test("not offered", () => pm.expect(pm.response.json().data.map(j => j.id)).to.not.include(Number(pm.variables.get("third_judge_id"))));'},
    {"folder": "9. Conflicts", "name": "List conflicts (staff)", "method": "GET", "path": "conflicts/",
     "role": "staff", "expect": 200, "who": "staff, leader"},
    {"folder": "9. Conflicts", "name": "Record a conflict as a judge → 403", "method": "POST", "path": "conflicts/",
     "role": "judge", "expect": 403, "who": "judge",
     "body": {"judge": "{{judge_user_id}}", "applicant_profile": "{{new_profile_id}}"}},

    # ------------------------------------------------------------------ 10. Dashboards, lookups, notifications
    {"folder": "10. Dashboards", "name": "Summary (applicant: own reports)", "method": "GET",
     "path": "dashboard/summary/", "role": "applicant", "expect": 200, "who": "applicant",
     "tests": 'pm.test("counts by status", () => pm.expect(pm.response.json().data).to.have.property("applications_by_status"));'},
    {"folder": "10. Dashboards", "name": "Summary (judge: own assignments)", "method": "GET",
     "path": "dashboard/summary/", "role": "judge", "expect": 200, "who": "judge",
     "tests": 'pm.test("counts by status", () => pm.expect(pm.response.json().data).to.have.property("assignments_by_status"));'},
    {"folder": "10. Dashboards", "name": "Summary (staff: whole event)", "method": "GET",
     "path": "dashboard/summary/", "role": "staff", "expect": 200, "who": "staff",
     "tests": 'pm.test("per award", () => pm.expect(pm.response.json().data.awards.length).to.be.above(0));'},
    {"folder": "10. Dashboards", "name": "Summary (leader: whole event)", "method": "GET",
     "path": "dashboard/summary/", "role": "leader", "expect": 200, "who": "leader"},
    {"folder": "10. Dashboards", "name": "Summary with NO token → 401", "method": "GET", "path": "dashboard/summary/",
     "role": None, "expect": 401, "who": "nobody"},
    {"folder": "10. Dashboards", "name": "Lookups (codes and labels)", "method": "GET", "path": "lookups/",
     "role": "applicant", "expect": 200, "who": "any logged-in"},
    {"folder": "10. Dashboards", "name": "My notifications (judge)", "method": "GET", "path": "notifications/",
     "role": "judge", "expect": 200, "who": "any logged-in",
     "tests": save("notification_id", "pm.response.json().data.results[0].id")},
    {"folder": "10. Dashboards", "name": "Mark a notification read (judge)", "method": "POST",
     "path": "notifications/{{notification_id}}/read/", "role": "judge", "expect": 200, "who": "any logged-in"},
    {"folder": "10. Dashboards", "name": "Mark ANOTHER user's notification → 404", "method": "POST",
     "path": "notifications/{{notification_id}}/read/", "role": "judge2", "expect": 404, "who": "judge"},

    # ------------------------------------------------------------------ 11. Logout (last: ends the sessions)
    {"folder": "11. Logout", "name": "Logout (new applicant)", "method": "POST", "path": "auth/logout/",
     "role": "new_applicant", "expect": 200, "who": "any logged-in", "body": {"refresh": "{{new_applicant_refresh}}"}},
    {"folder": "11. Logout", "name": "Refresh after logout → 401", "method": "POST", "path": "auth/refresh/",
     "role": None, "expect": 401, "who": "anyone", "body": {"refresh": "{{new_applicant_refresh}}"}},
]

# --- Builders ---------------------------------------------------------------------------


def common_tests(expect):
    lines = [f'pm.test("status is {expect}", () => pm.response.to.have.status({expect}));']
    if expect != 204:
        lines += [
            'pm.test("body is {success, data, message, errors}", () => {',
            "  const j = pm.response.json();",
            "  pm.expect(j).to.have.all.keys('success', 'data', 'message', 'errors');",
            f"  pm.expect(j.success).to.eql({'true' if expect < 400 else 'false'});",
            "});",
        ]
    return lines


def item(spec):
    path = spec["path"]
    raw_path, _, query = path.partition("?")
    url = {"raw": "{{base_url}}/" + path, "host": ["{{base_url}}"], "path": [p for p in raw_path.split("/") if p] + [""]}   # "" keeps the trailing slash Django needs
    if query:
        url["query"] = [dict(zip(("key", "value"), q.split("=", 1), strict=True)) for q in query.split("&")]
    request = {"method": spec["method"], "header": [], "url": url,
               "description": f"Who: {spec['who']}. Expected: {spec['expect']}."}
    token = TOKEN[spec["role"]]
    request["auth"] = ({"type": "bearer", "bearer": [{"key": "token", "value": f"{{{{{token}}}}}", "type": "string"}]}
                       if token else {"type": "noauth"})
    body = spec.get("raw_body")
    if body is None and spec.get("body") is not None:
        body = json.dumps(spec["body"], indent=2)
        # numbers from variables: "{{id}}" → {{id}} so the JSON gets a number, not a string
        for var in ("application_id", "judge_user_id", "judge2_user_id", "third_judge_id", "new_profile_id",
                    "assignment_id"):
            body = body.replace(f'"{{{{{var}}}}}"', f"{{{{{var}}}}}")
    if body is not None:
        request["header"].append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {"mode": "raw", "raw": body, "options": {"raw": {"language": "json"}}}
    events = [{"listen": "test", "script": {"type": "text/javascript",
                                            "exec": common_tests(spec["expect"]) + spec.get("tests", "").splitlines()}}]
    if spec.get("pre"):
        events.insert(0, {"listen": "prerequest", "script": {"type": "text/javascript",
                                                              "exec": spec["pre"].splitlines()}})
    return {"name": spec["name"], "request": request, "event": events}


def build():
    folders = {}
    for spec in REQUESTS:
        folders.setdefault(spec["folder"], []).append(item(spec))
    collection = {
        "info": {"name": NAME, "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                 "description": "Run top to bottom on the seed data (Collection Runner). Set demo_password in the "
                                "environment to DEMO_PASSWORD from your .env first. See postman/README.md."},
        "item": [{"name": name, "item": items} for name, items in folders.items()],
        "variable": [{"key": k, "value": ""} for k in (
            "applicant_token", "staff_token", "judge_token", "judge2_token", "leader_token", "manager_token",
            "manager_user_id", "new_applicant_token",
            "applicant_user_id", "staff_user_id", "judge_user_id", "judge2_user_id", "leader_user_id",
            "new_applicant_user_id", "third_judge_id", "created_user_id", "new_profile_id", "application_id",
            "draft_id", "other_application_id", "assignment_id", "judge2_assignment_id", "third_assignment_id",
            "evaluation_id", "change_request_id", "notification_id", "answers_json", "scores_json",
            "first_criterion", "new_applicant_email", "new_password", "new_gstin", "old_refresh")],
    }
    environment = {
        "name": "Awards Platform (local)",
        "values": [
            {"key": "base_url", "value": "http://localhost:8000/api/v1", "enabled": True},
            {"key": "demo_password", "value": "", "type": "secret", "enabled": True},
            {"key": "applicant_email", "value": "priya@acme.example", "enabled": True},
            {"key": "staff_email", "value": "staff@awards.example", "enabled": True},
            {"key": "judge_email", "value": "kapoor@judges.example", "enabled": True},
            {"key": "judge2_email", "value": "rao@judges.example", "enabled": True},
            {"key": "leader_email", "value": "leader@awards.example", "enabled": True},
            {"key": "manager_email", "value": "manager@awards.example", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }
    (HERE / "Awards-Platform.postman_collection.json").write_text(json.dumps(collection, indent=2) + "\n",
                                                                   encoding="utf-8")
    (HERE / "Awards-Platform.postman_environment.json").write_text(json.dumps(environment, indent=2) + "\n",
                                                                    encoding="utf-8")
    rows = ["# Postman testing checklist", "",
            "Generated from `build_collection.py`, in run order. Tick **Pass/Fail** as you run each request "
            "(the Collection Runner also checks status and response shape automatically).", "",
            "| # | Folder | Request | Method | Endpoint | Role | Expected | Pass/Fail |",
            "|---|---|---|---|---|---|---|---|"]
    for n, spec in enumerate(REQUESTS, start=1):
        rows.append(f"| {n} | {spec['folder']} | {spec['name']} | {spec['method']} | `/api/v1/{spec['path']}` | "
                    f"{spec['who']} | {spec['expect']} | ☐ |")
    (HERE / "CHECKLIST.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"{len(REQUESTS)} requests in {len(folders)} folders")


if __name__ == "__main__":
    build()
