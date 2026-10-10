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
