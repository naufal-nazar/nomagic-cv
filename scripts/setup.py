#!/usr/bin/env python3
"""One-command setup for NoMagicCV. Standard library only; works on macOS, Linux and Windows.

Usage (with uv, recommended: `uv run scripts/setup.py ...`; without uv, use python3):
  python3 scripts/setup.py                 set up this clone for every agent (default)
  python3 scripts/setup.py --check         verify the setup without changing anything
  python3 scripts/setup.py --global claude install the skill for Claude Code in all your projects
  python3 scripts/setup.py --global codex  install the skill for Codex (CLI, IDE and app)
  python3 scripts/setup.py --codex-hooks   enable automatic checks in Codex for this project
  python3 scripts/setup.py --zip           build dist/nomagic-cv.zip to upload to the Claude app
  python3 scripts/setup.py --email gmail   add Google's official Gmail MCP server (drafts) for outreach
  python3 scripts/setup.py --email smtp    prepare auto-send through your own provider's SMTP (app password)
  python3 scripts/setup.py --leads kit     install an open-source Google Maps scraper for /nomagic-employers

Safe to run more than once. Prints what it did and the next step for each agent.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "nomagic-cv"
IS_WIN = platform.system() == "Windows"
OK, WARN, FAIL = "✓", "!", "✗"
try:
    "✓".encode(sys.stdout.encoding or "utf-8")
except (UnicodeEncodeError, LookupError):
    OK, WARN, FAIL = "OK", "!!", "XX"

problems: list[str] = []


def say(mark: str, msg: str) -> None:
    print(f"  {mark} {msg}")
    if mark == FAIL:
        problems.append(msg)


def venv_python() -> Path:
    return ROOT / ".venv" / ("Scripts/python.exe" if IS_WIN else "bin/python")


def project_python() -> str:
    vp = venv_python()
    return str(vp) if vp.exists() else sys.executable


def has_deps(py: str) -> bool:
    code = "import yaml, pypdf, docx"
    return subprocess.run([py, "-c", code], capture_output=True).returncode == 0


# ------------------------------------------------------------------ steps
def step_python() -> None:
    if sys.version_info < (3, 10):
        say(FAIL, f"Python 3.10+ needed, found {platform.python_version()}")
    else:
        say(OK, f"Python {platform.python_version()}")


def step_deps(check: bool) -> None:
    py = project_python()
    if has_deps(py):
        say(OK, "Dependencies installed" + (" (.venv)" if py != sys.executable else ""))
        return
    if check:
        say(FAIL, "Dependencies missing (run: uv run scripts/setup.py, or python3 scripts/setup.py)")
        return
    if shutil.which("uv"):
        res = subprocess.run(["uv", "sync", "--no-dev"], cwd=ROOT, capture_output=True, text=True)
        if res.returncode == 0 and has_deps(str(venv_python())):
            say(OK, "Dependencies installed with uv (.venv, locked by uv.lock)")
            return
        say(WARN, "uv sync failed; falling back to pip:\n" + res.stderr[-400:])
    req = str(ROOT / "requirements.txt")
    attempt = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", req], capture_output=True, text=True)
    if attempt.returncode != 0 and "externally-managed" in (attempt.stderr + attempt.stdout):
        attempt = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--user", "-r", req], capture_output=True, text=True)
    if attempt.returncode == 0 and has_deps(sys.executable):
        say(OK, "Dependencies installed")
        return
    # Fall back to a project virtualenv; hooks pick it up automatically.
    venv.EnvBuilder(with_pip=True, clear=False).create(ROOT / ".venv")
    vp = str(venv_python())
    res = subprocess.run([vp, "-m", "pip", "install", "-q", "-r", req], capture_output=True, text=True)
    if res.returncode == 0 and has_deps(vp):
        say(OK, "Dependencies installed in .venv (hooks use it automatically)")
    else:
        say(FAIL, "Could not install dependencies:\n" + (res.stderr or attempt.stderr)[-800:])


def step_workspace(check: bool) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from cvlib import WORKSPACE
    except Exception:
        WORKSPACE = Path(os.environ.get("NOMAGIC_WORKSPACE") or ROOT / "workspace")
    if not check:
        for sub in ("sources", "cvs", "applications"):
            (WORKSPACE / sub).mkdir(parents=True, exist_ok=True)
    say(OK if WORKSPACE.exists() else FAIL, f"Private workspace: {WORKSPACE}")


def link_or_copy(link: Path, target: Path, check: bool) -> None:
    """Skill discovery folders. Symlinks where possible, copies on Windows without symlink rights."""
    if link.is_dir() and (link / "SKILL.md").exists():
        say(OK, f"Skill visible at {link.relative_to(ROOT)}")
        return
    if check:
        say(FAIL, f"Skill missing at {link.relative_to(ROOT)}")
        return
    if link.exists() or link.is_symlink():
        link.unlink() if (link.is_file() or link.is_symlink()) else shutil.rmtree(link)
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)
        say(OK, f"Linked skill at {link.relative_to(ROOT)}")
    except OSError:
        shutil.copytree(target, link)
        say(OK, f"Copied skill to {link.relative_to(ROOT)} (symlinks unavailable)")


def step_skill_links(check: bool) -> None:
    link_or_copy(ROOT / ".claude" / "skills" / "nomagic-cv", SKILL, check)
    link_or_copy(ROOT / ".agents" / "skills" / "nomagic-cv", SKILL, check)


def step_hook_interpreter(check: bool) -> None:
    """Hooks call python3; on systems without it (common on Windows) switch to python."""
    settings = ROOT / ".claude" / "settings.json"
    text = settings.read_text(encoding="utf-8")
    if shutil.which("python3") or "python3 " not in text:
        say(OK, "Claude Code hooks can find Python")
        return
    if check:
        say(FAIL, "Hooks call python3, which is not on PATH (run setup to fix)")
        return
    settings.write_text(text.replace("python3 ", "python "), encoding="utf-8")
    say(OK, "Hooks switched from python3 to python for this machine")


def step_git_hook(check: bool) -> None:
    if not (ROOT / ".git").exists():
        say(WARN, "Not a git clone: privacy pre-commit hook skipped")
        return
    cur = subprocess.run(["git", "-C", str(ROOT), "config", "core.hooksPath"], capture_output=True, text=True).stdout.strip()
    if cur == "scripts/git-hooks":
        say(OK, "Privacy pre-commit hook active")
    elif check:
        say(FAIL, "Privacy pre-commit hook not active")
    else:
        subprocess.run(["git", "-C", str(ROOT), "config", "core.hooksPath", "scripts/git-hooks"], check=False)
        if not IS_WIN:
            for f in (ROOT / "scripts" / "git-hooks").iterdir():
                f.chmod(0o755)
        say(OK, "Privacy pre-commit hook enabled")


def step_optional_tools() -> None:
    say(OK if shutil.which("pdftotext") else WARN,
        "pdftotext found" if shutil.which("pdftotext") else "pdftotext not found (optional; pypdf is used instead)")
    say(OK if shutil.which("rendercv") else WARN,
        "RenderCV found" if shutil.which("rendercv") else 'RenderCV not found (optional, for PDFs: pip install "rendercv[full]")')


def step_self_test() -> None:
    py = project_python()
    for name, args in (("Evidence gate", ["scripts/rules_lint.py"]), ("Evals", ["evals/run_evals.py"])):
        res = subprocess.run([py, *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
        say(OK if res.returncode == 0 else FAIL, f"{name} {'passed' if res.returncode == 0 else 'failed'}")
        if res.returncode:
            print(res.stdout[-600:] + res.stderr[-600:])


# ------------------------------------------------------------------ extras
def bundle(dest: Path) -> None:
    """Self-contained skill folder: SKILL.md + references + templates + scripts + rules."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SKILL, dest, symlinks=False)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "git-hooks", "setup.py")
    shutil.copytree(ROOT / "scripts", dest / "scripts", ignore=ignore)
    shutil.copytree(ROOT / "rules", dest / "rules")


