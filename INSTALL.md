# Installing NoMagicCV

This file is written for **AI agents and humans alike**. If you are an agent asked to install NoMagicCV, follow the steps for the user's environment, run every command, and report the result of the final check. Ask the user before installing anything outside the project folder (steps marked *user-wide*).

## 0. Prerequisites

- **Python 3.10+** (and [uv](https://docs.astral.sh/uv/) if you want the exact locked versions; optional).
- **For PDF export:** Chrome, Chromium or Edge already on your computer, or `pip install "rendercv[full]"`.
- Optional: poppler's `pdftotext` for the parse check; without it, the check uses pypdf.
- Claude app only (no terminal): a plan with code execution turned on. Skip to the Claude app row in section 3.

## 1. Get the code

```bash
git clone https://github.com/naufal-nazar/nomagic-cv.git
cd nomagic-cv
```

No git? Download the ZIP from the repository page, unzip it, and `cd` into the folder.

## 2. Run setup (all environments)

With [uv](https://docs.astral.sh/uv/) (recommended: fast, and installs the exact locked versions):

```bash
uv run scripts/setup.py
```

Without uv:

```bash
python3 scripts/setup.py        # Windows: py scripts/setup.py  or  python scripts/setup.py
```

It is safe to run more than once. It:

- checks Python 3.10+ and installs dependencies into the project `.venv` only: with `uv sync` from `uv.lock` when uv is installed, otherwise it creates `.venv` and runs pip inside it. It never installs into your own Python. If no `.venv` can be created (for example Debian/Ubuntu without `python3-venv`), it stops and explains; `--allow-user-install` (*user-wide*) then installs into your user site-packages instead
- creates the private `workspace/` folder
- makes the skill visible to Claude Code (`.claude/skills/`) and Codex and other agents (`.agents/skills/`), copying instead of linking where symlinks are unavailable
- points the hooks at a Python that exists on this machine
- turns on the privacy pre-commit hook
- runs the self-test (evidence gate and evals)

Success ends with `NoMagicCV is ready.` To verify later without changing anything: `python3 scripts/setup.py --check`.

## 3. Connect your agent

| Environment | What to do | What you get |
|---|---|---|
| **Claude Code**: terminal, desktop app or IDE | Open the `nomagic-cv` folder as the project. Type `/nomagic-facts`. | Skill, `/nomagic-*` commands, 5 subagents, automatic hooks |
| **Codex**: CLI, IDE extension or app | Open the folder as the project. Say `run nomagic-facts`. Optional automatic checks: `python3 scripts/setup.py --codex-hooks`, then check the file against your Codex version. | Skill, `AGENTS.md` rules, checks as steps or hooks |
| **Gemini CLI, Cursor, Copilot, other agents** | Open the folder. Say `Read AGENTS.md, then run nomagic-facts`. | Skill where supported, `AGENTS.md` rules, checks run as steps |
| **Claude app** (chat on web or desktop, no terminal) | Download `nomagic-cv.zip` from [Releases](https://github.com/naufal-nazar/nomagic-cv/releases) and check it against `nomagic-cv.zip.sha256` (or build it: `python3 scripts/setup.py --zip`), then upload it in **Customize > Skills** (code execution must be on). Step by step: [walkthrough, section 2a](docs/WALKTHROUGH.md#2a-claude-app-chat-no-terminal). | The skill and its checks run in Claude's cloud sandbox, not on your computer; no slash commands or hooks. Ask for generated files as downloads and keep copies |
| **Use it in every project** *(user-wide)* | `python3 scripts/setup.py --global claude` or `--global codex` or `--global all`. Or, from the release zip: [walkthrough, section 2b](docs/WALKTHROUGH.md#2b-claude-code-or-codex-local-terminal) | Skill installed to `~/.claude/skills` or `~/.codex/skills`; data in `~/nomagic-cv-workspace` |

## 3b. Connect email for outreach (optional)

Pick either route. In the full project both are gated by the same pre-send hook; skill-only installs and the Claude app have no hooks, so the assistant is instructed to make drafts there.

**Connectors** (Claude app, desktop, Claude Code): turn on the Gmail or Microsoft 365 connector in Claude and sign in. No other setup.

**Official MCP servers** (Codex, Claude Code, any MCP client):

| Provider | Command | Notes |
|---|---|---|
| Gmail | `python3 scripts/setup.py --email gmail` | Adds Google's official Gmail MCP server to `.mcp.json` and writes a Codex snippet. Developer Preview: enrol, enable the Gmail API and Gmail MCP API, then sign in from `/mcp`. Drafts and reading only. |
| Microsoft 365 (work) | `python3 scripts/setup.py --email outlook` | Prints the steps for Microsoft's Work IQ Mail MCP, which needs a Microsoft 365 Copilot licence. |

**Auto-send through any provider:** `python3 scripts/setup.py --email smtp` creates `workspace/.smtp.env` (private) for your SMTP host and an app password. Then set `preferences.outreach.mode: auto`.

## 3c. Lead finder and daily schedule (optional)

```bash
python3 scripts/setup.py --leads kit          # or --leads gosom (Docker); installed to ~/.nomagic/tools
python3 scripts/schedule.py install --agent claude --time 08:30   # or --agent codex; cron or Task Scheduler
```

Agents: ask the user before installing either. The lead finder shows a terms notice the user must accept themselves.

## 4. Final check (agents: report this output to the user)

```bash
python3 scripts/setup.py --check
```

## Where your data goes

- Inside the repo: `workspace/` (gitignored, blocked from commits by the pre-commit hook).
- Standalone installs and uploads: `~/nomagic-cv-workspace`.
- Anywhere else: set `NOMAGIC_WORKSPACE=/path/you/choose`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python3: command not found` (Windows) | Use `py` or `python`; setup rewrites the hooks to match. |
| `externally-managed-environment` from pip | Setup installs only into `.venv`, where this doesn't apply. If `.venv` can't be created, install `python3-venv` (or uv) and rerun, or use `--allow-user-install` (*user-wide*). |
| Skill not found by the agent | Run setup again; it repairs the skill links. Restart the agent. |
| Hooks don't run in Codex | Hooks are optional there. Run the checks listed in `AGENTS.md` as steps. |
| PDF export fails | `pip install "rendercv[full]"`, or export to `.docx` from your editor and run `parse_check.py` on it. |

## Uninstall

1. **Find your data first.** It is in `$NOMAGIC_WORKSPACE` if you set it; otherwise `workspace/` **inside the clone**, or `~/nomagic-cv-workspace` for skill-only installs.
2. **If it is `workspace/` inside the clone, copy or move it out before deleting anything**: deleting the clone deletes it.
3. Delete the `nomagic-cv` clone. If you installed the skill user-wide or from the zip, also delete `~/.claude/skills/nomagic-cv` and/or `~/.codex/skills/nomagic-cv` (these hold no personal data).
4. Data outside those folders stays until you delete it: `~/nomagic-cv-workspace` (or your `NOMAGIC_WORKSPACE`), lead-finder tools in `~/.nomagic/tools`, and any `schedule.py` job (remove it first with `python3 scripts/schedule.py remove`).
