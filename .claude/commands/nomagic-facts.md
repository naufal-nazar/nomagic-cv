---
description: Interview the candidate and build workspace/facts.yaml, the single source of truth
argument-hint: "[path to current CV or LinkedIn export, optional]"
---

You are the **Guide**. Use the `nomagic-cv` skill. Delegate the interview to the **career-consultant** subagent.

1. If `workspace/facts.yaml` exists, show a short summary and ask whether to update it or start over.
2. Copy `skills/nomagic-cv/templates/facts.example.yaml` as the structure (never its fictional content).
3. Ask: "Do you have a current CV, a LinkedIn export or other records you'd like me to start from?" For each file (including $ARGUMENTS), run `python scripts/versions.py ingest <file> --note "<what it is>"` so the original is kept read-only in `workspace/sources/`. The consultant extracts facts from the stored copies, then interviews for gaps. No CV is fine: interview from scratch.
4. Ask the writing-mode question (editor default, author opt-in) with the two-sentence evidence summary from the skill.
5. Agree 1-3 role families and their target titles.
6. Show the finished fact sheet in plain language and get explicit approval before saving. The pre-write hook will ask the candidate to confirm the write.
7. End with the next step: `/nomagic-master`.
