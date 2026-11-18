#!/usr/bin/env python3
"""Enforce the contribution rule: no hard rule without verified A/B evidence.

Checks rules/rules.yaml and rules/sources.yaml:
- unique ids and required fields
- every cited source exists and is verified
- strength 'default' needs at least one verified grade A or B source
- every rule id mentioned in skills/ and README.md exists
Exit 0 = clean, 1 = problems.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GRADES = {"A", "B", "C"}
STRENGTHS = {"default", "test", "guardrail"}
LAYERS = {"parse", "match", "scan", "prove", "signal", "knockout", "ai", "honesty", "measure", "security", "outreach"}


def lint(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    sources = yaml.safe_load((root / "rules/sources.yaml").read_text(encoding="utf-8"))["sources"]
    rules = yaml.safe_load((root / "rules/rules.yaml").read_text(encoding="utf-8"))["rules"]

    src_by_id = {}
    for s in sources:
        for key in ("id", "title", "url", "grade", "finding", "status"):
            if not s.get(key):
                problems.append(f"source {s.get('id', '?')}: missing '{key}'")
        if s.get("grade") not in GRADES:
            problems.append(f"source {s.get('id')}: grade must be A, B or C")
        if s.get("grade") == "A" and s.get("setting") not in ("field", "lab"):
            problems.append(f"source {s.get('id')}: grade A needs setting field|lab")
        if s.get("id") in src_by_id:
            problems.append(f"source {s['id']}: duplicate id")
        src_by_id[s.get("id")] = s

    seen = set()
    for r in rules:
        rid = r.get("id", "?")
        if rid in seen:
            problems.append(f"rule {rid}: duplicate id")
        seen.add(rid)
        if not re.fullmatch(r"R-[A-Z]+-\d{2}", rid):
            problems.append(f"rule {rid}: id must look like R-LAYER-01")
        if r.get("layer") not in LAYERS:
            problems.append(f"rule {rid}: unknown layer '{r.get('layer')}'")
        if r.get("strength") not in STRENGTHS:
            problems.append(f"rule {rid}: strength must be one of {sorted(STRENGTHS)}")
        cited = r.get("sources") or []
        for sid in cited:
            s = src_by_id.get(sid)
            if not s:
                problems.append(f"rule {rid}: unknown source '{sid}'")
            elif s.get("status") != "verified":
                problems.append(f"rule {rid}: source '{sid}' is unverified and cannot back a rule")
        if r.get("strength") == "default":
            strong = [sid for sid in cited if src_by_id.get(sid, {}).get("grade") in ("A", "B")
                      and src_by_id[sid].get("status") == "verified"]
            if not strong:
                problems.append(f"rule {rid}: 'default' needs a verified grade A or B source (use 'test' instead)")

    mentioned = set()
    for path in list((root / "skills").rglob("*.md")) + [root / "README.md"]:
        if path.exists():
            mentioned |= set(re.findall(r"R-[A-Z]+-\d{2}", path.read_text(encoding="utf-8")))
    for rid in sorted(mentioned - seen):
        problems.append(f"docs mention {rid}, which is not defined in rules.yaml")
    return problems


def main() -> int:
    problems = lint()
    for p in problems:
        print(f"ERROR  {p}")
    if not problems:
        print("OK     rules and sources pass the evidence gate.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
