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

## D6. Focus the build on the applicant workflow, with real data

**Date:** 13 Oct 2026

**Context:** after the 12 Oct meeting, the plan was to make a skeleton of each user's workflow. The many mock screens (judges, staff, leadership, 8 awards) with sample data were more than needed and hid the real flow.

**Options**
1. Keep all mock screens and keep adding sample data
2. Remove the mock screens and build one workflow for real (database, verification, rules), starting with the applicant
3. Build all four workflows for real at once

**Picked:** Option 2

**Why:** one real, tested workflow is worth more than many pictures. The applicant workflow comes first because every other user depends on applications existing. Rule 4 (form versions) is now real and tested. The old screens are kept in git (tag `v0.2-skeleton-ui`).

**Also decided in the 12 Oct meeting and built:** email verification first; organisation verified by GSTIN plus the holder's PAN; one report per organisation; forms saved midway; changes after submit only with staff confirmation. **Judges no longer declare conflicts**; staff check them (changes the earlier plan).

**What would change our mind:** if the reviewer needs to see the judge or leadership side in the next demo, build the judge workflow next on the same pattern.

---

## D7. Build every user's workflow from the 12 Oct meeting, with the rules in one place

**Date:** 13 Oct 2026

**What we built:** judge (email link, accept/decline, partial grading, score changes with staff permission), Round 2 (online meeting with a group of judges), staff (confirm/reject, assign judges, conflicts, workload, judges per report, requests, forms, activity log) and leadership (dashboard of the whole event).

**Key choices**

| Choice | Options | Picked | Why |
|---|---|---|---|
| Where the rules live | In each page vs. one module | One module: `apps/judging/services.py` | Every screen goes through the same rules, so a rule can't be skipped by a page that forgot it; easy to test |
| Judge login | Email code vs. signed link | Both: the link from the email (as the meeting asked) and the email code | The link is the meeting's design; the code is a fallback if the link expires (7 days) |
| Conflicts | Judge declares vs. staff record | Staff record (meeting decision) | Judges rarely declare; the system refuses conflicted judges everywhere, including Round 2 |
| Assigning | Manual only vs. suggestions + auto | Suggestions ordered by priority then load, plus "auto-assign" | Matches "priority list" and "balance the workload"; staff can still choose |
| Score change records | Editable vs. permanent | Permanent (cannot be edited or deleted, even in admin) | Rule 3 must hold even against mistakes |
| Final score | Many options | Average of judges' weighted totals, per round | Simple and explainable; how Round 1 and 2 combine is still an open question for the client |

**Left out on purpose:** blind judging (not in the meeting; Round 2 is face to face), real email sending, messaging inside the app (staff use email/phone), results publishing and the public leaderboard (next).

**What would change our mind:** if the client wants blind judging for Round 1, hide identifying answers in the judge's grading page (the earlier prototype showed how; tag `v0.2-skeleton-ui`).
