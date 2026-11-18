# Security policy

## Reporting a vulnerability

Please report security issues privately through [GitHub security advisories](https://github.com/naufal-nazar/nomagic-cv/security/advisories/new), not in public issues. You'll get a reply within 7 days.

## Scope

In scope:
- Prompt-injection bypasses of `scripts/posting_guard.py` (please include a fictional posting that reproduces it)
- Ways a hook or script could leak data from `workspace/` or commit it to git
- Command execution through crafted postings, CVs or fact sheets

## Design notes

- Job postings are treated as untrusted input; agents read only the sanitized copy. This is an instruction-level defence, not a sandbox.
- Personal data stays local in `workspace/` (or `NOMAGIC_WORKSPACE`), is gitignored, and is blocked by a pre-commit hook.
- The scripts make no network calls. Only the researcher subagent uses web search, through the agent's own tools.
