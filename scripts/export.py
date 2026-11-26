#!/usr/bin/env python3
"""Export a tagged CV to other open-source tools. Tags are stripped; structured data comes from facts.yaml.

Usage:
  export.py clean     CV.md [-o out.md]                 plain Markdown without provenance tags
  export.py jsonresume CV.md [-o resume.json]           JSON Resume (jsonresume.org) for Reactive Resume and others
  export.py rendercv  CV.md [-o Name_CV.yaml]           RenderCV input; then: rendercv render Name_CV.yaml
  export.py html      CV.md [-o cv.html]                single-column, ATS-friendly HTML (print-ready)
  export.py pdf       CV.md [-o First_Last_Role.pdf]    PDF via a local Chrome, Chromium or Edge (no other installs)
      --theme classic (default, single column, safest for ATS) | modern (header band + sidebar, for people)

Only lines that passed fact_check should be exported. Run fact_check.py first.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cvlib  # noqa: E402


def structure(cv_path: str, facts: dict) -> dict:
    """Read the CV's choices (what is included, in what order, wording) and join with facts."""
    idx = cvlib.fact_index(facts)
    lines = cvlib.parse_cv(cv_path)
    out = {"headline": "", "summary": [], "highlights": [], "roles": [], "education": [],
           "certifications": [], "skills": [], "languages": []}
    header = [ln for ln in lines if ln.section == "" and ln.kind == "text"]
    if header:
        out["headline"] = header[0].text
    current = None
    for ln in lines:
        sec, text = ln.section, cvlib.strip_markdown(ln.text)
        if ln.kind in ("blank", "h1", "h2") or sec == "":
            continue
        if sec == "summary":
            out["summary"].append(text)
        elif sec == "highlights" and ln.kind == "bullet":
            out["highlights"].append(text)
        elif "experience" in sec:
            if ln.kind == "role":
                rid = (ln.tags.get("role") or [None])[0]
                role = idx.get(rid, {}).get("obj") if rid else None
                if role:
                    current = {"role": role, "highlights": []}
                    out["roles"].append(current)
            elif ln.kind == "bullet" and current:
                current["highlights"].append(text)
        elif sec.startswith("education"):
            eid = (ln.tags.get("edu") or [None])[0]
            if eid in idx:
                out["education"].append(idx[eid]["obj"])
        elif sec.startswith("certification"):
            cid = (ln.tags.get("cert") or [None])[0]
            if cid in idx:
                out["certifications"].append(idx[cid]["obj"])
        elif sec.startswith("skill"):
            label, _, rest = text.partition(":")
            if rest:
                out["skills"].append({"label": label.strip(), "items": [x.strip() for x in rest.split(",") if x.strip()]})
            else:
                out["skills"].append({"label": "Skills", "items": [x.strip() for x in text.split(",") if x.strip()]})
        elif sec.startswith("language"):
            out["languages"] = facts["languages"]
    return out


def to_jsonresume(s: dict, facts: dict) -> dict:
    c = facts["candidate"]
    city, _, region = str(c.get("location", "")).partition(",")
    basics = {"name": c.get("name", ""), "label": s["headline"].split("|")[0].strip(), "email": c.get("email", ""),
              "phone": c.get("phone", ""), "summary": " ".join(s["summary"]),
              "location": {"city": city.strip(), "region": region.strip()}, "profiles": []}
    if c.get("linkedin"):
        url = c["linkedin"] if str(c["linkedin"]).startswith("http") else f"https://{c['linkedin']}"
        basics["profiles"].append({"network": "LinkedIn", "url": url})
    work = []
    for r in s["roles"]:
        role = r["role"]
        item = {"name": role["employer"], "position": role["title"], "location": role.get("location", ""),
                "startDate": str(role["start"]), "highlights": r["highlights"]}
        if str(role.get("end", "present")).lower() != "present":
            item["endDate"] = str(role["end"])
        work.append(item)
    return {
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
        "basics": basics,
        "work": work,
        "education": [{"institution": e.get("institution", ""), "studyType": e.get("degree", ""),
                       "endDate": str(e.get("year", ""))} for e in s["education"]],
        "certificates": [{"name": x.get("name", ""), "issuer": x.get("issuer", ""), "date": str(x.get("year", ""))}
                         for x in s["certifications"]],
        "skills": [{"name": g["label"], "keywords": g["items"]} for g in s["skills"]],
        "languages": [{"language": l["name"], "fluency": l.get("level", "")} for l in s["languages"]],
    }


