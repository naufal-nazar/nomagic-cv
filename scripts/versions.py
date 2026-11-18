#!/usr/bin/env python3
"""Versioned CV storage with one naming convention every agent can follow.

Layout (inside the workspace):
  sources/                                 originals you provided; never edited
    2026-11-19_current-cv.pdf
    index.yaml                             file, date added, sha256, note
  cvs/<family>/                            one folder per role family
    draft.md                               the only editable master
    <family>_v<N>_<YYYY-MM-DD>.md          frozen, read-only versions
    CURRENT                                name of the latest frozen version
    CHANGES.md                             what changed in each version, and why
  applications/<YYYY-MM-DD>_<company>_<role>/
    meta.yaml                              base version, version id for the tracker
    cv.md                                  tailored copy of the base version
    <First>_<Last>_<Role>.pdf               recruiter-facing export name

Commands:
  ingest FILE [--note TEXT]                copy an original into sources/ (dated, hashed)
  init FAMILY                              create cvs/FAMILY/ with an empty draft
  freeze FAMILY --note TEXT                draft -> next frozen version (fact check must pass)
  list [FAMILY]                            versions and the current one
  current FAMILY                           path of the current frozen version
  diff FAMILY vA vB                        unified diff between two versions
  apply FAMILY --company C --role R        new application folder from the current version
  export-name --role R                     recruiter-facing file name, e.g. Jordan_Lee_Data_Analyst.pdf
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cvlib  # noqa: E402

VERSION_RE = re.compile(r"^(?P<family>[a-z0-9-]+)_v(?P<n>\d+)_(?P<date>\d{4}-\d{2}-\d{2})\.md$")


def today() -> str:
    return os.environ.get("CV_TODAY") or dt.date.today().isoformat()


def slug(text: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-") or "x"


def ws() -> Path:
    return cvlib.WORKSPACE


def family_dir(family: str) -> Path:
    return ws() / "cvs" / slug(family)


def versions(family: str) -> list[tuple[int, Path]]:
    d = family_dir(family)
    out = []
    for p in d.glob("*.md") if d.exists() else []:
        m = VERSION_RE.match(p.name)
        if m and m.group("family") == slug(family):
            out.append((int(m.group("n")), p))
    return sorted(out)


def current(family: str) -> Path | None:
    d = family_dir(family)
    pointer = d / "CURRENT"
    if pointer.exists():
        p = d / pointer.read_text(encoding="utf-8").strip()
        if p.exists():
            return p
    vs = versions(family)
    return vs[-1][1] if vs else None


def make_read_only(p: Path) -> None:
    p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def is_frozen(path: Path) -> bool:
    """True for files no agent may edit: frozen versions and originals in sources/."""
    path = Path(path)
    return bool(VERSION_RE.match(path.name)) or ("sources" in path.parts and path.name != "index.yaml")


# ---------------------------------------------------------------- commands
def cmd_ingest(a) -> int:
    src = Path(a.file)
    if not src.exists():
        print(f"No such file: {src}", file=sys.stderr)
        return 2
    dest_dir = ws() / "sources"
    dest_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    index_path = dest_dir / "index.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"sources": []}
    for item in index["sources"]:
        if item["sha256"] == digest:
            print(f"Already stored as sources/{item['file']}")
            return 0
    name = f"{today()}_{slug(src.stem)}{src.suffix.lower()}"
    dest = dest_dir / name
    n = 2
    while dest.exists():
        dest = dest_dir / f"{today()}_{slug(src.stem)}-{n}{src.suffix.lower()}"
        n += 1
    shutil.copy2(src, dest)
    make_read_only(dest)
    index["sources"].append({"file": dest.name, "added": today(), "sha256": digest, "note": a.note or ""})
    index_path.write_text(yaml.safe_dump(index, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Stored original as sources/{dest.name} (read-only)")
    return 0


def cmd_init(a) -> int:
    d = family_dir(a.family)
    d.mkdir(parents=True, exist_ok=True)
    draft = d / "draft.md"
    if not draft.exists():
        template = Path(__file__).resolve().parent.parent / "skills" / "nomagic-cv" / "templates" / "master-cv.md"
        if not template.exists():
            template = Path(__file__).resolve().parent.parent / "templates" / "master-cv.md"
        draft.write_text(template.read_text(encoding="utf-8") if template.exists() else "", encoding="utf-8")
    changes = d / "CHANGES.md"
    if not changes.exists():
        changes.write_text(f"# {slug(a.family)}: version history\n\nOne change per version makes callback rates comparable.\n",
                           encoding="utf-8")
    print(f"Ready: {draft.relative_to(ws())}")
    return 0


def cmd_freeze(a) -> int:
    d = family_dir(a.family)
    draft = d / "draft.md"
    if not draft.exists():
        print(f"No draft at {draft}. Run: versions.py init {a.family}", file=sys.stderr)
        return 2
    check = subprocess.run([sys.executable, str(Path(__file__).with_name("fact_check.py")), str(draft)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check.returncode != 0:
        print(check.stdout + check.stderr)
        print("Freeze refused: the draft must pass fact_check first.", file=sys.stderr)
        return 1
    cur = current(a.family)
    if cur and cur.read_text(encoding="utf-8") == draft.read_text(encoding="utf-8"):
        print(f"No changes since {cur.name}; nothing to freeze.")
        return 0
    n = (versions(a.family)[-1][0] + 1) if versions(a.family) else 1
    name = f"{slug(a.family)}_v{n}_{today()}.md"
    dest = d / name
    shutil.copy2(draft, dest)
    make_read_only(dest)
    (d / "CURRENT").write_text(name + "\n", encoding="utf-8")
    with open(d / "CHANGES.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n## {slug(a.family)}-v{n} ({today()})\n{a.note}\n")
    print(f"Frozen {name} (version id for the tracker: {slug(a.family)}-v{n})")
    return 0


def cmd_list(a) -> int:
    root = ws() / "cvs"
    fams = [a.family] if a.family else sorted(p.name for p in root.iterdir() if p.is_dir()) if root.exists() else []
    if not fams:
        print("No role families yet. Run: versions.py init <family>")
    for f in fams:
        cur = current(f)
        print(f"{slug(f)}/  (draft.md editable)")
        for n, p in versions(f):
            print(f"  {'*' if cur and p == cur else ' '} {p.name}   id: {slug(f)}-v{n}")
    return 0


def cmd_current(a) -> int:
    cur = current(a.family)
    if not cur:
        print(f"No frozen version for {a.family} yet.", file=sys.stderr)
        return 1
    print(cur)
    return 0


def resolve(family: str, ref: str) -> Path:
    n = int(ref.lstrip("v"))
    for num, p in versions(family):
        if num == n:
            return p
    raise SystemExit(f"No version {ref} for {family}")


def cmd_diff(a) -> int:
    pa, pb = resolve(a.family, a.a), resolve(a.family, a.b)
    sys.stdout.writelines(difflib.unified_diff(
        pa.read_text(encoding="utf-8").splitlines(True), pb.read_text(encoding="utf-8").splitlines(True),
        fromfile=pa.name, tofile=pb.name))
    return 0


def export_name(role: str) -> str:
    try:
        name = cvlib.load_facts().get("candidate", {}).get("name", "Candidate")
    except FileNotFoundError:
        name = "Candidate"
    parts = [re.sub(r"[^A-Za-z0-9]", "", w) for w in f"{name} {role}".split()]
    return "_".join(p for p in parts if p) + ".pdf"


def cmd_apply(a) -> int:
    cur = current(a.family)
    if not cur:
        print(f"No frozen version for {a.family}. Freeze the draft first.", file=sys.stderr)
        return 1
    m = VERSION_RE.match(cur.name)
    folder = ws() / "applications" / f"{today()}_{slug(a.company)}_{slug(a.role)}"
    if folder.exists():
        print(f"Exists: {folder.relative_to(ws())}")
        return 0
    folder.mkdir(parents=True)
    shutil.copy2(cur, folder / "cv.md")
    (folder / "cv.md").chmod(0o644)
    meta = {"company": a.company, "role": a.role, "family": slug(a.family), "base_version": cur.name,
            "cv_version": f"{slug(a.family)}-v{m.group('n')}", "created": today(),
            "export_name": export_name(a.role)}
    (folder / "meta.yaml").write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Created {folder.relative_to(ws())}/ from {cur.name}")
    print(f"Save the posting as posting.md there. Export the final CV as {meta['export_name']}.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ingest"); s.add_argument("file"); s.add_argument("--note"); s.set_defaults(fn=cmd_ingest)
    s = sub.add_parser("init"); s.add_argument("family"); s.set_defaults(fn=cmd_init)
    s = sub.add_parser("freeze"); s.add_argument("family"); s.add_argument("--note", required=True)
    s.set_defaults(fn=cmd_freeze)
    s = sub.add_parser("list"); s.add_argument("family", nargs="?"); s.set_defaults(fn=cmd_list)
    s = sub.add_parser("current"); s.add_argument("family"); s.set_defaults(fn=cmd_current)
    s = sub.add_parser("diff"); s.add_argument("family"); s.add_argument("a"); s.add_argument("b"); s.set_defaults(fn=cmd_diff)
    s = sub.add_parser("apply"); s.add_argument("family"); s.add_argument("--company", required=True)
    s.add_argument("--role", required=True); s.set_defaults(fn=cmd_apply)
    s = sub.add_parser("export-name"); s.add_argument("--role", required=True)
    s.set_defaults(fn=lambda a: print(export_name(a.role)) or 0)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
