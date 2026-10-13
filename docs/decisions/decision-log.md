# Decision Log

Each decision: the options, the one we picked, why, and what would change our mind.

---

## D1. Framework: Django + PostgreSQL

**Date:** 11 Oct 2026

**Options**
1. Django + PostgreSQL (Python)
2. Spring Boot + PostgreSQL (Java)
3. React + Node/Express + PostgreSQL (JavaScript)

**Picked:** Django + PostgreSQL

**Why:** Django gives login, an admin screen, forms and database migrations built in, so more time goes into the four rules instead of plumbing. One app to run instead of two. PostgreSQL stores each form version's questions as JSON reliably.

**What would change our mind:** a need for a mobile app or very interactive screens. Then we would add a React frontend over a Django REST API.

---

## D2. Project structure: one Django project, apps split by business area

**Date:** 11 Oct 2026

**Options**
1. One app split into modules: accounts, awards, entries, judging, dashboard (modular monolith)
2. Separate frontend and backend repositories
3. Microservices

**Picked:** Option 1. See [Architecture.md](../Architecture.md).

**Why:** right size for a small team. Each module matches a user workflow, and each rule is enforced in the module that owns its data.

**What would change our mind:** several teams working on separate parts, or one part needing to scale on its own.

---

## D3. Keep award settings in the browser session until the database is built

**Date:** 12 Oct 2026

**Options**
1. Build the real award tables first, then connect the settings screen
2. Keep settings in the browser session for now, so every screen can follow them today
3. Leave the settings screen as a picture with no saving

**Picked:** Option 2

**Why:** it makes the brief's main point (two awards that differ by settings, not code) work and testable now, and fixes wrong sample content quickly. Each award's settings, criteria, eligibility and form live in one place (`apps/core/demo_data.py`), shaped the way the real tables will be, so moving to the database is a straight swap.

**Trade-off:** settings are lost when the browser session ends, and each browser sees its own settings. Fine for a demo, not for real use.

**What would change our mind:** as soon as the AwardCycle table exists, settings move there (planned next).

---

## D4. Hide identifying answers on the server, before the page is built

**Date:** 12 Oct 2026

**Options**
1. Send everything to the page and hide names with CSS or JavaScript
2. Remove identifying answers (and file names) on the server, so the page never receives them

**Picked:** Option 2

**Why:** with option 1, the names are still in the page source, so anyone can read them. Rule 1 says a judge *cannot* see who applied, so the data must never reach them. File names are hidden too, because a file like `acme-strategy-2026.pdf` gives the company away.

**What would change our mind:** nothing for blind awards. This is the only safe way.

---

## D5. Each round has a type, and blind judging only works in desk review

**Date:** 12 Oct 2026

**Why this came up:** Kaizen and 5S are judged by visiting the shop floor. A judge standing in the plant with the team can't be "blind", and before/after photos show the factory too. The system let staff switch blind judging on for any award, which made no sense for in-person judging.

**Options**
1. Keep a simple round count (1 or 2) and trust staff not to switch blind on for site-visit awards
2. Give each round a type (desk review, site visit, live presentation); allow blind judging only if at least one round is a desk review, and apply it only in those rounds
3. Remove blind judging for all shop-floor awards by sector

**Picked:** Option 2

**Why:** it matches how the awards really work, and the rule is enforced by the system (switch disabled on screen, rejected on the server, and a safety check in the data), not left to memory. Option 3 ties a rule to a sector name, which breaks as soon as a shop-floor award adds a desk round.

**Assumption to confirm with the client:** Kaizen screens written entries at a desk first, then visits only the shortlisted teams.

**Where the model breaks:** a pure on-site audit (like 5S) doesn't fit "the applicant fills a form, the judge scores the form". Judges fill a checklist on the floor instead. We show the round type, but an on-site checklist screen is out of scope for now.

**What would change our mind:** if the client says every Kaizen entry gets a site visit with no desk screening, Kaizen becomes one site-visit round, and blind judging is simply unavailable for it.

---

## D6. Authentication: email + password, four role tabs, role checked on the server

**Date:** 14 Oct 2026

**What we needed:** sign up (applicants only) and log in for four roles, with each role seeing only what it's allowed to.

