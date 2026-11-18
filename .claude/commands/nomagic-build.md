---
description: Build or rebuild the master CV for one role family, then review it with fresh eyes
argument-hint: "[role family id, optional: all families if omitted]"
---

You are the **Guide**. Use the `nomagic-cv` skill.

1. Read `workspace/facts.yaml`. If it is missing, stop and suggest `/nomagic-start`.
2. For each role family in $ARGUMENTS (or all): `python scripts/versions.py init <family>`, then delegate to the **resume-builder** subagent to write `workspace/cvs/<family>/draft.md` in the candidate's writing mode.
3. The post-write hook runs `scripts/fact_check.py`. If it reports errors, the builder fixes them by asking the candidate, never by inventing.
4. Delegate review to the **reviewer** subagent. If `scripts/cross_review.sh` finds a second model CLI, run it too (R-AI-02).
5. Show the candidate the CV and the review in plain language: what changed, which rules (with grades) drove it, and what is theirs to decide.
6. The candidate approves line by line. Then freeze it: `python scripts/versions.py freeze <family> --note "<what changed and why>"`, which writes `<family>_v<N>_<date>.md` (read-only) and records it in `CHANGES.md`. Show `versions.py list`.
