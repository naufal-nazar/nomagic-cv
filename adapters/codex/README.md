# Codex adapter

Codex reads `AGENTS.md` and Agent Skills from `.agents/skills/` natively, so the skill and golden rules work without changes.

## Hooks
Codex hooks are stable from v0.124.0 (April 2026) and can intercept `apply_patch` and Bash in PreToolUse/PostToolUse. `hooks/dispatch.py` already understands Codex `apply_patch` payloads and Bash commands that write into `workspace/`.

`hooks.example.json` mirrors the Claude Code setup. Hook schemas have changed across Codex releases, so check it against the current docs (https://developers.openai.com/codex/hooks) and your version (`codex --version`) before enabling, then copy it to `.codex/hooks.json` or inline it in `config.toml`.

Known difference: Codex may not support the `ask` permission decision used to guard `facts.yaml`. If it is ignored, the golden rule in `AGENTS.md` still applies, and you can switch the pre-write handler to deny with a message.

## Commands
Codex does not use `.claude/commands/`. Type the command name as a request ("run nomagic-apply on this posting: ..."); `AGENTS.md` maps it to the matching command file.
