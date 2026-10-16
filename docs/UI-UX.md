# UI / UX

> **Status (16 Oct 2026):** every portal screen runs on the real database. Only the public marketing pages (home, about, award catalogue text) still use sample content from `apps/core/demo_data.py`. The first version (11 Oct) was a clickable mock-up with sample data; it was replaced screen by screen in step 3.5.

## Design principles

| User | What they need | How the design answers it |
|---|---|---|
| **Applicant** (once or twice a year, near a deadline, long form) | Not lose work; know where things stand | Form split into sections that save as you go, a progress bar, a status timeline with dates and judging progress ("1 of 3 judges finished"), the results board |
| **Judge** (senior, short gaps) | Score fast, pick up where they left off | One list of assignments, Accept / Decline, 1–10 per criterion, save midway, progress per entry |
| **Programme staff** (daily) | See what needs doing today | A home page of counts (organisations to verify, entries to accept, possible duplicates, entries needing judges, requests to check) that link to the work |
| **Award manager** (owns one or more awards) | Set the award up and close it out | Award pages with a set-up checklist, "Waiting for you to confirm" on Entries, *Prepare results* with one button to send the award's result |
| **Leadership** (one view) | See how every award is going and approve results | One overview table of every award and its result status; *Approve award results* shows each award's ranking with Approve / Send back |

The four rules are visible in the UI, not only enforced in the background:

| Rule | Where you see it |
|---|---|
| R1 Blind judging | Judge screens show "🔒 Hidden for blind judging" in place of identifying answers; file names are neutral; the score page says when a round isn't blind (site visit, live presentation) |
| R2 No conflicts | The assign-judges page only offers eligible judges and says how many conflicts are recorded for the organisation |
| R3 Score audit | After submitting, a judge asks to change a score with a reason; the change history shows who, when, old and new value |
| R4 Form versions | The form builder shows each version as read-only, with how many applications use it; applicants see which version their entry used |

## Screen map

| Area | URL | Menu |
|---|---|---|
| **Public website** | `/` | Home, About us, Awards (with sector filter), Award detail, Log in, Sign up |
| **Applicant** | `/applicant/` | Dashboard, Organisation profile, Application form, Application status, Results, Notifications |
| **Judge** | `/judge/` | My assignments, Score an entry, Results, Notifications |
| **Programme staff** | `/staff/` | My awards, Awards, Award settings, Form builder, Entries, Duplicate review, Assign judges, Prepare results (view), Re-evaluations (view), Results, Notifications |
| **Award manager** | `/staff/` (their awards only) | My awards, Awards and teams, Award settings, Entries, Assign judges, Prepare results, Re-evaluations, Results, Notifications |
| **Leadership** | `/leadership/` | Overview, Awards and managers, Approve award results, Results board, People, Notifications |

Each role only sees its own menu; any other role's page answers **403 Access denied**, and another user's record answers **404**. Staff and award managers only see the awards they are on.

**Award settings** (staff and managers) is an older screen that edits the two demo awards side by side; the award's own page (*Details and rounds*) edits any award, including new ones. Retiring the older screen is planned (R8).

## Style

- **Colours:** navy (trust, seriousness), gold (awards, achievement), teal (fairness promises and progress).
- **One stylesheet:** `static/css/main.css`, with colours and sizes as CSS variables at the top.
- **Accessible:** visible keyboard focus, labelled form fields, colour is never the only signal (badges always have text).
- **Responsive:** works on phones; the sidebar moves to the top on small screens. A full accessibility and phone pass is planned (R10).

## Host organisation

The site is called **Awards Platform** (a demo name, not a real organisation). Its structure follows how real Indian industry bodies (e.g. CII) present awards: eligibility, step-by-step process, key dates, jury criteria and FAQs.

## Where the sample content lives

`apps/core/demo_data.py` now only feeds the public marketing pages and the portal menus (`PORTAL_NAV`). Moving the public pages to the `Award` table is planned (R8).
