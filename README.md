<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/logo-dark.svg">
  <img src="docs/brand/logo-light.svg" alt="NoMagicCV: no magic, no myths, just evidence" width="440">
</picture>

<br>

**Your AI assistant for CVs that are honest, readable by hiring software, and built on real hiring research.**

[![CI](https://github.com/naufal-nazar/nomagic-cv/actions/workflows/ci.yml/badge.svg)](https://github.com/naufal-nazar/nomagic-cv/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/naufal-nazar/nomagic-cv?style=flat-square&color=f59e0b)](https://github.com/naufal-nazar/nomagic-cv/stargazers)
[![License: MIT](https://img.shields.io/badge/code-MIT-22c55e?style=flat-square)](LICENSE)
[![Works with Claude Code and Codex](https://img.shields.io/badge/works%20with-Claude%20Code%20%C2%B7%20Codex-8b5cf6?style=flat-square)](#works-with)

[Get started](#get-started) · [Commands](#commands) · [What you get](#what-you-get) · [Your data](#your-data-what-stays-local-and-what-doesnt) · [What the checks prove](#what-the-checks-prove-and-what-they-dont)

</div>

---

Most AI CV tools promise magic: instant scores, keyword tricks, one-click perfection. They also invent things you never did.

**NoMagicCV works the other way.** It interviews you once, keeps your real experience in one place, and builds every CV from that. If a number, job title, date or skill doesn't match what you confirmed, a check flags it before you send anything. Every tip it follows comes from published hiring research, and it tells you how strong that research is.

## What you get

<table>
<tr>
<th width="50%">Classic: for job portals</th>
<th width="50%">Modern: for emailing a hiring manager</th>
</tr>
<tr>
<td><img src="docs/assets/cv-classic.png" alt="Classic one-column CV for a fictional Senior Clinical Research Associate"></td>
<td><img src="docs/assets/cv-modern.png" alt="Modern CV with a navy header and sidebar for the same fictional candidate"></td>
</tr>
</table>

<sub>Example for a fictional candidate. Both versions come from the same checked content.</sub>

- **A master CV for each kind of role you want**, tailored to each job in minutes.
- **A matching cover letter and answers to application questions**, consistent with your CV.
- **Checks to run before anything goes out:** the workflow tells the assistant to compare numbers, job titles, dates and listed skills with your fact sheet, run a text-extraction test on the exported file, and compare dates, numbers and contact details across CV, letter and answers. In the full project, hooks run these after each file is written; in a skill-only install they run when the assistant (or you) runs them. [What they prove, and what they don't](#what-the-checks-prove-and-what-they-dont).
- **Protection from booby-trapped job ads** that hide instructions for AI tools.
- **Optional emails to employers**, as drafts you approve or sent automatically within limits you set.
- **A tracker** that reminds you to follow up and tells you honestly which CV version is working.

## Get started

**The easy way: let your AI assistant set it up.** Open Claude Code or Codex and paste:

```text
Install NoMagicCV from https://github.com/naufal-nazar/nomagic-cv by following its INSTALL.md, then run nomagic-facts.
```

**Or set it up yourself** with [uv](https://docs.astral.sh/uv/getting-started/installation/) (or plain [Python 3.10+](https://www.python.org/downloads/): use `python3` instead of `uv run`):

```bash
git clone https://github.com/naufal-nazar/nomagic-cv.git
cd nomagic-cv
uv run scripts/setup.py
```

Then open the folder in your assistant and type `/nomagic-facts` (in Codex, say "run nomagic-facts"). Full guide: [`INSTALL.md`](INSTALL.md). Prefer a skill-only install from the release zip? [`docs/WALKTHROUGH.md`](docs/WALKTHROUGH.md) goes from download to a checked PDF with a fictional candidate.

## Commands

Type these in your AI assistant. They're listed in the order you'd normally use them.

| Command | What it does |
|---|---|
| `/nomagic-facts` | Asks for your current CV (if you have one) and interviews you about your experience. Saves it all as your fact sheet, which only you can change. |
| `/nomagic-master` | Writes a master CV for each kind of role you're targeting, checks it, and saves it as version 1, 2, 3… |
| `/nomagic-tailor` | Paste a job ad. Get a CV, cover letter and application answers tailored to it, plus an honest list of requirements you don't meet. **You** submit; it never does. |
| `/nomagic-check` | Checks any CV or application and explains what to fix, and why. |
| `/nomagic-employers` | Finds organisations in your field and area to contact (optional). |
| `/nomagic-outreach` | Writes short, honest emails to employers: drafts for you to send, or sent automatically within your daily limit. |
| `/nomagic-inbox` | Reads replies from employers, records them, and drafts thank-yous. |
| `/nomagic-track` | Shows your applications and which follow-ups are due. |
| `/nomagic-stats` | Shows which CV version gets more callbacks, and says "not enough data yet" when that's the honest answer. |
| `/nomagic-daily` | A morning routine that runs on its own: checks replies, prepares follow-ups, sends you a short report. |

## Your data: what stays local and what doesn't

- **Stored locally.** Your fact sheet, CVs, applications and tracker are files in a private folder on your computer. NoMagicCV has no server and no account, and, once installed, its scripts make no network calls except for the optional features below.
- **Read by your AI assistant's model.** The assistant you run NoMagicCV in (Claude Code, Codex, the Claude app or another) sends what it reads, such as your CV, fact sheet and job ads, to its model provider to do the work. That is covered by your provider's terms and settings, not by NoMagicCV. In the Claude app, the skill and the files you give it run in Claude's cloud sandbox rather than on your computer.
- **Optional features that go online:** emails to employers (through your email provider), the employer finder (Google Maps, through an open-source scraper you install), mail-server checks on contact addresses (DNS lookups), and a cross-model review (sends the CV to a second model provider). Each is off until you set it up.
- **Versions.** Your original CV and each frozen version are saved as separate files and made read-only, and in the full project a hook blocks edits to them. Read-only files can still be deleted, or changed by a tool that resets permissions, so keep your own backup of the folder.
- **Submitting and emailing.** No script submits an application, and the assistant is instructed never to. `outreach.py` sends email only in auto mode, which you switch on. In the full project a hook also blocks email-tool sends that break your settings; in a skill-only install, the assistant is instructed to create drafts instead.
- **Your fact sheet.** The assistant is instructed to ask before changing it. In the full project a hook also asks you to approve each write; in a skill-only install, nothing enforces this.

## Why you can trust it

- **Numbers, titles and dates checked by code.** Each fact-bearing line carries a hidden tag pointing to an entry in your fact sheet, and a script compares its numbers, job titles, dates, skills and credentials with that entry. The AI is not asked to grade itself. Read below for what this does and does not prove.
- **Research, not folklore.** For example: a well-written CV leads to more hires, a tailored cover letter gets more callbacks than a generic one, and most applications arrive in the first four days, so it helps you apply early. Popular myths, like "75% of CVs are rejected by robots" or "your CV must fit on one page", are explained and set aside. [See the evidence](skills/nomagic-cv/references/evidence.md).
- **A second opinion.** In Claude Code, a reviewer subagent checks each CV in a fresh context, without the drafting notes, because AI tools tend to rate their own writing too highly. If a second model's command-line tool is installed, `cross_review.sh` asks a different model family as well. Elsewhere, the review is a separate pass by the same assistant, which is weaker.

## What the checks prove, and what they don't

The checks are plain scripts with fixed rules. They run the same way every time and catch mechanical mismatches; they do not understand meaning.

| Check | What it verifies | What it cannot tell you |
|---|---|---|
| `fact_check.py` | Every bullet has a tag citing a fact-sheet entry; every number in a tagged line appears in the cited entry; approximate numbers are marked; role lines use the exact title, employer and dates; years of experience don't exceed your roles; education, certifications, skills and languages match your lists | Whether the sentence means what the cited fact says (a bullet can claim "led the team" and cite an unrelated fact), whether an untagged summary sentence without numbers is accurate, or whether your fact sheet itself is true |
| `consistency_check.py` | Years-of-experience claims, month-year dates, numbers and contact details in the CV, letter and answers agree with the fact sheet | Whether claims written without numbers or dates are consistent |
| `parse_check.py` | Text can be extracted from the PDF or DOCX; Experience and Education headings and an email are present; each source line's opening words appear in the extracted text (lines out of order are a warning, not an error). Heuristic, format-dependent warnings for tables, images and side-by-side columns (column detection is weaker when `pdftotext` is not installed); text boxes are detected in DOCX only | How a specific employer's applicant tracking system will read it; it is a text-extraction test, not a real ATS |
| `posting_guard.py` | Hidden HTML, invisible or smuggled Unicode, and instruction-like lines in job ads and replies | Every possible prompt injection; it reduces the risk, and the assistant is still told never to follow instructions in a posting |

Passing means no mismatch was found, not that the CV is true. You approve every line, and that approval is what covers meaning.

## Works with

| | |
|---|---|
| **Claude Code** (terminal, desktop app, IDE) | Everything, including the commands above and hooks that run the checks after each file is written. |
| **Codex** (CLI, IDE, app) | Everything; say "run nomagic-tailor" instead of typing a slash command. |
| **Other AI coding assistants** | Point them at `AGENTS.md`; the checks work the same. |
| **Claude app** (chat) and skill-only installs | The CV method and the check scripts, installed as a skill. No slash commands, subagents or hooks: the assistant runs the checks as steps. See [standalone installs](skills/nomagic-cv/SKILL.md#standalone-install-vs-full-project). |
| **Email** | Gmail and Microsoft 365 through Claude's connectors or their official servers. |

## For developers

How the checks, hooks and evidence system work, agent support details and how NoMagicCV compares to other tools: [`docs/DEVELOPERS.md`](docs/DEVELOPERS.md). Contributions welcome: [`CONTRIBUTING.md`](CONTRIBUTING.md).

Built on and inspired by open-source projects including [RenderCV](https://github.com/rendercv/rendercv), [JSON Resume](https://github.com/jsonresume/resume-schema), [Reactive Resume](https://github.com/amruthpillai/reactive-resume), [ai-job-search](https://github.com/ai-job-search-dev/ai-job-search), [career-ops](https://github.com/santifer/career-ops), [google-maps-scraper](https://github.com/gosom/google-maps-scraper) and [google-maps-scraper-kit](https://github.com/Mahanaicoach/google-maps-scraper-kit). Full list: [`CREDITS.md`](CREDITS.md).

## License

Code under [MIT](LICENSE), framework text under [CC BY 4.0](LICENSE-CONTENT). [Cite this project](CITATION.cff) · [Security](SECURITY.md) · Not legal or career advice.

<div align="center">
<br>
<img src="docs/brand/logo-mark.svg" alt="" width="40">
<br>
<sub>Made by <a href="https://github.com/naufal-nazar">Noufal Nazar</a>. If NoMagicCV helps you, a ⭐ helps others find it.</sub>
</div>
