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

---

## D8. Steps 3.4 and 3.5: finish the API; connect the screens through the service layer

**Date:** 14 Oct 2026

| Choice | Options | Picked | Why |
|---|---|---|---|
| Frontend | React / Next.js / Vue vs. the existing Django templates | **The existing Django templates** | The skeleton is already built with them, and the roadmap's 4 hours for 3.5 is enough to connect them, not to rebuild them in a new framework |
| How screens reach the data | Call the REST API over HTTP from the browser vs. call the services directly | **Call the same `services.py` functions the API views call** | One place for every rule (Rule 1–4, ownership, roles), so a screen and an API call can never disagree. No mock data is left on any role's screens |
| Web login | Four tabs (one per role) vs. one form | **One form** (unchanged, see D6) | The user chose a single login earlier. The role still comes from the account; the API keeps an optional `role` field that is refused if it doesn't match, and Postman tests the wrong role |
| JWT in the browser | A fetch wrapper storing tokens vs. session cookies | **Session cookies** for the web pages; JWT stays for API clients (Postman, a future app) | No tokens in browser storage; CSRF protection on every form. CORS is already configured for a future separate frontend |
| Bulk assign | Partial success vs. all or nothing | **All or nothing** | A half-assigned batch is hard to reason about; the error names the item that broke a rule |
| Who deactivates accounts | Staff and leaders vs. leaders only | **Leaders only** | Matches account creation (D6/D7). Staff can read the user list |
| Blind judging (found while integrating) | Hide identifying answers only vs. also the title and file names | **Also the title and file names** in blind rounds | Real entries put the company's name in the title and in file names; both leaked to judges before |

**What would change our mind:** a separate mobile app or a JavaScript frontend would use the same API (and the Postman collection documents it); it would need its own token storage and refresh handling.

---

## D9. Award managers, and staff only see their own awards

**Date:** 15 Oct 2026 · Asked by the user: staff should only reach the awards allocated to them; a new role works under leadership and runs specific awards; creating awards moves from staff to leaders.

| Choice | Options | Picked | Why |
|---|---|---|---|
| New role | Make some staff "senior" with a flag vs. a fifth role | **A fifth role, `manager` ("Award manager")** | One role per account is how every check already works (D6); a flag would need checking in a second place |
| Managers per award | Several vs. one | **One manager per award** (`Award.manager`); a manager can run several awards | The request: "each award is assigned to a specific manager". One clear owner per award |
| Staff allocation | Staff pick awards vs. assigned to them | **Assigned** (`Award.staff`) by a leader or that award's manager | Staff shouldn't grant themselves access |
| Where the rule lives | Check in each view vs. one helper | **`apps/awards/access.py` → `awards_for(user)`**, used by every `visible_to()`, staff page, API queryset, file download, request list and notification | One place to read and test; another award's record gives 404 (same as D7's object-level rule) |
| Managers' portal | A separate set of pages vs. the staff portal | **The staff portal**, scoped to their awards, plus a Team page | Managers do the same work as staff; no duplicated screens |
| Two-step requests | Managers as the first or the final step | **First step (the staff check)** on their own awards; the final confirmation stays with leaders | Keeps "staff check, leadership confirms" (D8) unchanged | *Changed by D12 for applicants' edit requests: the award manager now confirms them.*
| Creating awards | Staff vs. leaders | **Leaders only**, choosing the manager on the same form | The request; awards are a leadership decision |
| Existing data | Put every existing staff member on every award vs. nobody | **Nobody**: leaders allocate after the upgrade (the demo seed allocates its own staff) | Giving everyone everything would undo the point of the change |
| Organisations to verify | All vs. only those on my awards | **Only organisations that applied to one of their awards** (leaders: all) | An organisation is checked by the team that will judge it |

**What would change our mind:** if one award needed several managers, `Award.manager` would become a many-to-many like `Award.staff`; `awards_for()` is the only rule to change.

---

## D10. Duplicate organisations and the staff check on each entry

**Date:** 15 Oct 2026 · Asked by the user: duplicates only under the awards they are actually in, finish the duplicate solution end to end, staff accept or decline entries, and the applicant should see judging move on

