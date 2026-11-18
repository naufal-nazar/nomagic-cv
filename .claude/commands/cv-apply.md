---
description: Tailor a CV, cover letter and screening answers to one job posting, check them, and log the application
argument-hint: "<posting URL or pasted text> [priority]"
---

You are the **Guide**. Use the `nomagic-cv` skill. Aim for minutes, not hours (R-SIGNAL-01).

1. Create `workspace/applications/<YYYY-MM-DD>-<company>-<role>/` and save the posting text as `posting.md`.
2. **researcher** subagent: write `analysis.md` (exact title, must-haves, nice-to-haves, repeated terms, likely screening questions, company context, and must-haves the candidate does not meet). Pick the closest role family.
3. Tell the candidate any unmet must-haves now (R-HONEST-06) and ask whether to continue.
4. **resume-builder** subagent: copy the family master to `cv.md`; change only the headline title, skills order, highlights and 2-3 bullets toward the must-haves. Draft `answers.md` from the fact sheet, and `letter.md` if the role is a priority.
5. Hooks run `fact_check.py` and `consistency_check.py` automatically. Fix by asking, never by inventing.
6. Export: `python scripts/export.py rendercv cv.md -o cv_rendercv.yaml` then `rendercv render cv_rendercv.yaml` (or the candidate's own .docx). The hook runs `parse_check.py` on the PDF/DOCX.
7. **reviewer** subagent checks the package; cross-model review if available.
8. **tracker** subagent: `python scripts/tracker.py add --company ... --role ... --family ... --cv-version ... --posting-date ... --folder <folder>`.
9. Hand everything to the candidate to review and submit themselves. Never submit.
