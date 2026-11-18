@AGENTS.md

Claude Code specifics: slash commands are in `.claude/commands/`, subagents in `.claude/agents/`, and hooks in `.claude/settings.json` call `hooks/dispatch.py`. Use the subagents for their roles; keep the reviewer's context free of the drafting.
