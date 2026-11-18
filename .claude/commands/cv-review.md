---
description: See which CV versions get callbacks, with honest uncertainty, and pick one change to test next
argument-hint: "[role family, optional]"
---

1. **tracker** subagent: `python scripts/tracker.py stats` (add `--family <family>` if the candidate named one: $ARGUMENTS).
2. Explain the table in plain words. If intervals overlap or any version has fewer than 30 applications, say clearly there is no winner yet (R-MEASURE-01).
3. **career-consultant** subagent suggests exactly one element to change next (headline, summary, highlights order, or a bullet), with the rule id and grade behind it.
4. Remind the candidate that signals outside the CV (referrals, applying early) have stronger evidence than most wording changes.
