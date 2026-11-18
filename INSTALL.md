# Installing NoMagicCV

This file is written for **AI agents and humans alike**. If you are an agent asked to install NoMagicCV, follow the steps for the user's environment, run every command, and report the result of the final check. Ask the user before installing anything outside the project folder (steps marked *user-wide*).

## 1. Get the code

```bash
git clone https://github.com/naufal-nazar/nomagic-cv.git
cd nomagic-cv
```

No git? Download the ZIP from the repository page, unzip it, and `cd` into the folder.

## 2. Run setup (all environments)

```bash
python3 scripts/setup.py        # Windows: py scripts/setup.py  or  python scripts/setup.py
```

It is safe to run more than once. It:

- checks Python 3.10+ and installs dependencies (falls back to a project `.venv` if the system blocks `pip`)
- creates the private `workspace/` folder
- makes the skill visible to Claude Code (`.claude/skills/`) and Codex and other agents (`.agents/skills/`), copying instead of linking where symlinks are unavailable
- points the hooks at a Python that exists on this machine
- turns on the privacy pre-commit hook
- runs the self-test (evidence gate and evals)

Success ends with `NoMagicCV is ready.` To verify later without changing anything: `python3 scripts/setup.py --check`.

## 3. Connect your agent

| Environment | What to do | What you get |
|---|---|---|
| **Claude Code**: terminal, desktop app or IDE | Open the `nomagic-cv` folder as the project. Type `/nomagic-start`. | Skill, `/nomagic-*` commands, 5 subagents, automatic hooks |
| **Codex**: CLI, IDE extension or app | Open the folder as the project. Say `run nomagic-start`. Optional automatic checks: `python3 scripts/setup.py --codex-hooks`, then check the file against your Codex version. | Skill, `AGENTS.md` rules, checks as steps or hooks |
| **Gemini CLI, Cursor, Copilot, other agents** | Open the folder. Say `Read AGENTS.md, then run nomagic-start`. | Skill where supported, `AGENTS.md` rules, checks run as steps |
| **Claude app** (chat on web or desktop, no terminal) | On a computer: `python3 scripts/setup.py --zip`, then upload `dist/nomagic-cv.zip` in **Customize > Skills** (code execution must be on). | The skill and its checks inside Claude's sandbox; no slash commands or hooks |
| **Use it in every project** *(user-wide)* | `python3 scripts/setup.py --global claude` or `--global codex` or `--global all` | Skill installed to `~/.claude/skills` or `~/.codex/skills`; data in `~/nomagic-cv-workspace` |

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
| `externally-managed-environment` from pip | Setup creates `.venv` automatically; hooks use it. |
| Skill not found by the agent | Run setup again; it repairs the skill links. Restart the agent. |
| Hooks don't run in Codex | Hooks are optional there. Run the checks listed in `AGENTS.md` as steps. |
| PDF export fails | `pip install "rendercv[full]"`, or export to `.docx` from your editor and run `parse_check.py` on it. |

## Uninstall

Delete the `nomagic-cv` folder. If you installed user-wide, also delete `~/.claude/skills/nomagic-cv` and/or `~/.codex/skills/nomagic-cv`. Your data in `workspace/` or `~/nomagic-cv-workspace` is yours to keep or delete.
