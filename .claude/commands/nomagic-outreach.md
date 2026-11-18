---
description: Find employer contacts, draft fact-checked outreach, and send it in semi-auto (drafts) or auto mode
argument-hint: "[application folder or target, e.g. 'clinical research sites in Toronto']"
---

You are the **Guide**. Follow `skills/nomagic-cv/references/outreach.md`.

1. Read `preferences.outreach` in `workspace/facts.yaml` (mode, daily cap, phrases to avoid). If it's missing, ask the candidate for their mode (semi-auto is the default) and tone preferences, and show them the suggested settings to add.
2. Contacts, strongest first: people the candidate knows or who can refer them (`outreach.py add --basis referral|existing-relationship`), the posting's named contact (`--basis posting-contact`), then organisations' own published addresses. For the last, if the candidate has a Google Maps scraper export (gosom or the kit), import it: `python scripts/outreach.py import <file> --source gosom|kit`. Then `outreach.py verify`.
3. Confirm the list with the candidate before writing anything.
4. For each contact, `outreach.py new <id> --type intro|referral|followup [--application <folder>]`, then write the message from the fact sheet and the application's `analysis.md`. Delegate drafting to **resume-builder** and review to **reviewer**.
5. `python scripts/outreach.py lint <message>`. Fix by asking, never by inventing.
6. Semi-auto: create a draft in the candidate's mailbox with the email connector, then `outreach.py mark <message> --drafted`. Auto: `outreach.py send <message>` (the pre-send hook also gates MCP send tools).
7. Summarise what was drafted or sent, and when follow-ups fall due (`outreach.py due`).
