"""Shared helpers: load the fact sheet, parse CV Markdown, extract numbers and dates."""
from __future__ import annotations

import datetime as dt
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspace"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

TAG_RE = re.compile(r"<!--(.*?)-->", re.S)
NUM_RE = re.compile(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])\d+(?:\.\d+)?")
APPROX_MARKERS = ("~", "about", "around", "approximately", "roughly", "nearly", "some", "≈")


# ---------------------------------------------------------------- facts
def load_facts(path: str | Path | None = None) -> dict:
    p = Path(path) if path else WORKSPACE / "facts.yaml"
    with open(p, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    for key in ("roles", "education", "certifications", "skills", "languages", "role_families"):
        data.setdefault(key, [])
    data.setdefault("candidate", {})
    return data


def fact_index(facts: dict) -> dict[str, dict]:
    """Map every citable id to {'kind', 'text', 'approximate', 'role', 'obj'}."""
    idx: dict[str, dict] = {}
    for role in facts["roles"]:
        idx[role["id"]] = {"kind": "role", "text": "", "obj": role, "role": role["id"]}
        for res in role.get("results", []):
            idx[res["id"]] = {
                "kind": "result",
                "text": str(res.get("text", "")),
                "approximate": bool(res.get("approximate", False)),
                "role": role["id"],
                "obj": res,
            }
    for e in facts["education"]:
        idx[e["id"]] = {"kind": "edu", "text": f"{e.get('degree','')} {e.get('institution','')} {e.get('year','')}", "obj": e}
    for c in facts["certifications"]:
        idx[c["id"]] = {"kind": "cert", "text": f"{c.get('name','')} {c.get('acronym','')} {c.get('year','')}", "obj": c}
    return idx


def parse_ym(value) -> dt.date | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("present", "current", "now"):
        override = os.environ.get("CV_TODAY")
        return dt.date.fromisoformat(override) if override else dt.date.today()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})(?:-\d{1,2})?", s)
    if not m:
        raise ValueError(f"Date must be YYYY-MM or 'present', got {value!r}")
    return dt.date(int(m.group(1)), int(m.group(2)), 1)


def fmt_month(value) -> str:
    if str(value).strip().lower() in ("present", "current", "now"):
        return "Present"
    d = parse_ym(value)
    return f"{MONTHS[d.month - 1]} {d.year}"


def total_years(facts: dict) -> float:
    """Total years of experience across roles, merging overlaps."""
    spans = []
    for r in facts["roles"]:
        try:
            start, end = parse_ym(r.get("start")), parse_ym(r.get("end", "present"))
        except ValueError:
            continue
        if start and end and end >= start:
            spans.append((start, end))
    spans.sort()
    merged: list[list[dt.date]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    days = sum((e - s).days for s, e in merged)
    return days / 365.25


def known_terms(facts: dict) -> set[str]:
    terms = {str(s).strip().lower() for s in facts["skills"]}
    for r in facts["roles"]:
        terms |= {str(t).strip().lower() for t in r.get("tools", [])}
    for c in facts["certifications"]:
        if c.get("acronym"):
            terms.add(str(c["acronym"]).lower())
        terms.add(str(c.get("name", "")).lower())
    return terms


# ---------------------------------------------------------------- numbers
def numbers_in(text: str) -> list[float]:
    out = []
    for tok in NUM_RE.findall(text):
        try:
            out.append(float(tok.replace(",", "")))
        except ValueError:
            pass
    return out


def number_spans(text: str):
    for m in NUM_RE.finditer(text):
        try:
            yield float(m.group().replace(",", "")), m.start(), m.end()
        except ValueError:
            continue


def has_approx_marker(text: str, start: int) -> bool:
    window = text[max(0, start - 14):start].lower()
    return any(mk in window for mk in APPROX_MARKERS)


# ---------------------------------------------------------------- CV parsing
@dataclass
class CVLine:
    no: int
    raw: str
    text: str            # without tags, stripped
    section: str         # lower-case section name, "" for header block
    kind: str            # h1 | h2 | role | bullet | text | blank
    tags: dict = field(default_factory=dict)


def parse_tags(raw: str) -> dict:
    tags: dict[str, list[str]] = {}
    for body in TAG_RE.findall(raw):
        for part in body.split():
            if ":" in part:
                k, v = part.split(":", 1)
                tags.setdefault(k.strip().lower(), []).extend(x for x in v.split(",") if x)
            else:
                tags.setdefault(part.strip().lower(), [])
    return tags


def parse_cv(path: str | Path) -> list[CVLine]:
    content = Path(path).read_text(encoding="utf-8")
    # drop multi-line comments that are not tags (template notes)
    lines_out: list[CVLine] = []
    section = ""
    in_block_comment = False
    for no, raw in enumerate(content.splitlines(), start=1):
        stripped = raw.strip()
        if in_block_comment:
            if "-->" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("<!--") and "-->" not in stripped:
            in_block_comment = True
            continue
        tags = parse_tags(raw)
        text = TAG_RE.sub("", raw).strip()
        if not text:
            kind = "blank"
        elif text.startswith("# "):
            kind = "h1"
        elif text.startswith("## "):
            kind = "h2"
            section = text[3:].strip().lower()
        elif text.startswith("### "):
            kind = "role"
        elif re.match(r"^[-*] ", text):
            kind = "bullet"
        else:
            kind = "text"
        lines_out.append(CVLine(no, raw, text, section, kind, tags))
    return lines_out


ROLE_LINE_RE = re.compile(
    r"^###\s+(?P<title>.+?),\s+(?P<employer>.+?)(?:,\s+(?P<location>[^|]+?))?\s*\|\s*"
    r"(?P<start>[A-Z][a-z]{2} \d{4})\s*[-–—]\s*(?P<end>Present|[A-Z][a-z]{2} \d{4})\s*$"
)


def strip_markdown(text: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"^[-*]\s+", "", text)
    text = text.replace("**", "").replace("__", "")
    return text.strip()


def clean_cv_text(path: str | Path) -> str:
    """CV Markdown with provenance tags and template comments removed."""
    out = []
    for ln in parse_cv(path):
        out.append(ln.text)
    return "\n".join(out).strip() + "\n"
