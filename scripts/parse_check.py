#!/usr/bin/env python3
"""Parse test: see the CV the way an ATS does (R-PARSE-01..04).

Extracts text from a PDF or DOCX and flags: image-only PDFs, missing standard headings,
contact details missing from the body (or only in the header/footer), column layouts,
tables/text boxes/images, and, with --source, content lost or reordered versus the CV source.

Usage: parse_check.py FILE.pdf|FILE.docx [--source cv.md] [--json]
Exit code 0 = no errors, 1 = errors, 2 = cannot read the file.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cvlib  # noqa: E402

HEADINGS = {
    "experience": ["experience", "professional experience", "work experience", "employment history"],
    "education": ["education"],
    "skills": ["skills", "technical skills", "core skills"],
    "summary": ["summary", "professional summary", "profile"],
}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def pdf_text(path: Path) -> tuple[str, str]:
    """Return (reading-order text, layout text)."""
    if shutil.which("pdftotext"):
        # Ask for UTF-8 and decode it as UTF-8: the locale default (cp1252 on Windows) turns "–" into "â€“".
        run = lambda *a: subprocess.run(["pdftotext", "-enc", "UTF-8", *a, str(path), "-"], capture_output=True,
                                        encoding="utf-8").stdout
        plain, layout = run(), run("-layout")
        return plain, layout
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install poppler (pdftotext), or pypdf into the Python that runs NoMagicCV (`python -m pip install pypdf`).") from exc
    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return text, text


def docx_text(path: Path) -> tuple[str, str, dict]:
    try:
        import docx
    except ImportError as exc:
        raise RuntimeError("Install python-docx into the Python that runs NoMagicCV (`python -m pip install python-docx`) to check .docx files.") from exc
    d = docx.Document(str(path))
    body = "\n".join(p.text for p in d.paragraphs)
    hf = []
    for s in d.sections:
        hf += [p.text for p in s.header.paragraphs] + [p.text for p in s.footer.paragraphs]
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    extras = {
        "tables": len(d.tables),
        "textboxes": xml.count("txbxContent"),
        "images": len(d.inline_shapes) + xml.count("<wp:anchor"),
        "header_footer": "\n".join(hf),
    }
    return body, body, extras


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w%$.+@ ]", " ", s.lower())).strip()


def check(path: str, source: str | None = None) -> dict:
    p = Path(path)
    errors, warnings = [], []
    extras: dict = {}
    if p.suffix.lower() == ".pdf":
        text, layout = pdf_text(p)
    elif p.suffix.lower() == ".docx":
        text, layout, extras = docx_text(p)
    else:
        raise RuntimeError("Only .pdf and .docx are supported.")

    if len(text.strip()) < 200:
        errors.append(["R-PARSE-04", "Almost no text extracted: the file may be an image or scanned PDF."])

    lines = [ln.strip().lower() for ln in text.splitlines() if ln.strip()]
    for key, names in HEADINGS.items():
        if not any(ln.rstrip(":") in names for ln in lines):
            (errors if key in ("experience", "education") else warnings).append(
                ["R-PARSE-02", f"No standard '{key.title()}' heading found as its own line."])

    if not EMAIL_RE.search(text):
        hf = extras.get("header_footer", "")
        if EMAIL_RE.search(hf):
            errors.append(["R-PARSE-03", "Email is only in the page header/footer; many parsers skip those."])
        else:
            errors.append(["R-PARSE-03", "No email address found in the extracted text."])
    if not PHONE_RE.search(text):
        warnings.append(["R-PARSE-03", "No phone number found in the extracted text."])

    wide_gap_lines = sum(1 for ln in layout.splitlines() if len(re.findall(r"\S {6,}\S", ln)) >= 1 and len(ln.strip()) > 40)
    if wide_gap_lines > 8:
        warnings.append(["R-PARSE-01", f"{wide_gap_lines} lines look like side-by-side columns; use a single column."])
    if extras.get("tables"):
        warnings.append(["R-PARSE-01", f"{extras['tables']} table(s) found; parsers often scramble tables."])
    if extras.get("textboxes"):
        errors.append(["R-PARSE-01", f"{extras['textboxes']} text box(es) found; their text is often lost."])
    if extras.get("images"):
        warnings.append(["R-PARSE-01", f"{extras['images']} image(s) or icons found; parsers ignore them."])

    if source:
        flat = norm(text)
        pos = 0
        missing, reordered = [], []
        for ln in cvlib.parse_cv(source):
            if ln.kind not in ("bullet", "role", "text") or ln.section == "":
                continue
            key = norm(cvlib.strip_markdown(ln.text))[:50]
            if len(key) < 12:
                continue
            found = flat.find(key)
            if found < 0:
                missing.append(ln.no)
            elif found < pos:
                reordered.append(ln.no)
            else:
                pos = found
        if missing:
            errors.append(["R-PARSE-04", f"Source lines missing from extracted text: {missing[:10]}"])
        if reordered:
            warnings.append(["R-PARSE-04", f"Source lines out of order in extracted text: {reordered[:10]}"])

    return {"file": str(p), "chars": len(text), "errors": errors, "warnings": warnings, "text_preview": text[:600]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--source")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        res = check(a.file, a.source)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"parse_check: {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        for rule, msg in res["errors"]:
            print(f"ERROR  [{rule}] {msg}")
        for rule, msg in res["warnings"]:
            print(f"WARN   [{rule}] {msg}")
        if not res["errors"]:
            print(f"OK     {a.file}: {res['chars']} characters parsed ({len(res['warnings'])} warnings).")
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
