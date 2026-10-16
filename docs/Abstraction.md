# Abstraction: what's shared, what changes, and where the model breaks

> **Status:** updated 16 Oct 2026 to match what is built. Written from the brief, the client meetings and the code; it will change as we learn more.

The brief's first point: *"The parts every award shares, the parts that change per award, and the point where your model breaks."*

**Our model in one sentence:** an award is a **shared engine** (apply → assign judges → score → decide) driven by **per-award settings**, where an **applicant fills a form** and **independent judges score it** against weighted criteria, over **one or two rounds**.

---

## 1. What every award shares (designed once, used by every award)

| Shared part | What it does | Where |
|---|---|---|
| **People and roles** | Applicant, Judge, Programme staff, Award manager, Leader; staff and managers only reach their own awards | `apps/accounts`, `apps/awards/access.py` |
| **Organisation profile** | One profile per organisation, keyed by GSTIN, reused for every award; verified by staff | `apps/accounts` |
| **Duplicate check** | Finds the same company under different names or GSTINs (same PAN, cleaned name, similar name); staff merge or keep separate | `apps/accounts/duplicates.py` |
| **Application lifecycle** | Draft → Submitted → Accepted for judging → Judges assigned → In review → Scored → result (published when leadership approves the award's result) | `apps/applications` |
| **Form engine** | Shows any form from its stored questions; saves section by section; remembers which version an entry used | `apps/awards`, `apps/entries` |
| **Judge assignment** | Never offers a conflicted judge; only the award's panel; spreads the load under each judge's limit, best priority first | `apps/assignments` |
| **Scoring engine** | Each judge scores alone; weighted total per judge; final score = average of judges | `apps/evaluations` |
| **Score change log** | Every change after submit records who, when, old value, new value and why | `apps/evaluations` |
| **Blind judging engine** | Removes identifying answers, the title and file names on the server, in desk-review rounds | `apps/assignments` |
| **Requests after submitting** | Edit and score-change requests: staff check, the award manager confirms; re-evaluation decided by the award manager | `apps/core/approvals.py`, `apps/applications` |
| **Award results** | The award manager decides each entry; leadership approves the award's result as a whole, which publishes it on the results board | `apps/awards/results.py`, `apps/core/results.py` |
| **Leadership view** | Every award's progress and result status in one table; award-level approval | `apps/dashboard` |
| **The 4 rules** | Hold for every award, whatever its settings | Everywhere, tested in `tests/rules/` |

What is real and tested is listed in [testing.md](testing.md); only the public marketing pages still use sample content.

## 2. What changes per award (settings staff control, no code)

| Setting | Business Excellence | Kaizen | Status |
|---|---|---|---|
| Round 1 type | Desk review | Desk review | ✅ Editable |
| Round 2 type | Live presentation | Site visit | ✅ Editable |
| Blind judging | On (desk review only) | Off | ✅ Editable, blocked if every round is in person |
| Judges per entry | 3 | 2 | ✅ Editable |
| Who applies | Organisation | Team | ✅ Editable |
| Award manager and staff | Chosen by leadership / the manager | Chosen by leadership / the manager | ✅ Per award (Team page) |
| Entry fee | None | None | ✅ Editable (amount only; no payment) |
| Closing date | 30 Nov 2026 | 15 Dec 2026 | ✅ Editable |
| Form questions | 12 indicators in 3 areas | Short before/after form | ✅ Editable in the form builder (programme staff); each publish is a new version |
| Which questions are hidden when blind | Name, location | Team, company, members | ✅ Editable per question in the form builder |
| Scoring criteria and weights | 30 / 30 / 40 | 25 each | ✅ Editable on the award's criteria page (weights add up to 100 per round) |
| Round 2 criteria | Story, evidence, answers | Seen working, team explains, kept going | ✅ Editable on the same page |
| Eligibility text, FAQs | Organisation rules | Team rules | 🟡 Stored per award |

---

## 3. Where the model breaks

These are the places where real awards don't fit the model above. For each: what breaks, how bad it is, and what we'd do.

### 3.1 On-site audits with no application form (5S, some shop-floor competitions)

- **The model assumes:** the applicant fills a form, and judges score that form.
- **Reality:** in a 5S audit, judges walk the shop floor with a checklist. The *judge* fills the form; the applicant barely writes anything.
- **What we do now:** rounds can be a *site visit*, blind judging is blocked for in-person rounds, and judges see visit details. But the scorecard is still the same criteria list.
- **What it would take:** a "judge checklist" round type: a form filled by the judge on site (works on a phone, maybe offline), with photos as evidence.
- **Severity:** 🔴 High for 5S; the brief itself warns these *"may not fit the usual 'fill a form, upload evidence' shape"*.

### 3.2 Blind judging can't reach inside files and photos

- **The model assumes:** hiding the identifying *answers* hides the applicant.
- **Reality:** a PDF has the company letterhead; a photo shows the factory sign or uniforms.
- **What we do now:** hide identifying answers and rename files. Staff are asked to check evidence for names.
- **What it would take:** applicants upload "anonymised" versions, or staff approve each file before judges see it.
- **Severity:** 🟠 Medium. Blind judging is only as good as the evidence.

### 3.3 Teams inside organisations (Kaizen)

- **The model assumes:** one applicant = one organisation; one entry per GSTIN per award.
- **Reality:** one company can send several Kaizen teams. The *team* applies, but the *company* matters for conflicts of interest.
- **What we do now:** "Who applies: Team" is a setting; the entry still links to the organisation, so conflict checks still work.
- **What it would take:** the "one entry per GSTIN" rule must become "one entry per team" for team awards, with a team table under the organisation.
- **Severity:** 🟠 Medium.

### 3.4 Many categories inside one award (the award with 38 categories)

- **The model assumes:** one award = one ranking, one set of judges.
- **Reality:** 38 categories in one cycle, each with its own winners and probably its own judges.
- **What would happen today:** we'd have to create 38 separate awards, losing the shared deadline and overview.
- **What it would take:** a *category* level under each award cycle, with judges and rankings per category.
- **Severity:** 🔴 High for that award.

### 3.5 Very large assessments (the 250-indicator, 15-area, 6-month award)

- **The model assumes:** judges score a handful of criteria, alone, and we average.
- **Reality:** a large award like this works more like CII's business excellence assessment: a *team* of assessors reviews together, visits the site, and agrees a **consensus** score, then a jury decides. There may be more than two stages (eligibility, report, site visit, jury).
- **What breaks:** "independent scores, then average" (consensus is different); "maximum 2 rounds"; scoring 250 indicators one by one on a single screen.
- **What it would take:** more than 2 rounds, a consensus scoring mode, and scoring grouped by area.
- **Severity:** 🔴 High for that award, and it's the biggest one. We left it out on purpose (see the Day 2 report).

### 3.6 Changing questions in the middle of a cycle

- **The model assumes:** the form is frozen once applications open; changes wait for next year (new version).
- **Reality:** staff may need to fix a mistake in a question while people are already filling it in.
- **What it would take:** a new version within the cycle, and a rule for drafts already started (keep their version, or move them over).
- **Severity:** 🟡 Low to medium. Rule 4 still holds (submitted entries keep their version).

### 3.7 How the final score is worked out

- **The model assumes:** final score = average of the judges' totals, from the last round.
- **Reality (open questions):** some awards may blend Round 1 and Round 2, drop the highest and lowest score, or break ties with a specific criterion.
- **What it would take:** a "final score method" setting per award.
- **Severity:** 🟡 Low to medium; it's a setting, once we know the rules.

### 3.8 Other edges we know about

| Edge | Why it doesn't fit yet |
|---|---|
| **Entry fees** | The amount is a setting, but there's no payment, refund or invoice flow |
| **Partner organisations** running awards with us | Who sees what, co-branding and data ownership aren't modelled |
| **Regional awards** | Region = location (confirmed), so each region is its own award; there's no roll-up across regions, which the client said isn't needed |
| **Appeals** | A re-evaluation can be asked once per entry (the award manager decides); other appeals, and a deadline for asking, aren't modelled |

---

## 4. How we decide: setting, new feature, or out of scope?

| If a difference between awards is... | Then it becomes... | Example |
|---|---|---|
| A choice among things the engine already does | A **setting** | Blind on/off, rounds, judges per entry |
| A new way of judging that several awards need | A **new round type or mode** in the shared engine | Judge checklist for site audits |
| Needed by only one award and very different | **Out of scope for now**, written down here | Consensus scoring for the 250-indicator award |

The test: **if adding an award needs a developer, the model has broken.** Every row in Section 3 is a place where that would happen today.

---

## 5. Summary

| | Count |
|---|---|
| Shared parts (designed once, used by every award) | 11 |
| Per-award settings editable today | 7 |
| Per-award content stored but not yet editable on screen | 5 |
| Known breaking points | 7 main + 4 edges |

Related: [decision D5](decisions/decision-log.md) (round types and blind judging), [Architecture.md](Architecture.md), [User-Workflows.md](User-Workflows.md).
