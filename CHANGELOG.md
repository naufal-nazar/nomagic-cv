# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org).

## [Unreleased]

### Added
- Outreach in two modes: semi-auto drafts (default) and capped auto-send, with consent basis, follow-up limits, opt-outs and banned phrases enforced by `outreach.py` and a pre-send hook
- Lead import from gosom/google-maps-scraper and google-maps-scraper-kit exports; MX checks without SMTP probing
- Email via Claude connectors or official MCP servers (Google Gmail MCP, Microsoft Work IQ Mail), plus SMTP for auto-send
- `/nomagic-outreach` and `/nomagic-inbox`; replies scanned by the injection guard
- Versioned CV storage (`versions.py`), HTML/PDF export, branded README visuals

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
