---
description: Run every check on a CV file or application folder and explain the results with rule ids and grades
argument-hint: "<cv.md | application folder | cv.pdf>"
---

Delegate to the **reviewer** subagent with $ARGUMENTS:

- `.md` CV: `python scripts/fact_check.py <file>`
- application folder: `fact_check.py <folder>/cv.md` and `python scripts/consistency_check.py <folder>`
- `.pdf` / `.docx`: `python scripts/parse_check.py <file> [--source cv.md]`

Then the reviewer's own pass against `rules/rules.yaml`. Report errors first, then `test`-strength suggestions labelled as such.
