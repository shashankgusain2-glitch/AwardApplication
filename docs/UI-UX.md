# UI / UX

> **Status:** clickable screens with sample data. Buttons show a "demo" message instead of saving. Each screen switches to real data as its feature is built.

## Design principles

| User | What they need | How the design answers it |
|---|---|---|
| **Applicant** (once or twice a year, near a deadline, long form) | Not lose work; know how much is left | Auto-save message, progress bar, form split into sections, "Save and exit" |
| **Judge** (senior, short gaps) | Score fast, pick up where they left off | One list of assignments, 1–10 buttons instead of typing, progress per entry, saves as you go |
| **Programme staff** (daily) | See what needs doing today | "Today's to-do" home page, queues for entries and duplicates |
| **Leadership** (one view) | Spot problems across all awards | One table of every award, flags linking to a review queue |

The four rules are visible in the UI, not only enforced in the background:

| Rule | Where you see it |
|---|---|
| R1 Blind judging | Judge screens show "🔒 Hidden for blind judging" in place of identifying answers |
| R2 No conflicts | Assign-judges screen says how many judges were hidden because of a conflict; judges have a "Declare conflict" button |
| R3 Score audit | Judges are told every change after submit needs a reason; leadership approval shows how many changes were made |
| R4 Form versions | Form builder shows locked versions and version history; applicants see which version their entry used |

## Screen map

| Area | URL | Screens |
|---|---|---|
| **Public website** | `/` | Home, About us, Awards (with sector filter), Award detail, Log in |
| **Applicant** | `/applicant/` | Dashboard, Organisation profile, Application form, Application status |
| **Judge** | `/judge/` | My assignments, Score an entry |
| **Programme staff** | `/staff/` | My awards, Award settings, Form builder, Entries, Duplicate review, Assign judges |
| **Leadership** | `/leadership/` | Overview, Review queue, Approve results |

**Demo navigation:** the login page and every portal sidebar have a "view as" switch, so you can walk through each user's journey without logging in.

**Key demo screen:** *Programme staff → Award settings* shows the two awards side by side: Business Excellence (2 rounds, blind, 3 judges) and Kaizen (1 round, not blind, 2 judges). The difference is settings, not code.

## Style

- **Colours:** navy (trust, seriousness), gold (awards, achievement), teal (fairness promises and progress).
- **One stylesheet:** `static/css/main.css`, with colours and sizes as CSS variables at the top.
- **Accessible:** visible keyboard focus, labelled form fields, colour is never the only signal (badges always have text).
- **Responsive:** works on phones; the sidebar moves to the top on small screens.

## Host organisation

The public site is for a **fictional** industry body, *Udyog Excellence Council*. Its structure follows how real Indian industry bodies (e.g. CII) present awards: eligibility, step-by-step process, key dates, jury criteria and FAQs. The name, address and numbers live in one place (`apps/core/demo_data.py → ORGANISATION`) so they're easy to change.

## Where the sample data lives

`apps/core/demo_data.py`. Every view reads from it today. As each app's database models are built, its views switch to real queries and the matching sample data is deleted.
