#!/usr/bin/env python3
"""Regenerate the README visuals in docs/assets/ from real runs.

Every image is produced by running the actual scripts on the fictional eval
cases, so the visuals can't drift from what the code does:
  terminal SVGs  fact-check.svg, posting-guard.svg, honest-stats.svg, final-cv-check.svg
  final CV       cv-example.png (PDF exported by scripts/export.py, then rasterised)

Needs a local Chrome/Chromium/Edge (for the PDF), pdftoppm (poppler) and Pillow.
Usage: python docs/make_screenshots.py
"""
from __future__ import annotations

import csv
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
CASE = "evals/cases/data-analyst"
ENV = {**os.environ, "CV_TODAY": "2026-11-19", "NO_COLOR": "1", "PYTHONUTF8": "1"}

# ------------------------------------------------------------------ terminal renderer
FONT = "'JetBrains Mono','SFMono-Regular','Cascadia Code',Menlo,Consolas,'DejaVu Sans Mono',monospace"
CW, LH, FS, PAD, HEAD = 8.43, 22, 14, 22, 44
COLORS = {
    "bg": "#0b1020", "head": "#121a2f", "border": "#24304d", "text": "#e2e8f0", "dim": "#8b9bb4",
    "prompt": "#2dd4bf", "cmd": "#f8fafc", "rule": "#c4b5fd", "ref": "#7dd3fc", "note": "#5eead4",
}
PILLS = {"ERROR": ("#4c0519", "#fda4af"), "WARN": ("#422006", "#fcd34d"), "OK": ("#052e16", "#86efac")}
LABEL_COLS = 8  # pill + gap; wrapped lines hang under the message


def run(cmd: list[str], env: dict | None = None) -> str:
    out = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=env or ENV)
    return (out.stdout + out.stderr).replace(str(ROOT) + os.sep, "").replace(str(ROOT), ".").rstrip()


def tokens(msg: str) -> list[tuple[str, str]]:
    """Colour a message: rule ids, file:line refs, the rest as text."""
    out = []
    for part in re.split(r"(\[R-[A-Z]+-\d{2}\]|\b[\w./-]+\.(?:md|pdf|yaml):\d+\b)", msg):
        if not part:
            continue
        if part.startswith("[R-"):
            out.append((part, "rule"))
        elif re.match(r"[\w./-]+\.(md|pdf|yaml):\d+", part):
            out.append((part, "ref"))
        else:
            out.append((part, "text"))
    return out


def wrap(segs: list[tuple[str, str]], width: int) -> list[list[tuple[str, str]]]:
    words = [(w, cls) for text, cls in segs for w in re.findall(r"\S+\s*|\s+", text)]
    lines, cur, n = [], [], 0
    for w, cls in words:
        if n + len(w.rstrip()) > width and cur:
            lines.append(cur)
            cur, n = [], 0
            w = w.lstrip()
        cur.append((w, cls))
        n += len(w)
    if cur:
        lines.append(cur)
    return lines


def render(title: str, steps: list[tuple[str, str]], cols: int = 104) -> str:
    rows: list[tuple[str | None, list[tuple[str, str]]]] = []
    for i, (cmd, output) in enumerate(steps):
        if i:
            rows.append((None, []))
        rows.append(("$", [(cmd, "cmd")]))
        for line in output.splitlines():
            m = re.match(r"^(ERROR|WARN|OK)\s+(.*)$", line)
            if m:
                for j, seg in enumerate(wrap(tokens(m.group(2)), cols - LABEL_COLS)):
                    rows.append((m.group(1) if j == 0 else "", seg))
            else:
                cls = "note" if line.startswith(("No winner", "Too few", "Sanitized")) else "text"
                for seg in wrap([(line, cls)], cols) or [[]]:
                    rows.append((None, seg))
    width = PAD * 2 + cols * CW
    height = HEAD + PAD + len(rows) * LH + PAD - 6
    hy = HEAD / 2 + 5
    svg = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{width:.0f}' height='{height:.0f}' "
           f"viewBox='0 0 {width:.0f} {height:.0f}' role='img' aria-label='NoMagicCV {html.escape(title)}'>",
           f"<rect x='.5' y='.5' width='{width - 1:.0f}' height='{height - 1:.0f}' rx='12' fill='{COLORS['bg']}' "
           f"stroke='{COLORS['border']}'/>",
           f"<path d='M12.5 .5h{width - 25:.0f}a12 12 0 0 1 12 12v{HEAD - 12}h-{width - 1:.0f}v-{HEAD - 12}"
           f"a12 12 0 0 1 12-12z' fill='{COLORS['head']}'/>",
           f"<line x1='0' y1='{HEAD}' x2='{width:.0f}' y2='{HEAD}' stroke='{COLORS['border']}'/>",
           f"<g font-family=\"{FONT}\" font-size='{FS}'>",
           f"<text x='{PAD}' y='{hy:.0f}' font-weight='700' fill='{COLORS['prompt']}'>nomagic-cv</text>",
           f"<text x='{PAD + 11 * CW:.0f}' y='{hy:.0f}' fill='{COLORS['dim']}'>{html.escape(title)}</text>",
           f"<text x='{width - PAD:.0f}' y='{hy:.0f}' text-anchor='end' fill='{COLORS['dim']}' font-size='12'>"
           f"real output</text>"]
    y = HEAD + PAD + 10
    for pill, segs in rows:
        x = PAD
        if pill == "$":
            svg.append(f"<text x='{x}' y='{y}' font-weight='700' fill='{COLORS['prompt']}'>❯</text>")
            x += 2 * CW
        elif pill:
            bg, fg = PILLS[pill]
            svg.append(f"<rect x='{x - 3}' y='{y - 15}' width='{len(pill) * CW + 8:.1f}' height='20' rx='4' fill='{bg}'/>")
            svg.append(f"<text x='{x + 1}' y='{y}' font-weight='700' fill='{fg}'>{pill}</text>")
            x += LABEL_COLS * CW
        elif pill == "":
            x += LABEL_COLS * CW
        col = 0
        for text, cls in segs:
            weight = " font-weight='700'" if cls == "cmd" else ""
            svg.append(f"<text x='{x + col * CW:.1f}' y='{y}' xml:space='preserve' fill='{COLORS[cls]}'{weight}>"
                       f"{html.escape(text)}</text>")
            col += len(text)
        y += LH
    svg.append("</g></svg>")
    return "\n".join(svg) + "\n"


