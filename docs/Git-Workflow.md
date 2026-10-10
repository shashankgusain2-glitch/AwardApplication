# Git Workflow

How changes get into this repository.

## Branches

| Branch | Purpose |
|---|---|
| `main` | Always the latest reviewed version. The reviewer reads this branch. |
| `docs/<topic>` | Documents: plans, workflows, decisions (e.g. `docs/roadmap`) |
| `feature/<topic>` | New code (e.g. `feature/award-settings`) |
| `fix/<topic>` | Bug fixes (e.g. `fix/blind-judging-leak`) |
| `report/<day>` | Daily reports (e.g. `report/day-7`) |

## Steps for every change

1. Start from the latest `main`:
   `git switch main` then `git pull`
2. Create a branch:
   `git switch -c docs/roadmap`
3. Make the change and commit with a clear message:
   `git commit -m "Add product roadmap"`
4. Push the branch:
   `git push -u origin docs/roadmap`
5. Open a Pull Request on GitHub into `main`, check the changes, then merge.
6. Delete the branch after merging.

## Commit messages

- Start with a verb: *Add*, *Update*, *Fix*, *Remove*.
- Say what changed: `Update roadmap: move payments to Phase 5`.
- One topic per commit.

## Rules

- Never commit directly to `main`. Use a branch and a Pull Request.
- Pull before starting work, so you don't build on an old version.
- Never commit passwords, keys, or real client data.