| Choice | Options | Picked | Why |
|---|---|---|---|
| Finding duplicates | A nightly job vs. on save | **On every profile save** (sign-up and profile form), plus a full scan from `seed_data` | Staff see a pair as soon as it exists; profiles are few, so comparing one against all is cheap |
| What counts as a match | GSTIN only vs. GSTIN, names | **High**: same PAN (GSTIN characters 3-12; one company has a GSTIN per state) or the same name once "Pvt Ltd" and punctuation are removed. **Possible**: name similarity ≥ 0.80 | GSTINs are unique per profile already, so an exact GSTIN never matches; PAN and names do |
| Which award tab shows a pair | Either record entered vs. both entered | **Both entered** that award; every other pair is on a *Not in the same award* tab | The request: show duplicates only on the tabs of the awards they are actually in; a pair only clashes in an award when both are there |
| What a merge does | Move entries to one login vs. link the records | **Link** (`merged_into`): both logins and their entries stay; conflicts and verification follow the main record | People keep their accounts; undo is one field; the conflict check (Rule 2) is what the merge is for |
| Two entries in one award | Merge anyway vs. block | **Block** until staff decline one (a *Decline as duplicate* button on the card) | One organisation enters an award once |
| Staff check per entry | Organisation verification only vs. also each entry | **Also each entry**: new status `accepted`; only accepted entries go to judges; declining needs a reason | The request; an entry can be ineligible even from a verified organisation |
| Accepting with an open duplicate | Allow vs. block | **Block** while an undecided duplicate also entered the same award | Forces the duplicate to be resolved before judges see either entry |
| Applicant progress | Status only vs. counts | **Counts only**: "1 of 3 judges finished · 1 reviewing now" | The applicant thought it was stuck on *Assigned*; counts say nothing about who judges or what they scored |

**What would change our mind:** if the client wants one login per company, a merge would move entries to the main account instead of linking records.

---

## D11. A results board for everyone; the award manager decides re-evaluations

**Date:** 15 Oct 2026 · Asked by the user: nobody could see results once they were out; make a screen where they can be seen and a re-evaluation asked for with a reason, approved by the award manager who reassigns judges, with the new result on the board

| Choice | Options | Picked | Why |
|---|---|---|---|
| Who sees what on the board | Everyone sees everything vs. by role | **By role**: staff and managers the full ranking of their awards, leaders every award, applicants the successful entries plus their own, judges the successful entries | Winners are public; another organisation's unsuccessful result isn't |
| When a result is "out" | Approved/rejected status vs. also judged | **Judged, then approved or rejected by a leader** | An entry declined at the staff check is also "rejected" but has no score; it isn't a result and can't be re-evaluated |
| Who approves a re-evaluation | Staff then leader (two steps, as before) vs. the award manager | **The award manager, one step**; a leader only if the award has no active manager | The request; the manager owns the award and chooses the new judges |
| After approval | Back to the general assign list vs. straight to choosing judges | **Straight to the assign page** for that entry; the first judges aren't offered (they are "Replaced") | One flow; fresh eyes |
| The new result | Updated automatically vs. decided again | **Decided again by leadership** (Approve results shows "Re-evaluation: new judges' scores · was …"); the board then shows the new score and result with "Re-evaluated · was …" | Results stay a leadership decision; the old judges' scores stop counting the moment the re-evaluation is approved |
| Duplicates blocking acceptance | Any open match vs. high matches only | **High matches only** (same PAN or same cleaned name); possible matches stay flagged | "Plant 1" and "Plant 2" look alike but are often different entries; found when the Postman run registered a second test company |

**What would change our mind:** if the client wants results public on the website, the board's applicant view (successful entries only) is the one to show.

---

## D12. Applicants' edit requests: staff check, then the award manager confirms

**Date:** 15 Oct 2026 · Asked by the user: an edit confirmation shouldn't go to leadership; staff check it first, then the award manager confirms, and only then can the applicant edit

| Choice | Options | Picked | Why |
|---|---|---|---|
| Final confirmation of an edit | A leader (D9) vs. the award manager | **The award's manager** | The request; the manager owns the award. Leaders no longer see edit requests |
| First step | Staff or the manager vs. staff only | **Staff on that award**; the manager only if the award has no active staff | Otherwise the manager could check and confirm the same request alone |
| Award without a manager | Stuck vs. a fallback | **A leader confirms** (the "Requests to confirm" page shows only these and judges' score changes) | A request must never be stuck; every award should have a manager anyway (the Awards page warns when it doesn't) |
| Judges' score changes | Also to the manager vs. unchanged | **Unchanged: staff check, a leader confirms** | Not part of the request; scores are Rule 3 and stay with leadership |
| Requests already checked by staff before this change | Leave with leaders vs. move | **Move**: they now wait for the award manager | The rule is computed from the request's kind and award, not stored |

---

## D13. Duplicate review is for programme staff; leaders have no "All applications" page

