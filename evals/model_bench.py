#!/usr/bin/env python3
"""Model benchmark: how often does each AI model invent facts when writing a CV?

Protocol (agent-agnostic; this script only scores):
1. For each case in evals/cases/<case>/, give a model facts.yaml + posting.md and the
   nomagic-cv skill, and ask for a tailored, tagged CV.
2. Save the result as evals/out/<model>/<case>.md
3. Run: python evals/model_bench.py

Scores per model:
- fabrication errors: fact_check errors per CV (lower is better; the target is 0)
- clean rate: share of CVs with zero errors
- must-have coverage: share of the case's must-haves mentioned in the CV
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import cvlib  # noqa: E402
import fact_check  # noqa: E402


def main() -> int:
    out_dir = ROOT / "evals" / "out"
    if not out_dir.exists():
        print("No model outputs yet. Save them as evals/out/<model>/<case>.md (see docstring).")
        return 0
    print(f"{'model':<20}{'CVs':>5}{'errors/CV':>11}{'clean':>8}{'coverage':>10}")
    for model_dir in sorted(p for p in out_dir.iterdir() if p.is_dir()):
        n = errs = clean = 0
        cover = []
        for cv in sorted(model_dir.glob("*.md")):
            case = ROOT / "evals" / "cases" / cv.stem
            if not (case / "facts.yaml").exists():
                continue
            exp = yaml.safe_load((case / "expected.yaml").read_text(encoding="utf-8"))
            os.environ["CV_TODAY"] = str(exp.get("today", ""))
            rep = fact_check.check(str(cv), str(case / "facts.yaml"))
            n += 1
            errs += len(rep.errors)
            clean += not rep.errors
            text = cvlib.clean_cv_text(cv).lower()
            musts = exp.get("must_haves", [])
            if musts:
                cover.append(sum(m.lower() in text for m in musts) / len(musts))
        if n:
            cov = sum(cover) / len(cover) if cover else 0
            print(f"{model_dir.name:<20}{n:>5}{errs / n:>11.2f}{clean / n:>8.0%}{cov:>10.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
