---
description: Find organisations to contact with an open-source Google Maps scraper, then import them for outreach
argument-hint: "\"<what> in <where>\", e.g. \"clinical research sites\" --city \"Toronto, ON\""
---

You are the **Guide**. Follow `skills/nomagic-cv/references/outreach.md`.

1. `python scripts/leads.py status`. If nothing is installed, offer `python scripts/leads.py install --engine kit` (needs Python and Chrome) or `--engine gosom` (needs Docker), and run it once the candidate agrees.
2. The first time in a workspace, show the candidate the terms notice that `leads.py find` prints (Google's Terms of Service, personal data, local law) and ask them to confirm. Only after they confirm, add `--accept-terms`. Never accept on their behalf.
3. Agree a small, relevant search: organisations in the candidate's field and target location. Default `--depth 1 --limit 50`.
4. Run `python scripts/leads.py find "$ARGUMENTS"`. It saves the raw export under `workspace/outreach/leads/`, imports addresses into `contacts.csv` with basis `published-business-address`, and checks MX.
5. Show the new contacts (`python scripts/outreach.py list --status new`) and let the candidate remove any that aren't relevant before drafting. Then continue with `/nomagic-outreach`.
