# tests/rules/

**One test file for each of the four rules in the brief.**

| File | Rule | Status |
|---|---|---|
| `test_rule1_blind_judging.py` | A judge can't see who applied in a blind award (desk-review rounds only) | ✅ Running (1 planned) |
| `test_rule2_conflict_of_interest.py` | A judge is never given a report they have a conflict with; staff record conflicts | ⏳ Planned |
| `test_rule3_score_audit.py` | Every score change records who, when and why | ⏳ Planned |
| `test_rule4_form_versions.py` | Old applications still open with their own questions | ⏳ Planned |

The brief asks for *"tests written from the four rules"*. Keeping one file per rule lets a reviewer see each rule's checks in one place.
