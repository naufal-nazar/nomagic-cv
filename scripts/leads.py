#!/usr/bin/env python3
"""Find organisations to contact, using open-source Google Maps scrapers, then import them.

NoMagicCV orchestrates two MIT-licensed projects; it does not copy their code.
They are installed outside this repo (default ~/.nomagic/tools) and keep their own licences.
  kit    Mahanaicoach/google-maps-scraper-kit   Python + Chrome; grid search, email crawl, MX checks
  gosom  gosom/google-maps-scraper              Docker image or Go binary; fast, CSV/JSON

Commands:
  status                                   which engines are installed
  install --engine kit|gosom               install an engine (git clone, or docker pull)
  find "QUERY" [--city "City, ST"] [--engine auto|kit|gosom] [--depth 1] [--limit 50]
               [--no-email] [--accept-terms]
                                           run a search, save the export under
                                           outreach/leads/, import it into contacts.csv with
                                           basis published-business-address, and check MX

Before the first search you must pass --accept-terms once: both projects state that
scraping may break Google's Terms of Service and that phones and emails are personal data.
Keep searches small and relevant to the candidate's field, and follow local law.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cvlib  # noqa: E402
import outreach  # noqa: E402

KIT_REPO = "https://github.com/Mahanaicoach/google-maps-scraper-kit"
GOSOM_IMAGE = "gosom/google-maps-scraper"
TERMS = """Before searching, please confirm:
  - Scraping Google Maps may break Google's Terms of Service (both projects say so in their READMEs).
  - Phone numbers and emails are personal data. Use them only for relevant, low-volume job outreach,
    and follow local law (for example CASL in Canada, GDPR in the EU, CAN-SPAM in the US).
  - Imported addresses are recorded with the consent basis "published-business-address".
