#!/usr/bin/env python3
"""Deterministic evals: the checkers must pass honest CVs and catch fabricated ones.

For each case in evals/cases/*, reads expected.yaml and runs fact_check (CVs)
and consistency_check (application folders). Fails if an honest file is flagged
or a fabricated one slips through or misses an expected rule.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import consistency_check  # noqa: E402
import fact_check  # noqa: E402


def main() -> int:
    failures = 0
    for case in sorted((ROOT / "evals" / "cases").iterdir()):
        exp_path = case / "expected.yaml"
        if not exp_path.exists():
            continue
        exp = yaml.safe_load(exp_path.read_text(encoding="utf-8"))
        os.environ["CV_TODAY"] = str(exp.get("today", ""))
        facts = str(case / "facts.yaml")
        for name, want in (exp.get("cvs") or {}).items():
            rep = fact_check.check(str(case / name), facts)
            rules = {e["rule"] for e in rep.errors}
            ok = (not rep.errors) == want["pass"]
            missing = set(want.get("must_flag", [])) - rules
            ok = ok and not missing and len(rep.errors) >= want.get("min_errors", 0)
            failures += not ok
            print(f"{'PASS' if ok else 'FAIL'}  {case.name}/{name}: {len(rep.errors)} errors {sorted(rules)}"
                  + (f" missing {sorted(missing)}" if missing else ""))
            if not ok:
                for e in rep.errors:
                    print(f"        line {e['line']} [{e['rule']}] {e['message']}")
        for name, want in (exp.get("applications") or {}).items():
            res = consistency_check.check(str(case / "applications" / name), facts)
            rules = {r for _w, r, _m in res["errors"]}
            ok = (not res["errors"]) == want["pass"]
            missing = set(want.get("must_flag", [])) - rules
            ok = ok and not missing
            failures += not ok
            print(f"{'PASS' if ok else 'FAIL'}  {case.name}/applications/{name}: {len(res['errors'])} errors {sorted(rules)}"
                  + (f" missing {sorted(missing)}" if missing else ""))
            if not ok:
                for w, r, m in res["errors"]:
                    print(f"        {w} [{r}] {m}")
    print("\nAll evals passed." if not failures else f"\n{failures} eval(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
