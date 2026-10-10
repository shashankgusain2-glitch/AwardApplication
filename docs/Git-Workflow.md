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

## Merging a branch into `main`

Always merge with `--no-ff`. This keeps one **merge commit per branch**, so a whole feature can be undone in one step.

```bash
git switch main
git pull
git merge --no-ff feature/award-settings
git push origin main
```

After merging a milestone, add a **tag** (a named restore point):

```bash
git tag -a v0.3-award-settings -m "Award settings screen"
git push origin v0.3-award-settings
```

## Undoing changes

| I want to... | Command | Safe on `main`? |
|---|---|---|
| Undo **one commit** | `git revert <commit-id>` | ✅ Yes |
| Undo a **whole feature** (a merged branch) | `git revert -m 1 <merge-commit-id>` | ✅ Yes |
| Undo my **last commit that I haven't pushed** | `git reset --soft HEAD~1` (keeps the changes as uncommitted) | ✅ Yes, only before pushing |
| **Look at** an old version without changing anything | `git switch --detach <tag-or-commit-id>`, then `git switch main` to come back | ✅ Yes |
| Start a fix from an old version | `git switch -c fix/something <tag-or-commit-id>` | ✅ Yes |

`git revert` doesn't delete history. It adds a new commit that does the opposite, so the undo itself can also be undone.

**Never** use `git push --force` or `git reset --hard` on `main`. They erase history and can't be undone for anyone else.

**Watch out:** if a later commit builds on the one you revert (for example, the UI screens need the Django skeleton), git may report a conflict. Revert the later one first, or ask for help.

## Restore points (tags)

| Tag | Commit | What the project looked like |
|---|---|---|
| `v0.1-planning-docs` | `b6f639b` | User workflows, roadmap, git workflow (no code) |
| `v0.2-skeleton-ui` | `804d25b` | Django skeleton + clickable UI screens |

## History so far: how to undo each piece

| Commit | What it did | Undo with |
|---|---|---|
| `804d25b` | **Merge:** project skeleton + UI screens (all 4 commits below) | `git revert -m 1 804d25b` |
| `d8a51db` | Clickable UI screens | `git revert d8a51db` |
| `45b990a` | `.gitattributes` (line endings) | `git revert 45b990a` |
| `b5e74f6` | Django skeleton, architecture, test plan | `git revert b5e74f6` (revert `d8a51db` first) |
| `e467199` | Moved reports and meetings into `docs/` | `git revert e467199` |
| `b6f639b` | **Merge:** roadmap + git workflow guide | `git revert -m 1 b6f639b` |
| `7892761` | Git workflow guide | `git revert 7892761` |
| `2b9b810` | Product roadmap | `git revert 2b9b810` |
| `f3aea9f` | User workflows | `git revert f3aea9f` |

Commits before `f3aea9f` were made directly on `main` (daily reports, meeting notes). Each can still be undone with `git revert <commit-id>`. Run `git log --oneline` to see them.

## Commit messages

- Start with a verb: *Add*, *Update*, *Fix*, *Remove*.
- Say what changed: `Update roadmap: move payments to Phase 5`.
- One topic per commit.

## Rules

- Never commit directly to `main`. Use a branch and a Pull Request.
- Pull before starting work, so you don't build on an old version.
- Never commit passwords, keys, or real client data.
