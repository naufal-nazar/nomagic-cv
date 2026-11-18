#!/usr/bin/env python3
"""Regenerate the terminal screenshots in docs/assets/ from real runs.

Every image in the README is produced by this script running the actual
checks on the fictional eval cases, so the screenshots can't drift from
what the code does. Requires `pip install rich`.

Usage: python docs/make_screenshots.py
"""
from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
CASE = "evals/cases/data-analyst"
NBSP = "\u00a0"
ENV = {**os.environ, "CV_TODAY": "2026-11-19", "NO_COLOR": "1"}


def run(cmd: list[str], env: dict | None = None) -> str:
    out = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True, env=env or ENV)
    text = (out.stdout + out.stderr).replace(str(ROOT) + os.sep, "").replace(str(ROOT), ".")
    return text.rstrip()


def colour(line: str) -> Text:
    t = Text()
    m = re.match(r"^(ERROR|WARN|OK|NOTE)(\s+)(.*)$", line)
    if m:
        style = {"ERROR": "bold red", "WARN": "bold yellow", "OK": "bold green", "NOTE": "bold cyan"}[m.group(1)]
        t.append(m.group(1), style=style)
        t.append(NBSP * len(m.group(2)))
        rest = m.group(3)
        for part in re.split(r"(\[R-[A-Z]+-\d{2}\])", rest):
            # keep gaps visible in renderers that trim spaces at element edges
            part = re.sub(r"^ +| +$", lambda g: NBSP * len(g.group()), part)
            t.append(part, style="magenta" if re.fullmatch(r"\[R-[A-Z]+-\d{2}\]", part) else "")
        return t
    if line.startswith(("No winner", "Too few")):
        return Text(line, style="bold cyan")
    return Text(line)


def shot(name: str, title: str, steps: list[tuple[str, str]], width: int = 118) -> None:
    con = Console(record=True, width=width, force_terminal=True, color_system="truecolor")
    for i, (prompt, output) in enumerate(steps):
        if i:
            con.print()
        con.print(Text("$" + NBSP, style="bold green") + Text(prompt, style="bold"))
        for line in output.splitlines():
            con.print(colour(line), overflow="fold")
    ASSETS.mkdir(parents=True, exist_ok=True)
    con.save_svg(str(ASSETS / f"{name}.svg"), title=title)
    print(f"wrote docs/assets/{name}.svg")


def demo_tracker() -> str:
    """Fictional tracker: v2 looks better, but the sample is too small to say so."""
    rows, n = [], 0
    for version, total, callbacks in (("backend-v1", 22, 2), ("backend-v2", 19, 4)):
        for i in range(total):
            n += 1
            rows.append({"id": f"A{n:04d}", "date_applied": "2026-10-01", "company": f"Co{n}", "role": "Backend Engineer",
                         "role_family": "backend", "cv_version": version, "source": "", "posting_date": "",
                         "status": "callback" if i < callbacks else "rejected", "status_date": "2026-10-20",
                         "next_followup": "", "folder": ""})
    path = Path(tempfile.mkdtemp()) / "tracker.csv"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return str(path)


def main() -> int:
    shot("fact-check", "NoMagicCV: fact check", [
        (f"python scripts/fact_check.py fabricated.md --facts facts.yaml",
         run(["scripts/fact_check.py", f"{CASE}/fabricated.md", "--facts", f"{CASE}/facts.yaml"])
         .replace(f"{CASE}/", "")),
        (f"python scripts/fact_check.py good.md --facts facts.yaml",
         run(["scripts/fact_check.py", f"{CASE}/good.md", "--facts", f"{CASE}/facts.yaml"]).replace(f"{CASE}/", "")),
    ])
    clean = Path(tempfile.mkdtemp()) / "posting.clean.md"
    guard = run(["scripts/posting_guard.py", f"{CASE}/posting_malicious.md", "--sanitize", "-o", str(clean)])
    guard = guard.replace("posting_malicious.md", "posting.md").replace(str(clean), "posting.clean.md")
    shot("posting-guard", "NoMagicCV: posting injection guard", [
        ("python scripts/posting_guard.py posting.md --sanitize -o posting.clean.md", guard),
    ])
    tracker_csv = demo_tracker()
    shot("honest-stats", "NoMagicCV: honest callback statistics", [
        ("python scripts/tracker.py stats", run(["scripts/tracker.py", "stats"], {**ENV, "CV_TRACKER": tracker_csv})),
    ], width=96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
