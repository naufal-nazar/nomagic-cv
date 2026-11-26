# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org).

## [Unreleased]

## [0.2.0] - 2026-11-26

### Changed
- README, `SKILL.md` description, `pyproject.toml`, `CREDITS.md` and `docs/DEVELOPERS.md` now say precisely what the checks verify (tags, numbers, titles, dates, listed items, text extraction) and what they cannot (meaning, the truth of the fact sheet, a real ATS), and what leaves the machine (content the host assistant sends to its model provider; optional email, lead-finder, DNS and cross-review features). New README section: "What the checks prove, and what they don't"; the parse-check row describes its table, image and column detection as heuristic warnings; the data section says which protections (read-only versions, fact-sheet approval, email gating) rely on full-project hooks and which are instructions only in a skill-only install. `fact_check.py`'s OK line reworded to match
- Tracker: `tracker.py add` now logs a `draft`. A row becomes `applied` only with `tracker.py status <id> applied --confirmed-submitted` (or `add --confirmed-submitted`), which sets the submission date and the first follow-up. Drafts are left out of callback statistics and follow-up lists, and `due` lists them for confirmation. Existing rows are read as they are and never rewritten; saves keep extra columns and write atomically
- `SKILL.md` and `references/outreach.md` now say which steps rely on the full project's slash commands, subagents and hooks, and what to do instead in a standalone install (including: never use a connector's send action without the hook; draft instead)
- `schedule.py install` and `run-once` stop with an explanation outside the full project clone, where the `nomagic-daily` command they run does not exist
- Commands renamed to say what they do: `/nomagic-start` → `/nomagic-facts`, `/nomagic-build` → `/nomagic-master`, `/nomagic-apply` → `/nomagic-tailor` (it never submits), `/nomagic-review` → `/nomagic-stats`, `/nomagic-leads` → `/nomagic-employers`

### Added
- Outreach in two modes: semi-auto drafts (default) and capped auto-send, with consent basis, follow-up limits, opt-outs and banned phrases enforced by `outreach.py` and a pre-send hook
- Lead import from gosom/google-maps-scraper and google-maps-scraper-kit exports; MX checks without SMTP probing
- Email via Claude connectors or official MCP servers (Google Gmail MCP, Microsoft Work IQ Mail), plus SMTP for auto-send
- `/nomagic-outreach` and `/nomagic-inbox`; replies scanned by the injection guard
- `/nomagic-employers` runs gosom/google-maps-scraper or google-maps-scraper-kit and imports results
- `/nomagic-daily` unattended routine and `schedule.py` (cron, Task Scheduler); permission allowlist for headless runs
- Versioned CV storage (`versions.py`), HTML/PDF export, branded README visuals
- Standalone bundle (`setup.py --zip`, `--global`) now ships `LICENSE`, `LICENSE-CONTENT`, `CREDITS.md`, a runtime-only `requirements.txt`, and `NOTICE.md` with CC BY 4.0 attribution and a list of packaging changes
- `setup.py --zip` also writes `nomagic-cv.zip.sha256` (`sha256sum -c` format); release zips are attached to GitHub releases
- `docs/WALKTHROUGH.md`: install from the release zip and take a fictional candidate from the facts interview to a checked PDF, with real check output
- `tests/test_bundle_smoke.py`: builds the zip, installs it into a temporary skills folder and a fresh virtualenv from the bundle's `requirements.txt`, and runs the fact, consistency, parse (DOCX and PDF) and posting checks. Facts come from the bundle's fictional example; CVs, letters and postings are inline test strings, not repository files. PDF export is skipped, with the reason printed, when no Chrome, Chromium or Edge is installed. The docstring lists what a pass does and does not show

## [0.1.0] - 2026-11-19

First public release.

### Added
- Agent skill (`skills/nomagic-cv`) with the six-layer method, references and templates
- 37 graded rules and 23 research sources; CI evidence gate (`rules_lint.py`)
- Checks: fact provenance, ATS parse test, application consistency, posting injection guard
- Application tracker with 95% Wilson intervals
- RenderCV and JSON Resume export
- Claude Code commands (`/nomagic-*`), five subagents and hooks; Codex adapter; `AGENTS.md`
- Cross-platform `scripts/setup.py`, user-wide installs and a Claude app skill zip
- Evals with fictional candidates, unit tests, CI on Linux, macOS and Windows
