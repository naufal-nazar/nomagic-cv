#!/usr/bin/env python3
"""Run NoMagicCV's daily routine automatically, with Claude Code or Codex in headless mode.

The routine (/nomagic-daily) checks the inbox, records replies, prepares due follow-ups
(drafts in semi-auto mode; checked sends in auto mode), flags stale applications and
writes a report to workspace/reports/<date>_daily.md. It never edits facts.yaml,
never freezes CV versions and never submits applications.

Commands:
  install --agent claude|codex [--time 08:30] [--days weekdays|daily]
                       add a cron job (macOS, Linux) or a Task Scheduler task (Windows)
  remove               delete the job
  status               show the job, if any
  run-once --agent claude|codex
                       what the scheduler runs: one headless pass, output saved to workspace/reports/<date>_daily-run.log.md

In-app alternatives: the Codex app's automations, or your Claude app's scheduled tasks,
pointed at this folder with the prompt "/nomagic-daily" (Claude) or "run nomagic-daily" (Codex).
"""
from __future__ import annotations

import argparse
import datetime as dt
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = "# nomagic-cv daily"
TASK = "NoMagicCV-Daily"
IS_WIN = platform.system() == "Windows"
PROMPTS = {"claude": "/nomagic-daily", "codex": "run nomagic-daily"}


def python() -> str:
    for cand in (ROOT / ".venv" / "bin" / "python", ROOT / ".venv" / "Scripts" / "python.exe"):
        if cand.exists():
            return str(cand)
    return sys.executable


def headless(agent: str) -> list[str]:
    if agent == "claude":
        return ["claude", "-p", PROMPTS["claude"]]
    return ["codex", "exec", "--full-auto", PROMPTS["codex"]]


def job_command(agent: str) -> str:
    return f'cd "{ROOT}" && "{python()}" scripts/schedule.py run-once --agent {agent}'


def cron_lines() -> list[str]:
    res = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return res.stdout.splitlines() if res.returncode == 0 else []


def cmd_install(a) -> int:
    if not shutil.which(a.agent):
        print(f"'{a.agent}' is not on PATH. Install it and sign in first.", file=sys.stderr)
        return 1
    hh, mm = (int(x) for x in a.time.split(":"))
    if IS_WIN:
        days = ["/SC", "WEEKLY", "/D", "MON,TUE,WED,THU,FRI"] if a.days == "weekdays" else ["/SC", "DAILY"]
        tr = f'"{python()}" "{ROOT / "scripts" / "schedule.py"}" run-once --agent {a.agent}'
        subprocess.run(["schtasks", "/Create", "/F", "/TN", TASK, "/TR", tr, *days, "/ST", f"{hh:02d}:{mm:02d}"], check=True)
        print(f"Task Scheduler: {TASK} at {hh:02d}:{mm:02d} ({a.days}).")
        return 0
    if not shutil.which("crontab"):
        print("crontab not found. Use your app's scheduled tasks or automations instead.", file=sys.stderr)
        return 1
    dow = "1-5" if a.days == "weekdays" else "*"
    lines = [l for l in cron_lines() if MARK not in l]
    lines.append(f"{mm} {hh} * * {dow} {job_command(a.agent)} {MARK}")
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)
    print(f"cron: {a.agent} runs /nomagic-daily at {hh:02d}:{mm:02d} ({a.days}). Reports: workspace/reports/")
    print("Your computer must be awake at that time. Remove with: python scripts/schedule.py remove")
    return 0


def cmd_remove(_a) -> int:
    if IS_WIN:
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK], check=False)
    elif shutil.which("crontab"):
        lines = [l for l in cron_lines() if MARK not in l]
        subprocess.run(["crontab", "-"], input="\n".join(lines) + ("\n" if lines else ""), text=True, check=False)
    print("Removed the daily job (if there was one).")
    return 0


def cmd_status(_a) -> int:
    if IS_WIN:
        subprocess.run(["schtasks", "/Query", "/TN", TASK], check=False)
        return 0
    jobs = [l for l in cron_lines() if MARK in l]
    print("\n".join(jobs) if jobs else "No daily job installed.")
    return 0


def cmd_run_once(a) -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    from cvlib import WORKSPACE
    reports = WORKSPACE / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / f"{dt.date.today().isoformat()}_daily-run.log.md"
    res = subprocess.run(headless(a.agent), cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out.write_text(f"# Daily routine, {dt.datetime.now():%Y-%m-%d %H:%M} ({a.agent})\n\n{res.stdout}\n"
                   + (f"\n## Errors\n\n```\n{res.stderr[-3000:]}\n```\n" if res.returncode else ""), encoding="utf-8")
    print(f"Report: {out}")
    return res.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("install"); s.add_argument("--agent", required=True, choices=list(PROMPTS))
    s.add_argument("--time", default="08:30"); s.add_argument("--days", default="weekdays", choices=["weekdays", "daily"])
    s.set_defaults(fn=cmd_install)
    sub.add_parser("remove").set_defaults(fn=cmd_remove)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("run-once"); s.add_argument("--agent", required=True, choices=list(PROMPTS)); s.set_defaults(fn=cmd_run_once)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
