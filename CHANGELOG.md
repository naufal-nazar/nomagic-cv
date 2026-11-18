# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org).

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