def save(name: str, svg: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / f"{name}.svg").write_text(svg, encoding="utf-8")
    print(f"wrote docs/assets/{name}.svg")


# ------------------------------------------------------------------ fixtures
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
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return str(path)


def cv_image(tmp: Path) -> tuple[str, str]:
    """Export the honest example CV to PDF, parse-check it, and rasterise page 1."""
    pdf = tmp / "Jordan_Lee_Business_Intelligence_Analyst.pdf"
    export = run(["scripts/export.py", "pdf", f"{CASE}/good.md", "--facts", f"{CASE}/facts.yaml", "-o", str(pdf)])
    export = export.replace(str(tmp) + os.sep, "")
    check = run(["scripts/parse_check.py", str(pdf), "--source", f"{CASE}/good.md"]).replace(str(tmp) + os.sep, "")
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-png", "-r", "130", "-f", "1", "-l", "1", "-singlefile", str(pdf),
                        str(tmp / "page")], check=True)
        from PIL import Image, ImageChops
        img = Image.open(tmp / "page.png").convert("RGB")
        bbox = ImageChops.difference(img, Image.new("RGB", img.size, "white")).getbbox()
        if bbox:
            m = 60
            img = img.crop((max(0, bbox[0] - m), max(0, bbox[1] - m), min(img.width, bbox[2] + m),
                            min(img.height, bbox[3] + m)))
        framed = Image.new("RGB", (img.width + 2, img.height + 2), "#d1d5db")
        framed.paste(img, (1, 1))
        framed.save(ASSETS / "cv-example.png", optimize=True)
        print("wrote docs/assets/cv-example.png")
    return export, check


def main() -> int:
    facts = f"{CASE}/facts.yaml"
    save("fact-check", render("fact check", [
        ("python scripts/fact_check.py fabricated.md",
         run(["scripts/fact_check.py", f"{CASE}/fabricated.md", "--facts", facts]).replace(f"{CASE}/", "")),
        ("python scripts/fact_check.py good.md",
         run(["scripts/fact_check.py", f"{CASE}/good.md", "--facts", facts]).replace(f"{CASE}/", "")),
    ]))

    clean = Path(tempfile.mkdtemp()) / "posting.clean.md"
    guard = run(["scripts/posting_guard.py", f"{CASE}/posting_malicious.md", "--sanitize", "-o", str(clean)])
    guard = guard.replace("posting_malicious.md", "posting.md").replace(str(clean), "posting.clean.md")
    save("posting-guard", render("posting injection guard", [
        ("python scripts/posting_guard.py posting.md --sanitize", guard),
    ]))

    save("honest-stats", render("honest callback statistics", [
        ("python scripts/tracker.py stats", run(["scripts/tracker.py", "stats"], {**ENV, "CV_TRACKER": demo_tracker()})),
    ], cols=92))

    tmp = Path(tempfile.mkdtemp())
    export, check = cv_image(tmp)
    save("final-cv-check", render("export and parse test", [
        ("python scripts/export.py pdf cv.md", export),
        ("python scripts/parse_check.py Jordan_Lee_Business_Intelligence_Analyst.pdf --source cv.md", check),
    ], cols=92))
    return 0


if __name__ == "__main__":
    sys.exit(main())
