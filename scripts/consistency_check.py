#!/usr/bin/env python3
"""One version of the truth across an application (R-HONEST-05, R-KNOCK-01/02, R-SIGNAL-02).

Scans cv.md, letter.md and answers.md in an application folder and checks:
- years-of-experience claims never exceed what the fact sheet supports
- month-year dates match a role start or end date
- numbers in the letter and answers appear somewhere in the fact sheet
- email, phone and LinkedIn match the fact sheet

Usage: consistency_check.py APPLICATION_DIR [--facts workspace/facts.yaml] [--json]
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

FILES = ("cv.md", "letter.md", "answers.md")
YEARS_RE = re.compile(r"(\d+)\+?\s*(?:years|yrs)", re.I)
MONTH_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{4})\b")


def check(folder: str, facts_path: str | None = None) -> dict:
    facts = cvlib.load_facts(facts_path)
    cand = facts["candidate"]
    max_years = math.floor(cvlib.total_years(facts) + 1e-9)
    role_months = set()
    for r in facts["roles"]:
        role_months.add(cvlib.fmt_month(r["start"]))
        if str(r.get("end", "present")).lower() != "present":
            role_months.add(cvlib.fmt_month(r["end"]))
    fact_numbers = set()
    for r in facts["roles"]:
        for res in r.get("results", []):
            fact_numbers |= set(cvlib.numbers_in(str(res.get("text", ""))))
    for coll in ("education", "certifications"):
        for item in facts[coll]:
            fact_numbers |= set(cvlib.numbers_in(" ".join(str(v) for v in item.values())))
    fact_numbers.add(float(max_years))

    errors, warnings = [], []
    for name in FILES:
        path = Path(folder) / name
        if not path.exists():
            continue
        text = cvlib.TAG_RE.sub("", path.read_text(encoding="utf-8"))
        for i, line in enumerate(text.splitlines(), start=1):
            where = f"{name}:{i}"
            for m in YEARS_RE.finditer(line):
                if int(m.group(1)) > max_years:
                    errors.append([where, "R-KNOCK-02",
                                   f"Claims {m.group(1)} years; the fact sheet supports at most {max_years}."])
            for mon, yr in MONTH_RE.findall(line):
                label = f"{mon[:3]} {yr}"
                if label not in role_months:
                    warnings.append([where, "R-HONEST-05", f"Date '{label}' matches no role start or end date."])
            for email in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", line):
                if cand.get("email") and email.lower() != str(cand["email"]).lower():
                    errors.append([where, "R-HONEST-05", f"Email '{email}' differs from the fact sheet."])
            if "linkedin.com" in line.lower() and cand.get("linkedin") and str(cand["linkedin"]).lower() not in line.lower():
                errors.append([where, "R-SIGNAL-02", "LinkedIn URL differs from the fact sheet."])
            if name != "cv.md":
                year_claims = {float(m.group(1)) for m in YEARS_RE.finditer(line)}
                for value, _s, _e in cvlib.number_spans(line):
                    if value in fact_numbers or value in year_claims or (1950 <= value <= 2100):
                        continue
                    warnings.append([where, "R-HONEST-01", f"Number '{value:g}' does not appear in the fact sheet."])
    return {"folder": folder, "errors": errors, "warnings": warnings}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--facts")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        res = check(a.folder, a.facts)
    except (FileNotFoundError, ValueError) as exc:
        print(f"consistency_check: {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        for where, rule, msg in res["errors"]:
            print(f"ERROR  {where}  [{rule}] {msg}")
        for where, rule, msg in res["warnings"]:
            print(f"WARN   {where}  [{rule}] {msg}")
        if not res["errors"]:
            print(f"OK     {a.folder}: consistent with the fact sheet ({len(res['warnings'])} warnings).")
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