| Choice | Options | Picked | Why |
|---|---|---|---|
| Tokens vs. sessions | JWT in the browser vs. secure session cookie | **Session cookie** (HttpOnly, SameSite=Lax, Secure outside local dev) | Our pages are built by Django on the server, so sessions are the standard, simplest fit; nothing to store in JavaScript. The session holds the user id and the role |
| Password hashing | bcrypt vs. Django's PBKDF2 | **PBKDF2-SHA256** (Django default, salted, 1M rounds) | Equivalent strength, no extra package; switching to bcrypt or Argon2 later is one setting |
| Where the role lives | Separate tables per role vs. one `role` field | **One `role` field on the user** | Each person has exactly one role; replaces the old `is_leader` flag (migrated) |
| Role check | In the page only vs. on the server | **On the server**: the login form rejects a correct password on the wrong tab, and every portal view checks the role | The UI can be bypassed; the server can't |
| Wrong role | Redirect vs. error | **403 Access Denied** page | Clear to the user; logged-out users are sent to log in instead |
| Error messages | "No such account" vs. one message | **One message** for unknown email, wrong password and wrong tab | Doesn't reveal which emails have accounts |
| Award settings | Browser session vs. database | **Database** (`AwardSetting`) | With real logins, staff and judges are different sessions; a judge must see the blind-judging setting staff saved (this completes D3) |

**Accounts for staff, judges and leaders** are created in `/admin/` (by an admin) or by `python manage.py seed_demo` for the demo. They can't sign up.

**Not built yet (known gaps):** limiting repeated failed logins (brute force), two-factor login, and **verifying new applicants** before they get access. The 13 Oct meeting flagged that last one as unclear; sign-up currently gives immediate access.

**What would change our mind:** a separate mobile app or API clients would need token auth (e.g. JWT) alongside sessions.

**Update (14 Oct 2026): one login form instead of four tabs.** The user asked for a single login: everyone enters email + password and is sent to their own area based on the **role stored on their account** (applicant → applicant portal, staff → staff portal, and so on). The role is never chosen by the person logging in; a role sent with the form is ignored. Access control is unchanged: every portal page still checks the role on the server and returns 403 Access Denied to other roles. Error messages no longer mention tabs: "Incorrect email or password."

---

## D7. Backend foundation: models, service layer and a versioned REST API

**Date:** 14 Oct 2026 · Data model approved by the user before building ([Data-Model.md](../Data-Model.md)).

| Choice | Options | Picked | Why |
|---|---|---|---|
| App layout | Rename the existing screen apps vs. add new domain apps | **New apps** (`applications`, `assignments`, `evaluations`, `notifications`, `audit`) next to the existing screen apps | Nothing that works today breaks; the screens move to real data in Phase 3 |
| Business logic | In views/serializers vs. a service layer | **`services.py` per app** | One place for each rule, used by the API, the admin, the seed command and later the screens; easy to test |
| Scores | JSON blob vs. one row per criterion | **`CriterionScore` rows** | Database enforces 1–10; reports and dashboards can query scores |
| Delete | Hard delete vs. soft delete | **Soft delete** for Award and Application; **PROTECT** on judging history | History and the audit trail must survive |
| API auth | Session only vs. JWT | **JWT** (access + refresh, rotation, blacklist on logout) for API clients; sessions stay for the web pages | Frontend and mobile clients; role in the token claims |
| Role at login | Required vs. optional | **Optional**: if sent, it must match | The web login is one form (user decision); the API still rejects a mismatched role on the server |
| Object-level security | Check after loading vs. filter the queryset | **Filter in `get_queryset()`** | Another user's record returns 404, so ids can't be probed |
| Response format | DRF default vs. envelope | **`{success, data, message, errors}`** for every response | One shape for the frontend to handle |
| Lint/format | black + isort + flake8 vs. ruff | **ruff** | One fast tool doing all three |
| Award settings screen | Keep `AwardSetting` JSON vs. real columns | **Real `Award`/`AwardRound` columns** (`AwardSetting` removed) | One source of truth; audited |

**Assumptions made:** Phase 2 of the roadmap, 10 working days; ApplicantProfile fields taken from the organisation-profile screen; Kaizen and Business Excellence as the two demo awards.

**What would change our mind:** a separate frontend team might want cookie-based JWT (HttpOnly) instead of Bearer headers; large file uploads would move attachments to object storage (S3-style).
