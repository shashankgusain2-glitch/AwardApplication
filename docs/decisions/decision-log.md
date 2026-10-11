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