**Date:** 15 Oct 2026 · Asked by the user: remove *All applications* and *Duplicate review* from leaders and award managers

| Choice | Options | Picked | Why |
|---|---|---|---|
| Duplicate review | Hide the menu item vs. also refuse the page | **Menu item removed and the page refused (403)** for award managers and leaders; the service refuses them too | A hidden page that still works by URL isn't really removed. Staff on the award decide duplicates; managers still see the *Possible duplicate* badge on Entries |
| All applications (leaders) | Hide vs. delete | **Deleted** (view, address, template); the overview's "Open review queue" button now opens *Approve results* | Only leaders used it; scored entries are on *Approve results* and decided ones on the *Results board* |

---

## D14. Leaders only hear about what they decide; edit requests stay with staff

**Date:** 16 Oct 2026 · Asked by the user: applicants' edit notifications reached the leader; they should go to staff, only before judging; remove notifications from the leader panel that aren't for leaders, and let a leader open the ones that are and accept or reject there

| Choice | Options | Picked | Why |
|---|---|---|---|
| Why leaders still got edit notifications | — | Notifications created under the old staff → leader rule (copied to the live site), plus the D12 fallback for awards without a manager (DemoAward) | Both fixed below |
| Who is told about an edit request | The award's team vs. staff only | **The award's programme staff only** (its manager only if it has no staff); the manager is told when staff pass it on | The request; staff check first |
| Award with no manager | A leader confirms (D12) vs. the staff check decides | **The staff check decides**; leaders never take part in edits | The request |
| A judge starts while an edit request is open | Staff refuse it by hand vs. it closes itself | **It closes itself**: refused with "a judge has started judging", the applicant is told, the staff's reminder is cleared | Edits are only possible before judging |
| Old notifications | Leave vs. clean | **Data migration** deletes leaders' edit and old-rule re-evaluation notifications, and points their score-change notifications at the request's own page | Runs on the next deploy, so the live site is cleaned too |
| Opening a leader's notification | The general list vs. the one request | **The one request** (`/leadership/requests/score/<id>/`): reason, staff check, the judge's scores, Confirm / Refuse; "Already decided" once done | The request |

---

## D15. No Audit log page for leaders

**Date:** 16 Oct 2026 · Asked by the user: remove the audit log from the leader

| Choice | Options | Picked | Why |
|---|---|---|---|
| The page | Hide the menu item vs. remove the page | **Removed** (menu item, address `/leadership/audit/`, template); leaders were its only users | A hidden page that still opens by address isn't really removed |
| The audit trail itself | Stop recording vs. keep | **Kept**: every important action is still recorded (Rule 3 and the applicant's timeline depend on it) and stays read-only in `/admin/` for a superuser | Removing the page mustn't remove the record |

---

## D16. Leadership sees the whole event and approves each award's result as a whole

**Date:** 16 Oct 2026 · Asked by the user: leaders only see the results and a dashboard of how far each award has got, create awards and pick their manager, and approve the result of a whole award, not single applications

| Choice | Options | Picked | Why |
|---|---|---|---|
| The leader's pages | Many work queues vs. oversight only | **Overview, Awards and managers, People, Results board, Approve award results.** Requests to confirm, Re-evaluations, All applications, Duplicate review and the Audit log are gone (D13, D15) | The request |
| Who decides a single entry | The leader vs. the award manager | **The award manager** marks each scored entry Successful / Not successful (*Prepare results*); staff of an award without a manager do it | Leaders approve the event, not applicants |
| What a leader approves | Each entry vs. the award | **The award's result as a whole** (`Award.results_status`): sent by the manager once every entry is decided (nothing still with staff or judges); approve publishes it (`Application.result_published`), or send it back with a note | The request |
| When the applicant learns the result | When the manager decides vs. when leadership approves | **When leadership approves**: until then the applicant sees "Scored, waiting for the decision" (web and API), the board doesn't list it, and re-evaluation isn't possible | A provisional result mustn't leak |
| Judges' score changes | Leader confirms (D14) vs. the award manager | **Staff check, the award manager confirms** (staff alone if the award has no manager), like edits | Leaders are no longer in day-to-day decisions |
| Re-evaluations on an award without a manager | A leader (D11) vs. its staff | **Its programme staff** | Same reason |
| After a re-evaluation | Publish automatically vs. approve again | **The manager decides the entry again and sends the award's updated result; leadership approves it** | The result is always a leadership approval |
| Results decided before this change | Hide vs. keep | **Kept published** (data migration), their awards marked approved | Nothing disappears from the live board |