def install_global(agent: str) -> None:
    home = Path.home()
    targets = {"claude": [home / ".claude" / "skills" / "nomagic-cv"],
               "codex": [Path(os.environ.get("CODEX_HOME", home / ".codex")) / "skills" / "nomagic-cv"]}
    for dest in targets[agent]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        bundle(dest)
        say(OK, f"Installed skill for {agent}: {dest}")
    say(OK, "Your data will live in ~/nomagic-cv-workspace (set NOMAGIC_WORKSPACE to change it)")
    say(WARN, "Global installs give you the skill and checks; slash commands and hooks work when you open this repo")


def enable_codex_hooks() -> None:
    src = ROOT / "adapters" / "codex" / "hooks.example.json"
    dest = ROOT / ".codex" / "hooks.json"
    dest.parent.mkdir(exist_ok=True)
    text = src.read_text(encoding="utf-8")
    if not shutil.which("python3"):
        text = text.replace("python3 ", "python ")
    dest.write_text(text, encoding="utf-8")
    say(OK, f"Wrote {dest.relative_to(ROOT)}")
    say(WARN, "Codex hook formats change between versions: check `codex --version` against developers.openai.com/codex/hooks")


SMTP_TEMPLATE = """# NoMagicCV auto-send settings. This file stays in your private workspace and is never committed.
# Use an APP PASSWORD, never your normal password.
#   Gmail:   smtp.gmail.com, port 587 (needs 2-Step Verification, then create an app password)
#   iCloud:  smtp.mail.me.com, port 587 (app-specific password from your Apple Account)
#   Zoho:    smtp.zoho.com, port 587 (app password)
#   Others:  your provider's SMTP host; port 587 (STARTTLS) or 465 (SSL)
NOMAGIC_SMTP_HOST=
NOMAGIC_SMTP_PORT=587
NOMAGIC_SMTP_USER=
NOMAGIC_SMTP_PASSWORD=
# NOMAGIC_SMTP_FROM=Your Name <you@example.com>
"""


