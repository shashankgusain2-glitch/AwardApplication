"""
Judges, conflicts, assignments and scores.

Planned models:
- JudgeProfile: a user who can judge, with expertise areas.
- ConflictDeclaration: a judge's link to an Organisation.
  Assignment must never pair a judge with a conflicted entry.     [Rule 2]
- Assignment: one judge, one application, one round. Accept / decline / conflict.
- Score: one judge's score for one criterion.
- ScoreChange: append-only record of every change after submit —
  who, when, old value, new value, reason.                       [Rule 3]

Blind judging is applied when data is sent to a judge (server side),
not just hidden on screen.                                        [Rule 1]
"""