This is not legal advice. Re-run with --accept-terms to confirm (asked once per workspace)."""


def tools_dir() -> Path:
    return Path(os.environ.get("NOMAGIC_TOOLS") or Path.home() / ".nomagic" / "tools")


def kit_dir() -> Path:
    return tools_dir() / "google-maps-scraper-kit"


def has_docker() -> bool:
    return bool(shutil.which("docker")) and subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def gosom_binary() -> str | None:
    return shutil.which("google-maps-scraper")


def engines() -> dict[str, bool]:
    return {"kit": (kit_dir() / "scripts" / "scrape.py").exists(),
            "gosom": bool(gosom_binary()) or (has_docker() and subprocess.run(
                ["docker", "image", "inspect", GOSOM_IMAGE], capture_output=True).returncode == 0)}


def cmd_status(_a) -> int:
    for name, ok in engines().items():
        print(f"{name:<6} {'installed' if ok else 'not installed'}")
    if not any(engines().values()):
        print("Install one: python scripts/leads.py install --engine kit   (or --engine gosom with Docker)")
    return 0


def cmd_install(a) -> int:
    if a.engine == "kit":
        if (kit_dir() / ".git").exists():
            subprocess.run(["git", "-C", str(kit_dir()), "pull", "--ff-only"], check=False)
            print(f"Updated {kit_dir()}")
        else:
            kit_dir().parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--depth", "1", KIT_REPO, str(kit_dir())], check=True)
            print(f"Installed kit at {kit_dir()} (MIT; needs Python 3.9+ and Chrome)")
        return 0
    if gosom_binary():
        print("gosom binary already on PATH.")
        return 0
    if has_docker():
        subprocess.run(["docker", "pull", GOSOM_IMAGE], check=True)
        print(f"Pulled {GOSOM_IMAGE} (MIT)")
        return 0
    print("gosom needs Docker, or a binary from https://github.com/gosom/google-maps-scraper/releases on your PATH.",
          file=sys.stderr)
    return 1


def ack_path() -> Path:
    return outreach.root() / ".leads-terms-accepted"


def build_command(engine: str, query: str, city: str | None, depth: int, limit: int, email: bool,
                  out: Path, work: Path) -> list[str]:
    if engine == "kit":
        cmd = [sys.executable, str(kit_dir() / "scripts" / "scrape.py"), query, "--depth", str(depth),
               "--limit", str(limit), "--verify-emails", "--out", str(out)]
        if city:
            cmd += ["--city", city]
        cmd += ["--has-email"] if email else ["--no-email"]
        return cmd
    full_query = f"{query} {city}" if city and city.lower() not in query.lower() else query
    (work / "queries.txt").write_text(full_query + "\n", encoding="utf-8")
    flags = ["-depth", str(depth), "-exit-on-inactivity", "3m"] + (["-email"] if email else [])
    if gosom_binary():
        return [gosom_binary(), "-input", str(work / "queries.txt"), "-results", str(out), *flags]
    return ["docker", "run", "--rm", "-v", "gmaps-playwright-cache:/opt",
            "-v", f"{work / 'queries.txt'}:/queries.txt:ro", "-v", f"{out.parent}:/out",
            GOSOM_IMAGE, "-input", "/queries.txt", "-results", f"/out/{out.name}", *flags]


def cmd_find(a) -> int:
    if not ack_path().exists():
        if not a.accept_terms:
            print(TERMS)
            return 2
        ack_path().write_text(f"accepted {outreach.today()}\n", encoding="utf-8")
    available = engines()
    engine = a.engine
    if engine == "auto":
        engine = "kit" if available["kit"] else "gosom" if available["gosom"] else None
    if not engine or not available.get(engine):
        print("No scraper installed. Run: python scripts/leads.py install --engine kit", file=sys.stderr)
        return 1
    leads = outreach.root() / "leads"
    leads.mkdir(parents=True, exist_ok=True)
    out = leads / f"{outreach.today()}_{outreach.slug(a.query)}_{engine}.csv"
    started_engine = False
    with tempfile.TemporaryDirectory() as tmp:
        if engine == "kit":
            started_engine = subprocess.run([sys.executable, str(kit_dir() / "scripts" / "engine.py"), "start"],
                                            cwd=kit_dir(), capture_output=True, text=True).returncode == 0
        cmd = build_command(engine, a.query, a.city, a.depth, a.limit, not a.no_email, out, Path(tmp))
        print("Running:", " ".join(cmd))
        try:
            res = subprocess.run(cmd, cwd=kit_dir() if engine == "kit" else None)
        finally:
            if started_engine:
                subprocess.run([sys.executable, str(kit_dir() / "scripts" / "engine.py"), "stop"],
                               cwd=kit_dir(), capture_output=True)
    if res.returncode != 0 or not out.exists():
        print(f"The {engine} search did not produce {out.name}. See its output above.", file=sys.stderr)
        return 1
    records = outreach.load_records(out)
    found = [c for r in records for c in outreach.normalise(r, engine)]
    if a.limit:
        found = found[: a.limit]
    added, skipped = outreach.upsert(found, "published-business-address")
    print(f"Saved {out.relative_to(cvlib.WORKSPACE)}: {len(records)} places, {added} new contacts, "
          f"{skipped} duplicates or without email.")
    outreach.cmd_verify(argparse.Namespace())
    print("Next: review the list (outreach.py list --status new) with the candidate before drafting anything.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("install"); s.add_argument("--engine", required=True, choices=["kit", "gosom"]); s.set_defaults(fn=cmd_install)
    s = sub.add_parser("find"); s.add_argument("query"); s.add_argument("--city")
    s.add_argument("--engine", default="auto", choices=["auto", "kit", "gosom"])
    s.add_argument("--depth", type=int, default=1, help="each step loads about 20 places (default 1)")
    s.add_argument("--limit", type=int, default=50, help="maximum new contacts to import (default 50)")
    s.add_argument("--no-email", action="store_true", help="skip website crawl for emails")
    s.add_argument("--accept-terms", action="store_true")
    s.set_defaults(fn=cmd_find)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
