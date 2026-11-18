# Credits

This project integrates with other open-source tools through adapters. No third-party code is copied into this repository; users install each tool themselves.

## Integrations

| Project | License | How we use it |
|---|---|---|
| [RenderCV](https://github.com/rendercv/rendercv) by Sina Atalay and contributors | MIT | `scripts/export.py rendercv` writes its YAML input; the user runs `rendercv render`. |
| [JSON Resume](https://github.com/jsonresume/resume-schema) schema ([jsonresume.org](https://jsonresume.org)) | MIT | `scripts/export.py jsonresume` writes the open schema for import into other tools. |
| [Reactive Resume](https://github.com/amruthpillai/reactive-resume) by Amruth Pillai | MIT | Optional visual editing, via JSON Resume export. |
| [OpenResume](https://github.com/xitanggg/open-resume) by Xitang Zhao | AGPL-3.0 | Optional second parse test, run as a separate program. No code copied. |
| [google-maps-scraper](https://github.com/gosom/google-maps-scraper) by gosom | MIT | Optional lead source; `outreach.py import --source gosom` reads its CSV/JSON export. Run separately. |
| [google-maps-scraper-kit](https://github.com/Mahanaicoach/google-maps-scraper-kit) by Mahanaicoach | MIT | Optional lead source; `outreach.py import --source kit` reads its CSV/JSON export. Run separately. |
| [Gmail MCP server](https://developers.google.com/workspace/gmail/api/reference/mcp) by Google | Google terms | Official remote MCP for drafts and inbox reading, added by `setup.py --email gmail`. |
| [Work IQ Mail](https://learn.microsoft.com/en-us/microsoft-copilot-studio/use-work-iq) by Microsoft | Microsoft terms | Official Outlook MCP for Microsoft 365 tenants with Copilot licences; documented, not configured automatically. |
| [Resume Matcher](https://github.com/srbhr/Resume-Matcher) by Saurabh Rai | Apache-2.0 | Optional keyword-gap check. We report must-have coverage, not a match score. |

## Ideas we learned from (no code used)

| Project | Idea | What we changed |
|---|---|---|
| [ai-job-search](https://github.com/ai-job-search-dev/ai-job-search) (MIT) | Posting integrity gate: treat job postings as untrusted input and check them for hidden text, invisible characters and instruction-like lines | Our own implementation (`scripts/posting_guard.py`) that also decodes Unicode tag-character smuggling, writes a sanitized copy, runs as a hook and is covered by evals |
| [santifer/career-ops](https://github.com/santifer/career-ops) | Application pipeline and tracker dashboard | Added honest statistics with uncertainty intervals |
| [JobOps](https://github.com/reggiechan74/jobops) | One file per role as the source of truth; a provenance step | Provenance is checked by code, not by AI judgement |
| [poferraz/career-ops](https://github.com/poferraz/career-ops) | Anti-slop quality rubric, evidence tiers | Each rule tied to a named, linked study or labelled practice |

## Research

The framework stands on the studies listed in [`rules/sources.yaml`](rules/sources.yaml). Thank you to their authors.
