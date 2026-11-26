---
description: The daily routine, safe to run unattended - inbox replies, due follow-ups, stale applications, one report
---

You are the **Guide**, possibly running unattended (scheduled). Nobody may be watching, so:
never edit `workspace/facts.yaml`, never freeze CV versions, never submit applications, never mark a draft as applied, never accept
lead-finder terms, and never send anything outreach rules don't allow. When something needs the
candidate, write it in the report as a question instead of guessing.

1. Context: `python scripts/tracker.py due`, `python scripts/outreach.py due`, `python scripts/versions.py list`.
2. Inbox (only if an email connector or MCP server is available): follow `/nomagic-inbox` for the last 3 days.
   Scan every reply with `posting_guard.py`; record each with `outreach.py reply` and update `tracker.py status`.
3. Follow-ups due: for each, `outreach.py new <id> --type followup`, write it from the fact sheet and the earlier
   message, `outreach.py lint`. Semi-auto mode: create drafts only. Auto mode: `outreach.py send` (the cap and
   the pre-send hook still apply). Applications due a follow-up in the tracker: draft a short follow-up too.
4. Hygiene: untracked application folders (`tracker.py check-complete`), drafts with unfrozen changes,
   applications with no reply after 21 days (suggest marking them ghosted; don't change them).
5. Write `workspace/reports/<YYYY-MM-DD>_daily.md`: replies and how they were recorded, drafts created,
   messages sent, follow-ups coming up, questions for the candidate. Keep it under one screen.
