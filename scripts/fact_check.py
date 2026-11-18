#!/usr/bin/env python3
"""Check that every fact in a CV traces to workspace/facts.yaml.

Enforces R-HONEST-01 (no invented facts), R-HONEST-02 (official titles only),
R-HONEST-03 (approximate numbers marked) and R-SIGNAL-05 (current dates honest).

Usage: fact_check.py CV.md [--facts workspace/facts.yaml] [--json]
Exit code 0 = clean, 1 = errors found, 2 = usage problem.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cvlib  # noqa: E402

FACT_SECTIONS = {"summary", "highlights", "experience", "professional experience", "projects", "relevant projects"}
YEARS_RE = re.compile(r"(\d+)\+?\s*(?:years|yrs)", re.I)


class Report:
    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def err(self, line, rule, msg):
        self.errors.append({"line": line, "rule": rule, "message": msg})

    def warn(self, line, rule, msg):
        self.warnings.append({"line": line, "rule": rule, "message": msg})


def check(cv_path: str, facts_path: str | None = None) -> Report:
    rep = Report()
    facts = cvlib.load_facts(facts_path)
    idx = cvlib.fact_index(facts)
    cand = facts["candidate"]
    terms = cvlib.known_terms(facts)
    years_total = cvlib.total_years(facts)
    lines = cvlib.parse_cv(cv_path)
    current_role: str | None = None

    # ---- header block
    header = [ln for ln in lines if ln.section == "" and ln.kind != "blank"]
    if header and header[0].kind == "h1":
        name = cvlib.strip_markdown(header[0].text)
        if cand.get("name") and name.lower() != str(cand["name"]).lower():
            rep.err(header[0].no, "R-HONEST-01", f"Name '{name}' does not match facts ('{cand['name']}').")
    for ln in header:
        for email in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", ln.text):
            if cand.get("email") and email.lower() != str(cand["email"]).lower():
                rep.err(ln.no, "R-HONEST-05", f"Email '{email}' differs from facts.")
        if cand.get("linkedin") and "linkedin.com" in ln.text.lower() and str(cand["linkedin"]).lower() not in ln.text.lower():
            rep.err(ln.no, "R-HONEST-05", "LinkedIn URL differs from facts.")

    for ln in lines:
        if ln.kind in ("blank", "h1", "h2") or ln.section == "":
            continue
        sec = ln.section
        fids = ln.tags.get("f", [])
        for fid in fids:
            if fid not in idx:
                rep.err(ln.no, "R-HONEST-01", f"Tag cites unknown fact id '{fid}'.")

        # ---- role lines
        if ln.kind == "role":
            rid = (ln.tags.get("role") or [None])[0]
            if not rid:
                rep.err(ln.no, "R-HONEST-02", "Role line has no <!-- role:ID --> tag.")
                current_role = None
                continue
            if rid not in idx or idx[rid]["kind"] != "role":
                rep.err(ln.no, "R-HONEST-01", f"Unknown role id '{rid}'.")
                current_role = None
                continue
            current_role = rid
            role = idx[rid]["obj"]
            body = ln.text[4:].replace("**", "").strip()
            expected = f"{role['title']}, {role['employer']}"
            if not body.startswith(expected):
                rep.err(ln.no, "R-HONEST-02",
                        f"Role line must start with the official title and employer exactly: '{expected}'.")
            m = re.search(r"\|\s*([A-Z][a-z]{2} \d{4})\s*[-–—]\s*(Present|[A-Z][a-z]{2} \d{4})\s*$", body)
            if not m:
                rep.err(ln.no, "R-HONEST-01", "Role line needs dates as 'Mon YYYY - Mon YYYY' or '- Present'.")
            else:
                exp_start, exp_end = cvlib.fmt_month(role["start"]), cvlib.fmt_month(role.get("end", "present"))
                if m.group(1) != exp_start or m.group(2) != exp_end:
                    rep.err(ln.no, "R-SIGNAL-05",
                            f"Dates '{m.group(1)} - {m.group(2)}' differ from facts '{exp_start} - {exp_end}'.")
            continue

        # ---- fact-bearing sections
        if sec in FACT_SECTIONS and ln.kind in ("bullet", "text"):
            nums = list(cvlib.number_spans(ln.text))
            if ln.kind == "bullet" and not fids:
                rep.err(ln.no, "R-HONEST-01", "Bullet has no <!-- f:ID --> tag; every bullet must trace to a fact.")
                continue
            if nums and not fids and "calc" not in ln.tags:
                rep.err(ln.no, "R-HONEST-01", "Line contains numbers but cites no fact.")
                continue
            cited = [idx[f] for f in fids if f in idx]
            allowed = set()
            approx_nums = set()
            for c in cited:
                for n in cvlib.numbers_in(c["text"]):
                    allowed.add(n)
                    if c.get("approximate"):
                        approx_nums.add(n)
                if c.get("role") and c["role"] in idx:
                    role = idx[c["role"]]["obj"]
                    for key in ("start", "end"):
                        val = str(role.get(key, ""))
                        if re.match(r"\d{4}", val):
                            allowed.add(float(val[:4]))
            years_claims = {float(m.group(1)) for m in YEARS_RE.finditer(ln.text)}
            if years_claims:
                if "calc" in ln.tags and "years" in ln.tags.get("calc", []):
                    for y in years_claims:
                        if y > math.floor(years_total + 1e-9):
                            rep.err(ln.no, "R-HONEST-01",
                                    f"Claims {y:g} years; facts support at most {math.floor(years_total)}.")
                        allowed.add(y)
                elif not any(y in allowed for y in years_claims):
                    rep.err(ln.no, "R-HONEST-01", "Years-of-experience claim needs a <!-- calc:years --> tag.")
            for value, start, _end in nums:
                if value not in allowed:
                    rep.err(ln.no, "R-HONEST-01",
                            f"Number '{value:g}' is not in the cited fact(s) {fids or '[]'}.")
                elif value in approx_nums and not cvlib.has_approx_marker(ln.text, start):
                    rep.err(ln.no, "R-HONEST-03",
                            f"'{value:g}' is approximate in facts; write it as '~{value:g}' or 'about {value:g}'.")
            if sec != "summary" and sec != "highlights" and current_role:
                for c in cited:
                    if c.get("role") and c["role"] != current_role:
                        rep.warn(ln.no, "R-HONEST-01",
                                 f"Bullet under '{current_role}' cites a fact from '{c['role']}'.")
            continue

        # ---- education / certifications
        if sec.startswith("education") and ln.kind in ("text", "bullet"):
            ids = ln.tags.get("edu", [])
            if not ids or ids[0] not in idx:
                rep.err(ln.no, "R-HONEST-01", "Education line needs a valid <!-- edu:ID --> tag.")
                continue
            e = idx[ids[0]]["obj"]
            for key in ("degree", "institution"):
                if e.get(key) and str(e[key]).lower() not in ln.text.lower():
                    rep.err(ln.no, "R-HONEST-01", f"Education {key} must read '{e[key]}'.")
            years = re.findall(r"\b(?:19|20)\d{2}\b", ln.text)
            if years and e.get("year") and str(e["year"]) not in years:
                rep.err(ln.no, "R-HONEST-01", f"Education year must be {e['year']}.")
            continue
        if sec.startswith("certification") and ln.kind in ("text", "bullet"):
            ids = ln.tags.get("cert", [])
            if not ids or ids[0] not in idx:
                rep.err(ln.no, "R-HONEST-01", "Certification line needs a valid <!-- cert:ID --> tag.")
                continue
            c = idx[ids[0]]["obj"]
            if str(c.get("name", "")).lower() not in ln.text.lower():
                rep.err(ln.no, "R-MATCH-04", f"Certification must be written in full: '{c.get('name')}'.")
            years = re.findall(r"\b(?:19|20)\d{2}\b", ln.text)
            if years and c.get("year") and str(c["year"]) not in years:
                rep.err(ln.no, "R-HONEST-01", f"Certification year must be {c['year']}.")
            continue

        # ---- skills
        if sec.startswith("skill") and ln.kind in ("text", "bullet"):
            body = cvlib.strip_markdown(ln.text)
            if ":" in body:
                body = body.split(":", 1)[1]
            for item in [x.strip() for x in re.split(r"[,;|]", body) if x.strip()]:
                if item.lower() not in terms:
                    rep.err(ln.no, "R-HONEST-01", f"Skill '{item}' is not in facts (skills, role tools or certifications).")
            continue

        # ---- languages
        if sec.startswith("language") and ln.kind in ("text", "bullet"):
            known = {str(l["name"]).lower(): str(l.get("level", "")).lower() for l in facts["languages"]}
            for name, level in re.findall(r"([A-Za-zÀ-ÿ ]+?)\s*\(([^)]+)\)", cvlib.strip_markdown(ln.text)):
                key = name.strip(" ,|").lower()
                if key not in known:
                    rep.err(ln.no, "R-HONEST-01", f"Language '{name.strip()}' is not in facts.")
                elif known[key] and level.strip().lower() != known[key]:
                    rep.err(ln.no, "R-HONEST-01", f"{name.strip()} level must be '{known[key]}'.")
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cv")
    ap.add_argument("--facts", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        rep = check(a.cv, a.facts)
    except (FileNotFoundError, ValueError) as exc:
        print(f"fact_check: {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings}, indent=2))
    else:
        for e in rep.errors:
            print(f"ERROR  {a.cv}:{e['line']}  [{e['rule']}] {e['message']}")
        for w in rep.warnings:
            print(f"WARN   {a.cv}:{w['line']}  [{w['rule']}] {w['message']}")
        if not rep.errors:
            print(f"OK     {a.cv}: every fact traces to the fact sheet ({len(rep.warnings)} warnings).")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
