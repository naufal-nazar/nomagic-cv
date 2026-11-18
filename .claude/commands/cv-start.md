---
description: Interview the candidate and build workspace/facts.yaml, the single source of truth
argument-hint: "[path to current CV or LinkedIn export, optional]"
---

You are the **Guide**. Use the `nomagic-cv` skill. Delegate the interview to the **career-consultant** subagent.

1. If `workspace/facts.yaml` exists, show a short summary and ask whether to update it or start over.
2. Copy `skills/nomagic-cv/templates/facts.example.yaml` as the structure (never its fictional content).
3. If the candidate gave a file ($ARGUMENTS), have the consultant extract facts from it first, then interview for gaps.
4. Ask the writing-mode question (editor default, author opt-in) with the two-sentence evidence summary from the skill.
5. Agree 1-3 role families and their target titles.
6. Show the finished fact sheet in plain language and get explicit approval before saving. The pre-write hook will ask the candidate to confirm the write.
7. End with the next step: `/cv-build`.