def to_rendercv(s: dict, facts: dict) -> dict:
    c = facts["candidate"]
    cv: dict = {"name": c.get("name", ""), "location": c.get("location", ""), "email": c.get("email", "")}
    if c.get("phone"):
        cv["phone"] = re.sub(r"[^\d+]", "", str(c["phone"]))
    if c.get("linkedin"):
        cv["social_networks"] = [{"network": "LinkedIn", "username": str(c["linkedin"]).rstrip("/").split("/")[-1]}]
    sections: dict = {}
    if s["summary"]:
        sections["summary"] = [" ".join(s["summary"])]
    if s["highlights"]:
        sections["highlights"] = [{"bullet": h} for h in s["highlights"]]
    if s["roles"]:
        sections["experience"] = [{
            "company": r["role"]["employer"], "position": r["role"]["title"],
            "location": r["role"].get("location", ""), "start_date": str(r["role"]["start"]),
            "end_date": str(r["role"].get("end", "present")), "highlights": r["highlights"],
        } for r in s["roles"]]
    if s["education"]:
        sections["education"] = [{"institution": e.get("institution", ""), "area": e.get("degree", ""),
                                  "end_date": str(e.get("year", ""))} for e in s["education"]]
    if s["certifications"]:
        sections["certifications"] = [{"bullet": f"{x.get('name','')} ({x.get('acronym','')}), {x.get('issuer','')}, {x.get('year','')}"}
                                      for x in s["certifications"]]
    if s["skills"]:
        sections["skills"] = [{"label": g["label"], "details": ", ".join(g["items"])} for g in s["skills"]]
    if s["languages"]:
        sections["languages"] = [{"label": l["name"], "details": l.get("level", "")} for l in s["languages"]]
    cv["sections"] = sections
    return {"cv": cv}


BASE_CSS = """
@page { size: A4; margin: 14mm 15mm 14mm 15mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Inter", "Source Sans 3", "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: #1f2937;
       font-size: 10.6pt; line-height: 1.5; margin: 0; }
h1 { font-size: 28pt; line-height: 1.05; margin: 0; color: #0f2a4a; font-weight: 750; }
.headline { font-size: 12.5pt; font-weight: 600; color: #334e68; margin: 5pt 0 7pt; }
.contact { font-size: 9.6pt; color: #475569; margin: 0; }
.contact span { white-space: nowrap; }
.contact span + span::before { content: "|"; color: #94a3b8; margin: 0 6pt; }
h2 { font-size: 10pt; text-transform: uppercase; letter-spacing: 0; color: #0f2a4a; font-weight: 700;
     margin: 15pt 0 7pt; padding-bottom: 3pt; border-bottom: 1.2pt solid #c7d2df; }
p { margin: 0 0 3pt; }
ul { margin: 3pt 0 0 0; padding-left: 13pt; }
li { margin: 0 0 3.6pt; padding-left: 1pt; }
li::marker { color: #64748b; }
.role { margin: 0 0 12pt; break-inside: avoid; }
/* Title line, then dates on their own line, both in normal text flow. Right-aligned (flex) dates were
   extracted out of reading order with some fonts, and tabular-nums glyphs lost their digits in pypdf. */
.role-head { display: block; }
.role-title { font-weight: 700; color: #0f172a; font-size: 11pt; }
.dates { display: block; white-space: nowrap; color: #475569; font-size: 9.8pt; }
.org { color: #334e68; font-weight: 500; }
.item { margin: 0 0 7pt; }
.item strong { color: #0f172a; }
.muted { color: #64748b; }
.skill-group { margin: 0 0 7pt; }
.skill-group b { display: block; color: #0f2a4a; font-size: 9pt; margin-bottom: 1pt; }
"""

