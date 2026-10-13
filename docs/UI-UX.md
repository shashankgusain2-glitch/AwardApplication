# UI / UX

> **Status (13 Oct 2026):** simplified to the applicant workflow only. Earlier clickable mock screens for judges, staff and leadership were removed to keep the build focused (they can be restored from git tag `v0.2-skeleton-ui`).

## Screens

| # | Screen | Who | What happens |
|---|---|---|---|
| 1 | Home | Everyone | Shows the 2 open events and one button: **Apply** |
| 2 | Verify email | Applicant | Enter work email → get a 6-digit code |
| 3 | Enter code | Applicant | Type the code → logged in (no password) |
| 4 | Register organisation | Applicant | Name, GSTIN, PAN of holder → checked, then saved once |
| 5 | Events | Applicant | The 2 events; **Apply**, **Continue the form** or **View status** |
| 6 | Application | Applicant | Short form; **Save and finish later** or **Submit**; status tracker; **Ask staff to allow changes** |
| 7 | Staff | Staff | Approve or decline edit requests; move reports along the status |

## Principles

- **One clear next step on every page.** Steps are numbered "Step 1 of 4" to "Step 4 of 4".
- **Never lose work.** The form can be saved with gaps; required questions are checked only on submit.
- **Short forms for starters.** 5 questions per event.
- **Locked after submit.** Changes need staff to agree, as decided in the 12 Oct meeting.
