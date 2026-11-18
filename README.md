# NoMagicCV

**No magic. No myths. Just evidence.**

Most AI CV tools promise magic: instant ATS scores, "75% of CVs are rejected by robots", one-click perfection. NoMagicCV does the opposite. It brings the best open-source CV tools under one roof, checks every fact against your own records with code, and follows only rules backed by named, graded research. *The only magic is the receipts.*

An open-source AI resume & CV builder agent: the Evidence-Based CV Framework packaged as an [Agent Skill](https://agentskills.io) with slash commands, subagents and hooks for Claude Code, Codex and other coding agents. Field-agnostic, ATS-friendly, private by default.

> The "7-second scan" comes from one vendor eye-tracking study (Ladders, grade C). We design the top third for a fast scan and say how strong the evidence is.

## Why this exists

AI CV tools write fast and invent freely. This one treats your CV like code under test:

| | What it does | Enforced by |
|---|---|---|
| 🧾 **Facts checked by code** | Every title, date, number, tool and credential traces to your `facts.yaml`. Invented facts fail the build. | `scripts/fact_check.py` + hook |
| 📚 **Checkable rules** | Every rule has an id, a grade (A/B/C) and a named study. No study, no hard rule. | `rules/rules.yaml`, `scripts/rules_lint.py` in CI |
| 🔍 **Independent review** | A reviewer that never saw the drafting, ideally on a different model family, because LLMs prefer CVs they wrote ([Xu, Li & Jiang, AIES 2025](https://doi.org/10.1609/aies.v8i3.36755)). | `reviewer` subagent, `scripts/cross_review.sh` |
| 🧩 **One version of the truth** | CV, cover letter, LinkedIn and screening answers state the same years, dates and contacts. | `scripts/consistency_check.py` + hook |
| 🤖 **Parse test** | See what an ATS extracts from your PDF/DOCX, and whether anything went missing or out of order. | `scripts/parse_check.py` + hook |
| 📈 **Honest statistics** | Callback rates per CV version with 95% intervals. It won't crown a winner from 20 applications. | `scripts/tracker.py stats` |
| 🧪 **Public benchmark** | Fabrication rate and must-have coverage across models on fictional candidates. | `evals/` |
| 🔒 **Private by default** | Your data stays in `workspace/` (gitignored), and a pre-commit hook blocks it from being pushed. | `scripts/git-hooks/pre-commit` |

## The evidence, in one table

| Finding | Source | Grade |
|---|---|---|
| Better-written CVs get ~8% more hires | Wiles, Munyikwa & Horton (NBER; Management Science 2025) | A field |
| Spelling errors hurt as much as missing experience | Lacroux & Martin-Lacroux (2016) | A lab |
| Plain words read as more intelligent | Oppenheimer (2006) | A lab |
| Referrals raise hiring odds | Burks et al. (QJE 2015) | A field |
| Longer unemployment lowers callbacks | Kroft, Lange & Notowidigdo (QJE 2013) | A field |
| Local experience nearly doubles immigrant callbacks (5.9% to 11%) | Oreopoulos (AEJ: Policy 2011) | A field |
| Identity cues and AI rankers affect callbacks | Kang et al. (ASQ 2016); Wilson & Caliskan (AIES 2024) | A |
| AI screeners prefer AI-written CVs (68-92%) | Xu, Li & Jiang (AIES 2025) | A lab |
| Tailored cover letters: 16.4% vs 10.7% callbacks | ResumeGo | B |
| Two pages preferred for experienced candidates | ResumeGo | B |
| 56% of applications arrive in 96 hours | St. Louis Fed | B |

Full table, myths and links: [`references/evidence.md`](skills/nomagic-cv/references/evidence.md) · [`references/myths.md`](skills/nomagic-cv/references/myths.md) · [`rules/sources.yaml`](rules/sources.yaml)

## How it works

You run a few commands. A Guide hands each step to a specialist subagent. Everything is saved as files, so any agent can pick up where the last one stopped.

```
/cv-start  ─► Career Consultant interviews you ─► workspace/facts.yaml (you approve)
/cv-build  ─► Resume Builder writes a master CV per role family ─► Reviewer checks it
/cv-apply  ─► Researcher decodes the posting ─► Builder tailors ─► Reviewer ─► Tracker logs it
/cv-check  ─► every check on a file or folder, with rule ids and grades
/cv-track  ─► status updates and follow-ups
/cv-review ─► callback rates with uncertainty, and one change to test next
```

| Hook | When | What it does |
|---|---|---|
| SessionStart | session opens | Shows follow-ups due and the next step |
| PreToolUse | before `facts.yaml` changes | Asks you; only you change the truth |
| PostToolUse | after a CV, letter or answers file is written | Runs fact and consistency checks; errors go back to the agent to fix |
| PostToolUse | after a PDF/DOCX export | Runs the parse test against the source |
| Stop | before the agent finishes | Blocks while an application folder is untracked |

Hooks only trigger. The scripts do the checking, so Codex and Claude Code get the same checks.

## Quick start

```bash
git clone https://github.com/naufal-nazar/nomagic-cv.git
cd nomagic-cv
make setup        # deps, privacy hook, workspace folders
claude            # or: codex
> /cv-start       # Codex: "run cv-start"
```

Requirements: Python 3.10+. Optional: [RenderCV](https://github.com/rendercv/rendercv) for PDFs (`pip install "rendercv[full]"`), `pdftotext` (poppler) for the parse test.

**Claude Code**: commands, subagents and hooks load from `.claude/`. **Codex**: reads `AGENTS.md` and the skill from `.agents/skills/`; see [`adapters/codex`](adapters/codex/README.md) to enable hooks. **Other agents**: point them at `AGENTS.md`.

## Your CV, with receipts

CVs are Markdown with provenance tags that are stripped on export:

```markdown
### Data Analyst, Acme Retail, Toronto, ON | Mar 2021 - Present <!-- role:acme -->
- Built weekly demand forecasts for ~40 stores in SQL and Python. <!-- f:acme.r1 -->
```

Change "40" to "60", rename the title to "Senior Data Analyst" or drop the "~" on a number you marked approximate, and the check fails:

```
ERROR  cv.md:11  [R-HONEST-01] Number '60' is not in the cited fact(s) ['acme.r1'].
ERROR  cv.md:10  [R-HONEST-02] Role line must start with the official title and employer exactly: 'Data Analyst, Acme Retail'.
ERROR  cv.md:11  [R-HONEST-03] '40' is approximate in facts; write it as '~40' or 'about 40'.
```

Export when it passes: `python scripts/export.py rendercv cv.md -o My_CV.yaml && rendercv render My_CV.yaml`, or `export.py jsonresume` for Reactive Resume and other JSON Resume tools.

## Design decisions

- **The candidate runs it** and approves every line. The agent never submits.
- **Editor mode by default** (you draft, it tightens); author mode is opt-in, with the evidence on both sides shown.
- **Official titles only** in role lines; the target title lives in the headline.
- **Approximate numbers** only if you'd defend them in an interview, marked as approximate.
- **Same rules everywhere**; most evidence is North American and European, and we say so.
- **One master per role family**, quick tailoring per posting: speed matters (56% of applications arrive in 96 hours).

## Works with

[RenderCV](https://github.com/rendercv/rendercv) (PDF rendering) · [JSON Resume](https://jsonresume.org) (import/export) · [Reactive Resume](https://github.com/amruthpillai/reactive-resume) (visual editing via JSON Resume) · [OpenResume](https://github.com/xitanggg/open-resume) (second parse test, run separately). See [`CREDITS.md`](CREDITS.md).

## Limits, honestly

- The fact check catches numbers, titles, dates, skills and credentials. It does not catch a claim written in words ("led the team") that the facts don't support; the reviewer does that, and so do you.
- Most studies come from North America and Europe.
- Grade C rules are marked `test`: worth trying, not proven.
- Not legal or career advice. You are responsible for what you send.

## Contributing

New rules need a cited study with its sample size and a grade; grade C can't become a hard rule. See [`CONTRIBUTING.md`](CONTRIBUTING.md). Run `make check` before opening a PR.

## License

Code: [MIT](LICENSE). Framework text (skill, references, rules): [CC BY 4.0](LICENSE-CONTENT). Third-party tools keep their own licenses.