THEMES = {
    "classic": BASE_CSS + """
header { padding-bottom: 9pt; border-bottom: 2.2pt solid #0f2a4a; margin-bottom: 2pt; }
.skills-inline .skill-group b { display: inline; margin: 0; }   /* one line of text: "Label: items" */
""",
    "modern": BASE_CSS + """
header { background: #0f2a4a; color: #fff; margin: 0 0 16pt; padding: 8mm 8mm 7mm; border-radius: 3pt; }
header h1 { color: #fff; }
header .headline { color: #c7d7ea; }
header .contact { color: #dbe5f1; font-size: 8.7pt; }
header .contact span + span::before { color: #7f97b3; }
.cols { display: grid; grid-template-columns: 32% 1fr; column-gap: 16pt; }
.cols > main { grid-column: 2; grid-row: 1; }
.cols > aside { grid-column: 1; grid-row: 1; border-right: 1pt solid #dbe3ec; padding-right: 12pt; }
.cols h2:first-child { margin-top: 2pt; }
aside h2 { font-size: 9pt; }
aside p, aside .skill-group { font-size: 9.8pt; }
""",
}


def esc(text: str) -> str:
    import html
    return html.escape(str(text))


def _sections(s: dict, facts: dict) -> dict[str, str]:
    out = {}
    if s["summary"]:
        out["summary"] = "<h2>Summary</h2>" + "".join(f"<p>{esc(x)}</p>" for x in s["summary"])
    if s["highlights"]:
        out["highlights"] = "<h2>Highlights</h2><ul>" + "".join(f"<li>{esc(x)}</li>" for x in s["highlights"]) + "</ul>"
    if s["roles"]:
        parts = ["<h2>Experience</h2>"]
        for r in s["roles"]:
            role = r["role"]
            dates = f"{cvlib.fmt_month(role['start'])} – {cvlib.fmt_month(role.get('end', 'present'))}"
            where = ", ".join(x for x in (role["employer"], role.get("location", "")) if x)
            parts.append(f"<div class='role'><div class='role-head'><span><span class='role-title'>{esc(role['title'])}</span>"
                         f"<span class='org'>, {esc(where)}</span></span> <span class='dates'>{esc(dates)}</span></div>")
            if r["highlights"]:
                parts.append("<ul>" + "".join(f"<li>{esc(h)}</li>" for h in r["highlights"]) + "</ul>")
            parts.append("</div>")
        out["experience"] = "".join(parts)
    if s["education"]:
        out["education"] = "<h2>Education</h2>" + "".join(
            f"<p class='item'><strong>{esc(e.get('degree', ''))}</strong><br>{esc(e.get('institution', ''))}"
            f"{', ' + esc(e['location']) if e.get('location') else ''}<span class='muted'> | {esc(e.get('year', ''))}</span></p>"
            for e in s["education"])
    if s["certifications"]:
        out["certifications"] = "<h2>Certifications</h2>" + "".join(
            f"<p class='item'>{esc(x.get('name', ''))}{' (' + esc(x['acronym']) + ')' if x.get('acronym') else ''}"
            f"<br><span class='muted'>{esc(x.get('issuer', ''))} | {esc(x.get('year', ''))}</span></p>"
            for x in s["certifications"])
    if s["skills"]:
        out["skills"] = "<h2>Skills</h2>" + "".join(
            f"<div class='skill-group'><b>{esc(g['label'])}:</b> {esc(', '.join(g['items']))}</div>" for g in s["skills"])
    if s["languages"]:
        out["languages"] = "<h2>Languages</h2><p>" + ", ".join(
            f"{esc(l['name'])} ({esc(l.get('level', ''))})" for l in s["languages"]) + "</p>"
    return out


