# postman/

**Ready-to-import Postman files for the REST API (roadmap step 3.4).**

| File | What it is |
|---|---|
| `Awards-Platform.postman_collection.json` | 123 requests in 12 folders (one per module), each with tests |
| `Awards-Platform.postman_environment.json` | `base_url`, the demo account emails, and an empty `demo_password` |
| [CHECKLIST.md](CHECKLIST.md) | Every request in run order: endpoint, method, role, expected status, a Pass/Fail box |
| `build_collection.py` | Makes the three files above. Edit its `REQUESTS` list, then run it again |

## How to use it

1. Start the app and load the demo data (see [docs/Setup.md](../docs/Setup.md)).
2. In Postman: **Import** both JSON files, then choose the **Awards Platform (local)** environment.
3. In that environment, set **`demo_password`** to the `DEMO_PASSWORD` value from your `.env`. It is left blank on purpose so the password is never saved in the repository.
4. Click the collection → **Run** (Collection Runner) and run it **top to bottom**. You can run it again; every run signs up a fresh applicant.

Or from a terminal, with Newman (Postman's command-line runner):

```bash
npx newman run postman/Awards-Platform.postman_collection.json -e postman/Awards-Platform.postman_environment.json --env-var demo_password=YOUR_DEMO_PASSWORD
```

## What a run does

The requests tell one story on the seed data, so later requests use ids saved by earlier ones:

1. **Auth**: log in as each role (tokens and user ids saved automatically), sign up a new applicant, me, refresh, logout.
2. **Users**: a leader creates, renames, deactivates and reactivates a judge.
3. **Profiles**: the new applicant adds a GSTIN; staff verify the organisation.
4. **Awards**: read the Kaizen form; its questions are turned into answers for step 5.
5. **Applications**: the applicant creates, answers and submits an application.
6. **Assignments**: staff assign judge Kapoor, bulk-assign a third judge, then reassign that one to judge Rao. Both judges accept.
7. **Evaluations**: both judges score and submit, so the report becomes **scored**. Kapoor asks to change a score, staff allow it, and the change is recorded with a reason.
8. **Decisions**: a leader approves the result.
9. **Conflicts**, 10. **Dashboards**, lookups and notifications, 11. **Logout**.

Every request checks its **status code** and that the body is `{success, data, message, errors}`. The negative tests sit next to the happy path:

- **No token** → 401
- **Wrong role** → 403 (for example, a judge listing applications, or staff creating accounts)
- **Wrong role on the login form** → 401
- **Another judge's report** → 404 (the API doesn't even admit it exists)
- **Invalid payload** → 400 (a bad GSTIN, a score of 11, a score of `true`, a missing award, a bad status)

## Rate limit

Login and sign-up are limited per minute. Local development allows 60 a minute (`THROTTLE_LOGIN_DEV`), so a full run fits. Production keeps 10 a minute.
