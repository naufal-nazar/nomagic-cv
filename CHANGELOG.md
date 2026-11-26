# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org).

## [Unreleased]

### Changed
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
- `tests/test_bundle_smoke.py`: builds the zip, installs it into a temporary skills folder and a fresh virtualenv using only the bundle's files, and runs the fact, consistency, parse and posting checks on the fictional example data

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