def to_html(s: dict, facts: dict, theme: str = "classic") -> str:
    c = facts["candidate"]
    contact = " ".join(f"<span>{esc(x)}</span>" for x in (c.get("location"), c.get("work_authorization"),
                                                          c.get("phone"), c.get("email"), c.get("linkedin")) if x)
    head = (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>{esc(c.get('name', 'CV'))}</title>"
            f"<style>{THEMES[theme]}</style></head><body>"
            f"<header><h1>{esc(c.get('name', ''))}</h1><p class='headline'>{esc(s['headline'])}</p>"
            f"<p class='contact'>{contact}</p></header>")
    sec = _sections(s, facts)
    if theme == "modern":
        main = "".join(sec.get(k, "") for k in ("summary", "highlights", "experience"))
        side = "".join(sec.get(k, "") for k in ("skills", "certifications", "education", "languages"))
        body = f"<div class='cols'><main>{main}</main><aside>{side}</aside></div>"
    else:
        order = ("summary", "highlights", "experience", "education", "certifications", "skills", "languages")
        body = "".join(sec.get(k, "") for k in order).replace("<h2>Skills</h2>", "<h2>Skills</h2><div class='skills-inline'>", 1)
        if "skills-inline" in body:
            body = body.replace("<h2>Languages</h2>", "</div><h2>Languages</h2>", 1) if "<h2>Languages</h2>" in body else body + "</div>"
    return head + body + "</body></html>\n"


def find_browser() -> str | None:
    import shutil as _sh
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge", "chrome"):
        if _sh.which(name):
            return _sh.which(name)
    for path in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Chromium.app/Contents/MacOS/Chromium",
                 "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                 r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if Path(path).exists():
            return path
    return None


def html_to_pdf(html_text: str, pdf_path: Path) -> None:
    import subprocess, tempfile
    browser = find_browser()
    if not browser:
        raise SystemExit("No Chrome, Chromium or Edge found. Use `export.py rendercv` or print the HTML to PDF.")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "cv.html"
        src.write_text(html_text, encoding="utf-8")
        pdf_path.unlink(missing_ok=True)      # so an old file is never mistaken for this run's output
        res = subprocess.run([browser, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                              f"--print-to-pdf={pdf_path.resolve()}", src.resolve().as_uri()],
                             capture_output=True, text=True, errors="replace")
        written = pdf_path.exists() and pdf_path.stat().st_size > 0
        if not written:
            raise SystemExit(f"{browser} could not print the PDF (exit {res.returncode}).\n{(res.stderr or '')[-1500:]}\n"
                             "Alternatives: `export.py html` then print to PDF, or `export.py rendercv`.")
        if res.returncode != 0:
            # Seen on macOS CI: Chrome writes the whole PDF, then its shutdown watchdog fires and it exits 2.
            print(f"Note: the browser exited with code {res.returncode} after writing the PDF; run parse_check.py on it.",
                  file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("format", choices=["clean", "jsonresume", "rendercv", "html", "pdf"])
    ap.add_argument("cv")
    ap.add_argument("--facts")
    ap.add_argument("-o", "--output")
    ap.add_argument("--theme", default="classic", choices=["classic", "modern"],
                    help="classic: single column, safest for applicant tracking systems (default). "
                         "modern: header band and sidebar, for emailing a person directly")
    a = ap.parse_args()
    if a.format == "clean":
        data = cvlib.clean_cv_text(a.cv)
    else:
        facts = cvlib.load_facts(a.facts)
        s = structure(a.cv, facts)
        if a.format == "jsonresume":
            data = json.dumps(to_jsonresume(s, facts), indent=2, ensure_ascii=False) + "\n"
        elif a.format in ("html", "pdf"):
            data = to_html(s, facts, a.theme)
            if a.format == "pdf":
                role = s["headline"].split("|")[0].strip() or "CV"
                name = "_".join(w for w in re.sub(r"[^A-Za-z0-9 ]", "", f"{facts['candidate'].get('name', '')} {role}").split())
                out = Path(a.output or f"{name}.pdf")
                html_to_pdf(data, out)
                print(f"Wrote {out}")
                return 0
        else:
            data = yaml.safe_dump(to_rendercv(s, facts), sort_keys=False, allow_unicode=True)
    if a.output:
        Path(a.output).write_text(data, encoding="utf-8")
        print(f"Wrote {a.output}")
    else:
        sys.stdout.write(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