def setup_email(provider: str) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from cvlib import WORKSPACE
    except Exception:
        WORKSPACE = ROOT / "workspace"
    if provider == "gmail":
        mcp = ROOT / ".mcp.json"
        data = json.loads(mcp.read_text(encoding="utf-8")) if mcp.exists() else {}
        data.setdefault("mcpServers", {})["gmail"] = {"type": "http", "url": "https://gmailmcp.googleapis.com/mcp/v1"}
        mcp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        say(OK, "Added Google's official Gmail MCP server to .mcp.json (Claude Code)")
        snippet = ROOT / "adapters" / "codex" / "gmail-mcp.toml"
        say(OK, f"Codex: copy {snippet.relative_to(ROOT)} into ~/.codex/config.toml or .codex/config.toml")
        say(WARN, "Google's server is a Developer Preview: enrol, enable the Gmail API and Gmail MCP API in a Google "
                  "Cloud project, then sign in from /mcp. See developers.google.com/workspace/gmail/api/reference/mcp")
        say(WARN, "It reads and drafts but does not send, so it pairs with semi-auto mode. For auto mode add --email smtp")
    elif provider == "outlook":
        say(WARN, "Microsoft's official Outlook MCP (Work IQ Mail) needs a Microsoft 365 Copilot licence in an "
                  "organisation tenant; personal Outlook.com accounts are not supported. See learn.microsoft.com "
                  "(Work IQ MCP overview). Otherwise use semi-auto mode with drafts you paste, or --email smtp "
                  "if your provider allows SMTP with an app password.")
    elif provider == "smtp":
        env = WORKSPACE / ".smtp.env"
        env.parent.mkdir(parents=True, exist_ok=True)
        if not env.exists():
            env.write_text(SMTP_TEMPLATE, encoding="utf-8")
            if not IS_WIN:
                env.chmod(0o600)
        say(OK, f"Fill in {env} with your SMTP host and an app password (private, gitignored)")
        say(OK, "Then set preferences.outreach.mode: auto in facts.yaml to let checked messages send")


def build_zip() -> None:
    dist = ROOT / "dist"
    staging = dist / "staging" / "nomagic-cv"
    bundle(staging)
    archive = shutil.make_archive(str(dist / "nomagic-cv"), "zip", root_dir=staging.parent, base_dir="nomagic-cv")
    shutil.rmtree(dist / "staging")
    say(OK, f"Built {Path(archive).relative_to(ROOT)} (top-level folder: nomagic-cv/)")
    say(OK, "Upload it in the Claude app under Customize > Skills (code execution must be on)")


NEXT = """
Next step, in the agent you use:
  Claude Code (terminal, desktop app or IDE)  open this folder, then type  /nomagic-facts
  Codex (CLI, IDE or app)                     open this folder, then say   run nomagic-facts
  Other agents                                open this folder, then say   Read AGENTS.md, then run nomagic-facts
  Claude app (chat, no terminal)              uv run scripts/setup.py --zip (or python3 ...), upload dist/nomagic-cv.zip
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify only")
    ap.add_argument("--global", dest="glob", choices=["claude", "codex", "all"], help="install the skill user-wide")
    ap.add_argument("--codex-hooks", action="store_true", help="enable Codex hooks for this project")
    ap.add_argument("--zip", action="store_true", help="build dist/nomagic-cv.zip for the Claude app")
    ap.add_argument("--email", choices=["gmail", "outlook", "smtp"], action="append",
                    help="connect an email provider for outreach (repeatable)")
    ap.add_argument("--leads", choices=["kit", "gosom"], help="install an open-source Google Maps scraper for /nomagic-employers")
    ap.add_argument("--skip-tests", action="store_true")
    a = ap.parse_args()

    print(f"NoMagicCV setup ({platform.system()}, {'check only' if a.check else 'installing'})")
    step_python()
    step_deps(a.check)
    step_workspace(a.check)
    step_skill_links(a.check)
    step_hook_interpreter(a.check)
    step_git_hook(a.check)
    step_optional_tools()
    if a.glob:
        for agent in (["claude", "codex"] if a.glob == "all" else [a.glob]):
            install_global(agent)
    if a.codex_hooks:
        enable_codex_hooks()
    if a.zip:
        build_zip()
    for provider in a.email or []:
        setup_email(provider)
    if a.leads:
        res = subprocess.run([project_python(), str(ROOT / "scripts" / "leads.py"), "install", "--engine", a.leads])
        say(OK if res.returncode == 0 else FAIL, f"Lead finder ({a.leads}) {'installed' if res.returncode == 0 else 'not installed'}")
    if not a.skip_tests and not problems:
        step_self_test()

    if problems:
        print(f"\n{FAIL} Setup incomplete ({len(problems)} problem(s)). Fix the items marked {FAIL} and run again.")
        return 1
    print(f"\n{OK} NoMagicCV is ready.")
    print(NEXT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
