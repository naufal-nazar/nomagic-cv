#!/usr/bin/env python3
"""Export a tagged CV to other open-source tools. Tags are stripped; structured data comes from facts.yaml.

Usage:
  export.py clean     CV.md [-o out.md]                 plain Markdown without provenance tags
  export.py jsonresume CV.md [-o resume.json]           JSON Resume (jsonresume.org) for Reactive Resume and others
  export.py rendercv  CV.md [-o Name_CV.yaml]           RenderCV input; then: rendercv render Name_CV.yaml

Only lines that passed fact_check should be exported. Run fact_check.py first.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cvlib  # noqa: E402


def structure(cv_path: str, facts: dict) -> dict:
    """Read the CV's choices (what is included, in what order, wording) and join with facts."""
    idx = cvlib.fact_index(facts)
    lines = cvlib.parse_cv(cv_path)
    out = {"headline": "", "summary": [], "highlights": [], "roles": [], "education": [],
           "certifications": [], "skills": [], "languages": []}
    header = [ln for ln in lines if ln.section == "" and ln.kind == "text"]
    if header:
        out["headline"] = header[0].text
    current = None
    for ln in lines:
        sec, text = ln.section, cvlib.strip_markdown(ln.text)
        if ln.kind in ("blank", "h1", "h2") or sec == "":
            continue
        if sec == "summary":
            out["summary"].append(text)
        elif sec == "highlights" and ln.kind == "bullet":
            out["highlights"].append(text)
        elif "experience" in sec:
            if ln.kind == "role":
                rid = (ln.tags.get("role") or [None])[0]
                role = idx.get(rid, {}).get("obj") if rid else None
                if role:
                    current = {"role": role, "highlights": []}
                    out["roles"].append(current)
            elif ln.kind == "bullet" and current:
                current["highlights"].append(text)
        elif sec.startswith("education"):
            eid = (ln.tags.get("edu") or [None])[0]
            if eid in idx:
                out["education"].append(idx[eid]["obj"])
        elif sec.startswith("certification"):
            cid = (ln.tags.get("cert") or [None])[0]
            if cid in idx:
                out["certifications"].append(idx[cid]["obj"])
        elif sec.startswith("skill"):
            label, _, rest = text.partition(":")
            if rest:
                out["skills"].append({"label": label.strip(), "items": [x.strip() for x in rest.split(",") if x.strip()]})
            else:
                out["skills"].append({"label": "Skills", "items": [x.strip() for x in text.split(",") if x.strip()]})
        elif sec.startswith("language"):
            out["languages"] = facts["languages"]
    return out


def to_jsonresume(s: dict, facts: dict) -> dict:
    c = facts["candidate"]
    city, _, region = str(c.get("location", "")).partition(",")
    basics = {"name": c.get("name", ""), "label": s["headline"].split("|")[0].strip(), "email": c.get("email", ""),
              "phone": c.get("phone", ""), "summary": " ".join(s["summary"]),
              "location": {"city": city.strip(), "region": region.strip()}, "profiles": []}
    if c.get("linkedin"):
        url = c["linkedin"] if str(c["linkedin"]).startswith("http") else f"https://{c['linkedin']}"
        basics["profiles"].append({"network": "LinkedIn", "url": url})
    work = []
    for r in s["roles"]:
        role = r["role"]
        item = {"name": role["employer"], "position": role["title"], "location": role.get("location", ""),
                "startDate": str(role["start"]), "highlights": r["highlights"]}
        if str(role.get("end", "present")).lower() != "present":
            item["endDate"] = str(role["end"])
        work.append(item)
    return {
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
        "basics": basics,
        "work": work,
        "education": [{"institution": e.get("institution", ""), "studyType": e.get("degree", ""),
                       "endDate": str(e.get("year", ""))} for e in s["education"]],
        "certificates": [{"name": x.get("name", ""), "issuer": x.get("issuer", ""), "date": str(x.get("year", ""))}
                         for x in s["certifications"]],
        "skills": [{"name": g["label"], "keywords": g["items"]} for g in s["skills"]],
        "languages": [{"language": l["name"], "fluency": l.get("level", "")} for l in s["languages"]],
    }


def to_rendercv(s: dict, facts: dict) -> dict:
    c = facts["candidate"]
    cv: dict = {"name": c.get("name", ""), "location": c.get("location", ""), "email": c.get("email", "")}
    if c.get("phone"):
        cv["phone"] = re.sub(r"[^\d+]", "", str(c["phone"]))
    if c.get("linkedin"):
        cv["social_networks"] = [{"network": "LinkedIn", "username": str(c["linkedin"]).rstrip("/").split("/")[-1]}]
    sections: dict = {}
    if s["summary"]:
        sections["summary"] = [" ".join(s["summary"])]
    if s["highlights"]:
        sections["highlights"] = [{"bullet": h} for h in s["highlights"]]
    if s["roles"]:
        sections["experience"] = [{
            "company": r["role"]["employer"], "position": r["role"]["title"],
            "location": r["role"].get("location", ""), "start_date": str(r["role"]["start"]),
            "end_date": str(r["role"].get("end", "present")), "highlights": r["highlights"],
        } for r in s["roles"]]
    if s["education"]:
        sections["education"] = [{"institution": e.get("institution", ""), "area": e.get("degree", ""),
                                  "end_date": str(e.get("year", ""))} for e in s["education"]]
    if s["certifications"]:
        sections["certifications"] = [{"bullet": f"{x.get('name','')} ({x.get('acronym','')}), {x.get('issuer','')}, {x.get('year','')}"}
                                      for x in s["certifications"]]
    if s["skills"]:
        sections["skills"] = [{"label": g["label"], "details": ", ".join(g["items"])} for g in s["skills"]]
    if s["languages"]:
        sections["languages"] = [{"label": l["name"], "details": l.get("level", "")} for l in s["languages"]]
    cv["sections"] = sections
    return {"cv": cv}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("format", choices=["clean", "jsonresume", "rendercv"])
    ap.add_argument("cv")
    ap.add_argument("--facts")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()
    if a.format == "clean":
        data = cvlib.clean_cv_text(a.cv)
    else:
        facts = cvlib.load_facts(a.facts)
        s = structure(a.cv, facts)
        if a.format == "jsonresume":
            data = json.dumps(to_jsonresume(s, facts), indent=2, ensure_ascii=False) + "\n"
        else:
            data = yaml.safe_dump(to_rendercv(s, facts), sort_keys=False, allow_unicode=True)
    if a.output:
        Path(a.output).write_text(data, encoding="utf-8")
        print(f"Wrote {a.output}")
    else:
        sys.stdout.write(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
