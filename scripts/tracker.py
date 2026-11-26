#!/usr/bin/env python3
"""Application tracker with honest statistics (R-SIGNAL-01, R-MEASURE-01).

Commands:
  add     --company C --role R --family F [--cv-version V | --folder DIR with meta.yaml] [--source S] [--posting-date YYYY-MM-DD] [--folder DIR] [--date YYYY-MM-DD]
          [--confirmed-submitted]           logs a DRAFT by default; add the flag only if the candidate says they already submitted it
  status  ID STATUS [--date YYYY-MM-DD] [--confirmed-submitted]
                                            STATUS: draft applied callback interview offer rejected ghosted withdrawn
                                            'applied' needs --confirmed-submitted: the candidate told you they submitted it
  due                                       follow-ups due, applications with no reply after 21 days, drafts not yet submitted
  list
  stats   [--family F]                      callback rate per CV version with 95% Wilson intervals
  check-complete                            application folders with a cv.md but no tracker row (exit 1 if any)

Data: workspace/tracker.csv (override with CV_TRACKER=path).

A row starts as 'draft' when the application package is saved. It becomes 'applied' only when the candidate
confirms they submitted it; that date starts the follow-up clock and counts the row in stats. Rows written by
earlier versions (always 'applied') are read as they are; nothing is rewritten.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cvlib  # noqa: E402

FIELDS = ["id", "date_applied", "company", "role", "role_family", "cv_version", "source",
          "posting_date", "status", "status_date", "next_followup", "folder"]
STATUSES = ["draft", "applied", "callback", "interview", "offer", "rejected", "ghosted", "withdrawn"]
POSITIVE = {"callback", "interview", "offer"}
NEEDS_SUBMISSION = {"callback", "interview", "offer", "rejected", "ghosted"}   # outcomes only a submitted application can have
MIN_N = 30
FOLLOWUP_DAYS = 7
STALE_DAYS = 21


def tracker_path() -> Path:
    return Path(os.environ.get("CV_TRACKER", cvlib.WORKSPACE / "tracker.csv"))


def load() -> list[dict]:
    p = tracker_path()
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _existing_header() -> list[str]:
    p = tracker_path()
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return next(csv.reader(fh), [])


def save(rows: list[dict]) -> None:
    """Write atomically, keeping any extra columns the candidate added to the CSV."""
    p = tracker_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = FIELDS + [c for c in _existing_header() if c and c not in FIELDS]
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) or "" for k in fields})
    os.replace(tmp, p)


def today() -> dt.date:
    override = os.environ.get("CV_TODAY")
    return dt.date.fromisoformat(override) if override else dt.date.today()


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def cmd_add(a) -> int:
    if a.folder and not a.cv_version:
        meta = Path(a.folder) / "meta.yaml"
        if meta.exists():
            import yaml
            a.cv_version = (yaml.safe_load(meta.read_text(encoding="utf-8")) or {}).get("cv_version")
    if not a.cv_version:
        print("--cv-version is required unless --folder has a meta.yaml (made by versions.py apply)", file=sys.stderr)
        return 2
    rows = load()
    date = a.date or today().isoformat()
    rid = f"A{len(rows) + 1:04d}"
    row = {"id": rid, "date_applied": "", "company": a.company, "role": a.role, "role_family": a.family,
           "cv_version": a.cv_version, "source": a.source or "", "posting_date": a.posting_date or "",
           "status": "draft", "status_date": date, "next_followup": "", "folder": a.folder or ""}
    if a.confirmed_submitted:
        mark_applied(row, date)
    rows.append(row)
    save(rows)
    if row["status"] == "applied":
        print(f"Added {rid}: {a.company} / {a.role} (cv {a.cv_version}), submitted {date}. Follow up on {row['next_followup']}.")
    else:
        print(f"Added {rid} as a draft: {a.company} / {a.role} (cv {a.cv_version}). "
              f"When the candidate confirms they submitted it: tracker.py status {rid} applied --confirmed-submitted")
    if a.posting_date:
        age = (dt.date.fromisoformat(date) - dt.date.fromisoformat(a.posting_date)).days
        if age > 4:
            print(f"Note [R-SIGNAL-01, B]: posting was {age} days old; 56% of applications arrive in the first 96 hours.")
    return 0


def mark_applied(row: dict, date: str) -> None:
    row["status"] = "applied"
    row["status_date"] = date
    row["date_applied"] = date
    row["next_followup"] = (dt.date.fromisoformat(date) + dt.timedelta(days=FOLLOWUP_DAYS)).isoformat()


def cmd_status(a) -> int:
    if a.status not in STATUSES:
        print(f"Status must be one of {STATUSES}", file=sys.stderr)
        return 2
    rows = load()
    for r in rows:
        if r["id"] == a.id:
            date = a.date or today().isoformat()
            if a.status == "applied" and r["status"] != "applied":
                if not a.confirmed_submitted:
                    print("Mark an application 'applied' only after the candidate confirms they submitted it, then add "
                          "--confirmed-submitted (and --date if it was not today).", file=sys.stderr)
                    return 2
                mark_applied(r, date)
            elif a.status in NEEDS_SUBMISSION and not r.get("date_applied"):
                print(f"{a.id} is still a draft. Ask the candidate when they submitted it, record that first with "
                      f"tracker.py status {a.id} applied --confirmed-submitted --date YYYY-MM-DD, then set '{a.status}'.",
                      file=sys.stderr)
                return 2
            else:
                r["status"] = a.status
                r["status_date"] = date
                r["next_followup"] = r["next_followup"] if a.status == "applied" else ""
                if a.status == "draft":
                    r["date_applied"] = ""
            save(rows)
            print(f"{a.id} -> {r['status']}")
            return 0
    print(f"No application {a.id}", file=sys.stderr)
    return 1


def due_items(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    t = today()
    rows = [r for r in rows if r.get("date_applied")]
    follow = [r for r in rows if r["status"] == "applied" and r["next_followup"]
              and dt.date.fromisoformat(r["next_followup"]) <= t]
    stale = [r for r in rows if r["status"] == "applied"
             and (t - dt.date.fromisoformat(r["date_applied"])).days >= STALE_DAYS]
    return follow, stale


def cmd_due(_a) -> int:
    rows = load()
    follow, stale = due_items(rows)
    drafts = [r for r in rows if r["status"] == "draft"]
    if not follow and not stale and not drafts:
        print("Nothing due.")
    for r in drafts:
        print(f"DRAFT      {r['id']} {r['company']} / {r['role']} (saved {r['status_date']}): not marked submitted; "
              "ask the candidate whether they sent it.")
    for r in follow:
        print(f"FOLLOW UP  {r['id']} {r['company']} / {r['role']} (applied {r['date_applied']})")
    for r in stale:
        print(f"NO REPLY   {r['id']} {r['company']} / {r['role']}: 21+ days; consider marking 'ghosted'.")
    return 0


def cmd_list(_a) -> int:
    for r in load():
        print(f"{r['id']}  {r['date_applied'] or '(draft)':<10}  {r['status']:<10} {r['cv_version']:<8} {r['company']} / {r['role']}")
    return 0


def cmd_stats(a) -> int:
    rows = [r for r in load() if not a.family or r["role_family"] == a.family]
    drafts = sum(1 for r in rows if r["status"] == "draft")
    rows = [r for r in rows if r["status"] not in ("withdrawn", "draft")]
    if drafts:
        print(f"{drafts} draft(s) not counted: only applications the candidate confirmed as submitted are measured.")
    if not rows:
        print("No submitted applications yet.")
        return 0
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["cv_version"], []).append(r)
    results = []
    print(f"{'version':<10}{'n':>5}{'callbacks':>11}{'rate':>8}   95% interval")
    for v, rs in sorted(groups.items()):
        n = len(rs)
        k = sum(1 for r in rs if r["status"] in POSITIVE)
        lo, hi = wilson(k, n)
        results.append((v, n, k, lo, hi))
        print(f"{v:<10}{n:>5}{k:>11}{k / n:>8.1%}   {lo:.1%} - {hi:.1%}")
    print()
    small = [v for v, n, *_ in results if n < MIN_N]
    if small:
        print(f"Too few applications to judge {', '.join(small)} (fewer than {MIN_N} each). Treat differences as noise.")
    if len(results) >= 2:
        best = max(results, key=lambda x: x[2] / x[1])
        rivals = [x for x in results if x is not best]
        if all(best[3] > x[4] for x in rivals) and not small:
            print(f"Version {best[0]} is ahead and its interval does not overlap the others.")
        else:
            print("No winner yet: the intervals overlap. Keep both, change one element at a time [R-MEASURE-01].")
    return 0


def cmd_check_complete(_a) -> int:
    apps = cvlib.WORKSPACE / "applications"
    if not apps.exists():
        return 0
    tracked = {Path(r["folder"]).name for r in load() if r.get("folder")}
    missing = [d.name for d in sorted(apps.iterdir()) if d.is_dir() and (d / "cv.md").exists() and d.name not in tracked]
    for m in missing:
        print(f"Untracked application folder: {m}")
    return 1 if missing else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add")
    s.add_argument("--company", required=True)
    s.add_argument("--role", required=True)
    s.add_argument("--family", required=True)
    s.add_argument("--cv-version")
    s.add_argument("--source")
    s.add_argument("--posting-date")
    s.add_argument("--folder")
    s.add_argument("--date")
    s.add_argument("--confirmed-submitted", action="store_true",
                   help="the candidate confirmed this application was already submitted")
    s.set_defaults(fn=cmd_add)
    s = sub.add_parser("status")
    s.add_argument("id")
    s.add_argument("status")
    s.add_argument("--date")
    s.add_argument("--confirmed-submitted", action="store_true",
                   help="required with 'applied': the candidate confirmed they submitted it")
    s.set_defaults(fn=cmd_status)
    sub.add_parser("due").set_defaults(fn=cmd_due)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    s = sub.add_parser("stats")
    s.add_argument("--family")
    s.set_defaults(fn=cmd_stats)
    sub.add_parser("check-complete").set_defaults(fn=cmd_check_complete)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
