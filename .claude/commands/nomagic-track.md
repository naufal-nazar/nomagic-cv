---
description: Update an application's status, or list what's due
argument-hint: "[application id] [draft|applied|callback|interview|offer|rejected|ghosted|withdrawn]"
---

Delegate to the **tracker** subagent.

- With an id and status: `python scripts/tracker.py status $ARGUMENTS`. `applied` also needs `--confirmed-submitted`; add it only when the candidate has told you they submitted the application. A submitted row goes back to `draft` only with `--not-submitted`, when the candidate says it was never actually sent; rows with an outcome never go back.
- Without arguments: `python scripts/tracker.py due`, then `python scripts/tracker.py list`.

For each follow-up due, offer a short, specific follow-up note drafted from `analysis.md` and the fact sheet.
