#!/usr/bin/env python3
"""Outreach to employers, with two modes and guardrails (R-OUT-01..05).

Modes (set in facts.yaml under preferences.outreach.mode):
  semi  (default)  messages become drafts in your mailbox; you review and send
  auto             messages that pass every check are sent by SMTP from your own account,
                   within a daily cap; everything else stays a draft

Workspace layout:
  outreach/contacts.csv          who, where the address came from, consent basis, status
  outreach/messages/<date>_<org>_<type>.md   one message per file (YAML header + body)
  outreach/log.csv               every draft, send and reply

Commands:
  import FILE --source gosom|kit|manual [--basis B]  add leads (CSV or JSON) from a Google Maps
                                                     scraper export or your own list
  add --org O --email E --basis B [--name N --role R] add one contact
  verify                                           check each address's domain can receive mail (MX)
  list [--status S]
  new CONTACT_ID --type intro|referral|followup [--application DIR]   create a message file
  lint MESSAGE.md                                  run every outreach rule
  send MESSAGE.md                                  auto mode: send by SMTP if lint passes;
                                                   semi mode: mark as ready for drafting
  mark MESSAGE.md --drafted|--sent                 record what you did in your mail app
  reply CONTACT_ID --kind K [--note TEXT]          record a reply (no-openings, apply-online,
                                                   cv-on-file, interview, positive, unsubscribe, bounce)
  due                                              follow-ups due today

Consent bases (CASL-style; not legal advice):
  existing-relationship | referral | posting-contact | published-business-address
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cvlib  # noqa: E402

FIELDS = ["id", "org", "name", "role", "email", "website", "phone", "city", "category",
          "source", "consent_basis", "mx_ok", "status", "added", "notes"]
LOG_FIELDS = ["date", "contact_id", "email", "event", "message", "detail"]
BASES = ["existing-relationship", "referral", "posting-contact", "published-business-address"]
REPLY_KINDS = {
    "no-openings": ("closed", "rejected"), "apply-online": ("replied", None), "cv-on-file": ("replied", None),
    "interview": ("replied", "interview"), "positive": ("replied", "callback"),
    "unsubscribe": ("do-not-contact", None), "bounce": ("bounced", None),
}
LIMITS = {"intro": (80, 200), "referral": (60, 160), "followup": (60, 120)}
DEFAULTS = {"mode": "semi", "daily_cap": 10, "followup_days": 10, "max_followups": 2,
            "avoid": [], "signature": None}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "live.com"}


def today() -> str:
    return os.environ.get("CV_TODAY") or dt.date.today().isoformat()


def slug(text: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", str(text).lower())).strip("-") or "x"


def root() -> Path:
    p = cvlib.WORKSPACE / "outreach"
    (p / "messages").mkdir(parents=True, exist_ok=True)
    return p


def settings() -> dict:
    try:
        facts = cvlib.load_facts()
    except FileNotFoundError:
        facts = {}
    cfg = {**DEFAULTS, **((facts.get("preferences") or {}).get("outreach") or {})}
    cfg["candidate"] = facts.get("candidate", {})
    return cfg


def read_csv(path: Path, fields: list[str]) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def contacts() -> list[dict]:
    return read_csv(root() / "contacts.csv", FIELDS)


def save_contacts(rows: list[dict]) -> None:
    write_csv(root() / "contacts.csv", FIELDS, rows)


def log(contact: dict, event: str, message: str = "", detail: str = "") -> None:
    path = root() / "log.csv"
    rows = read_csv(path, LOG_FIELDS)
    rows.append({"date": today(), "contact_id": contact.get("id", ""), "email": contact.get("email", ""),
                 "event": event, "message": message, "detail": detail})
    write_csv(path, LOG_FIELDS, rows)


def events() -> list[dict]:
    return read_csv(root() / "log.csv", LOG_FIELDS)


# ---------------------------------------------------------------- import
def normalise(rec: dict, source: str) -> list[dict]:
    """Map a gosom/google-maps-scraper or google-maps-scraper-kit row to contacts (one per email)."""
    g = {k.lower().strip(): (v if v is not None else "") for k, v in rec.items()}
    org = g.get("title") or g.get("name") or g.get("org") or g.get("company") or ""
    raw = g.get("emails") or g.get("email") or ""
    if isinstance(raw, list):
        raw = ",".join(raw)
    emails = sorted(set(EMAIL_RE.findall(str(raw))))
    addr = g.get("address") or g.get("complete_address") or ""
    if isinstance(addr, dict):
        addr = ", ".join(str(v) for v in addr.values() if v)
    city = g.get("city") or ""
    return [{"org": str(org).strip(), "name": g.get("contact_name", ""), "role": g.get("role", ""),
             "email": e.lower(), "website": g.get("website") or g.get("web_site") or "",
             "phone": g.get("phone") or "", "city": city or str(addr)[:80], "category": g.get("category") or "",
             "source": source} for e in emails]


def load_records(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("results", [])
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def upsert(new: list[dict], basis: str) -> tuple[int, int]:
    rows = contacts()
    known = {r["email"].lower() for r in rows}
    added = skipped = 0
    n = len(rows)
    for c in new:
        if not c["email"] or c["email"] in known:
            skipped += 1
            continue
        n += 1
        rows.append({**c, "id": f"C{n:04d}", "consent_basis": basis, "mx_ok": "", "status": "new",
                     "added": today(), "notes": ""})
        known.add(c["email"])
        added += 1
    save_contacts(rows)
    return added, skipped


def cmd_import(a) -> int:
    recs = load_records(Path(a.file))
    found = [c for r in recs for c in normalise(r, a.source)]
    added, skipped = upsert(found, a.basis)
    print(f"Imported {added} contacts from {len(recs)} records ({skipped} duplicates or without email).")
    print(f"Consent basis recorded: {a.basis}. Run `outreach.py verify` next.")
    return 0


def cmd_add(a) -> int:
    added, _ = upsert([{"org": a.org, "name": a.name or "", "role": a.role or "", "email": a.email.lower(),
                        "website": "", "phone": "", "city": "", "category": "", "source": "manual"}], a.basis)
    print("Added." if added else "Already in contacts.")
    return 0


def mx_ok(domain: str) -> bool | None:
    try:
        import dns.resolver
    except ImportError:
        return None
    try:
        return bool(list(dns.resolver.resolve(domain, "MX", lifetime=5)))
    except Exception:
        return False


def cmd_verify(_a) -> int:
    rows = contacts()
    unknown = 0
    for r in rows:
        if r.get("mx_ok"):
            continue
        res = mx_ok(r["email"].split("@")[-1])
        if res is None:
            unknown += 1
            continue
        r["mx_ok"] = "yes" if res else "no"
        if not res:
            r["status"] = "bounced"
    save_contacts(rows)
    if unknown:
        print("Install dnspython for MX checks: pip install dnspython")
    print(f"Checked {len(rows) - unknown} domains. No SMTP probing is done: it can harm your sender reputation.")
    return 0


def cmd_list(a) -> int:
    for r in contacts():
        if a.status and r["status"] != a.status:
            continue
        print(f"{r['id']}  {r['status']:<15} {r['consent_basis']:<27} {r['org'][:30]:<30} {r['email']}")
    return 0


# ---------------------------------------------------------------- messages
def parse_message(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit(f"{path} needs a YAML header between --- lines.")
    return yaml.safe_load(m.group(1)) or {}, m.group(2).strip()


def write_message(path: Path, meta: dict, body: str) -> None:
    path.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n" + body.strip() + "\n",
                    encoding="utf-8")


def find_contact(cid: str) -> dict:
    for r in contacts():
        if r["id"] == cid or r["email"] == cid.lower():
            return r
    raise SystemExit(f"No contact {cid}")


def cmd_new(a) -> int:
    c = find_contact(a.contact)
    cfg = settings()
    name = cfg["candidate"].get("name", "")
    sig = cfg.get("signature") or "\n".join(x for x in (name, cfg["candidate"].get("phone", ""),
                                                        cfg["candidate"].get("email", ""),
                                                        cfg["candidate"].get("linkedin", "")) if x)
    greeting = f"Dear {c['name']}," if c.get("name") else f"Dear {c['org']} hiring team,"
    optout = "If you'd rather I didn't follow up, just let me know and I won't contact you again."
    body = f"{greeting}\n\n[Write the message here: who you are, why this organisation, one fact-backed result, a clear ask.]\n\n{optout}\n\nBest regards,\n{sig}"
    meta = {"to": c["email"], "contact_id": c["id"], "org": c["org"], "type": a.type, "subject": "",
            "application": a.application or "", "status": "draft", "created": today()}
    path = root() / "messages" / f"{today()}_{slug(c['org'])}_{a.type}.md"
    n = 2
    while path.exists():
        path = root() / "messages" / f"{today()}_{slug(c['org'])}_{a.type}-{n}.md"
        n += 1
    write_message(path, meta, body)
    print(f"Created {path.relative_to(cvlib.WORKSPACE)}")
    return 0


def lint(path: Path) -> tuple[list[str], list[str]]:
    meta, body = parse_message(path)
    cfg = settings()
    errs, warns = [], []
    c = next((r for r in contacts() if r["id"] == meta.get("contact_id")), None)
    if not c:
        return [f"[R-OUT-01] Recipient is not in contacts.csv; add them with a consent basis first."], []
    if c["consent_basis"] not in BASES:
        errs.append(f"[R-OUT-01] No valid consent basis for {c['email']} (one of: {', '.join(BASES)}).")
    if c["status"] in ("do-not-contact", "bounced", "closed"):
        errs.append(f"[R-OUT-04] {c['email']} is marked '{c['status']}'. Don't contact them again.")
    if c.get("mx_ok") == "no":
        errs.append(f"[R-OUT-01] {c['email']}'s domain cannot receive mail.")
    if meta.get("to", "").lower() != c["email"].lower():
        errs.append("[R-OUT-01] 'to' does not match the contact's email.")
    if not str(meta.get("subject", "")).strip():
        errs.append("Subject is empty.")
    if "[" in body and "]" in body and re.search(r"\[[^\]]*(write|placeholder|here)[^\]]*\]", body, re.I):
        errs.append("Body still contains a template placeholder.")
    words = len(re.findall(r"\b\w[\w'-]*\b", body.split("Best regards")[0]))
    lo, hi = LIMITS.get(meta.get("type", "intro"), (60, 200))
    if not lo <= words <= hi:
        errs.append(f"[R-OUT-03] {meta.get('type')} body has {words} words; keep it between {lo} and {hi}.")
    for phrase in cfg.get("avoid") or []:
        if phrase and phrase.lower() in body.lower():
            errs.append(f"[R-OUT-05] Contains '{phrase}', which the candidate asked to avoid.")
    if c["consent_basis"] == "published-business-address" and c["email"].split("@")[-1] in FREE_MAIL:
        warns.append("[R-OUT-01] Free-mail address: confirm it is the organisation's own published contact.")
    if c["consent_basis"] == "published-business-address" and "let me know" not in body.lower():
        warns.append("[R-OUT-01] Cold message: include a one-line way to opt out.")
    # facts: numbers must exist in the fact sheet
    try:
        facts = cvlib.load_facts()
        known = set()
        for r in facts["roles"]:
            for res in r.get("results", []):
                known |= set(cvlib.numbers_in(str(res.get("text", ""))))
        known.add(float(int(cvlib.total_years(facts))))
        sig_start = body.find("Best regards")
        for value, s, _e in cvlib.number_spans(body[:sig_start if sig_start > 0 else None]):
            if value not in known and not 1950 <= value <= 2100:
                errs.append(f"[R-HONEST-01] Number '{value:g}' is not in the fact sheet.")
    except FileNotFoundError:
        warns.append("No facts.yaml found; numbers not checked.")
    # follow-up spacing and count
    same_org = [r for r in contacts() if r["org"] == c["org"] and r["id"] != c["id"] and r["status"] == "contacted"]
    if same_org and meta.get("type") != "followup":
        warns.append(f"Already contacting {same_org[0]['email']} at {c['org']}; one thread per organisation is kinder.")
    sent = [e for e in events() if e["contact_id"] == c["id"] and e["event"] == "sent"]
    if meta.get("type") == "followup":
        prior_followups = [e for e in sent if "followup" in e["message"]]
        if not sent:
            errs.append("[R-OUT-03] Follow-up with no earlier message sent to this contact.")
        if len(prior_followups) >= int(cfg["max_followups"]):
            errs.append(f"[R-OUT-03] Already sent {len(prior_followups)} follow-ups (max {cfg['max_followups']}).")
        if sent:
            last = max(dt.date.fromisoformat(e["date"]) for e in sent)
            gap = (dt.date.fromisoformat(today()) - last).days
            if gap < int(cfg["followup_days"]):
                errs.append(f"[R-OUT-03] Last message was {gap} days ago; wait {cfg['followup_days']} days.")
    elif sent:
        warns.append("This contact already received a message; use --type followup.")
    return errs, warns


def cmd_lint(a) -> int:
    errs, warns = lint(Path(a.message))
    for e in errs:
        print(f"ERROR  {Path(a.message).name}  {e}")
    for w in warns:
        print(f"WARN   {Path(a.message).name}  {w}")
    if not errs:
        print(f"OK     {Path(a.message).name}: passes every outreach rule ({len(warns)} warnings).")
    return 1 if errs else 0


def sent_today() -> int:
    return sum(1 for e in events() if e["event"] == "sent" and e["date"] == today())


def load_smtp_env() -> None:
    """Read workspace/.smtp.env (KEY=value lines) without overriding real environment variables."""
    path = cvlib.WORKSPACE / ".smtp.env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def smtp_send(meta: dict, body: str, cfg: dict) -> None:
    load_smtp_env()
    host = os.environ.get("NOMAGIC_SMTP_HOST")
    user = os.environ.get("NOMAGIC_SMTP_USER")
    password = os.environ.get("NOMAGIC_SMTP_PASSWORD")
    if not (host and user and password):
        raise SystemExit("Auto mode needs NOMAGIC_SMTP_HOST, NOMAGIC_SMTP_USER and NOMAGIC_SMTP_PASSWORD "
                         "(an app password). See references/outreach.md.")
    msg = EmailMessage()
    msg["From"] = os.environ.get("NOMAGIC_SMTP_FROM") or user
    msg["To"] = meta["to"]
    msg["Subject"] = meta["subject"]
    msg["Message-ID"] = make_msgid()
    msg.set_content(body)
    attach = meta.get("attachment")
    if attach:
        p = Path(attach) if Path(attach).is_absolute() else cvlib.WORKSPACE / attach
        msg.add_attachment(p.read_bytes(), maintype="application", subtype="pdf", filename=p.name)
    port = int(os.environ.get("NOMAGIC_SMTP_PORT", "587"))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, password)
            s.send_message(msg)


def cmd_send(a) -> int:
    path = Path(a.message)
    errs, warns = lint(path)
    if errs:
        print("\n".join(f"ERROR  {e}" for e in errs))
        print("Not sent. Fix the errors (by asking the candidate, never by inventing).", file=sys.stderr)
        return 1
    meta, body = parse_message(path)
    cfg = settings()
    c = find_contact(meta["contact_id"])
    if cfg["mode"] != "auto":
        meta["status"] = "ready"
        write_message(path, meta, body)
        print("Semi-auto mode: create this as a DRAFT in the candidate's mailbox via the email connector, "
              f"then run: outreach.py mark {path.name} --drafted")
        return 0
    if sent_today() >= int(cfg["daily_cap"]):
        print(f"Daily cap of {cfg['daily_cap']} reached. Kept as draft for tomorrow. [R-OUT-02]", file=sys.stderr)
        return 1
    smtp_send(meta, body, cfg)
    meta["status"] = "sent"
    meta["sent"] = today()
    write_message(path, meta, body)
    rows = contacts()
    for r in rows:
        if r["id"] == c["id"]:
            r["status"] = "contacted"
    save_contacts(rows)
    log(c, "sent", path.name)
    print(f"Sent to {meta['to']} ({sent_today()}/{cfg['daily_cap']} today).")
    return 0


def cmd_mark(a) -> int:
    path = Path(a.message)
    meta, body = parse_message(path)
    c = find_contact(meta["contact_id"])
    event = "sent" if a.sent else "drafted"
    meta["status"] = event
    write_message(path, meta, body)
    if a.sent:
        rows = contacts()
        for r in rows:
            if r["id"] == c["id"]:
                r["status"] = "contacted"
        save_contacts(rows)
    log(c, event, path.name)
    print(f"Recorded: {path.name} {event}.")
    return 0


def cmd_reply(a) -> int:
    c = find_contact(a.contact)
    status, app_status = REPLY_KINDS[a.kind]
    rows = contacts()
    for r in rows:
        if r["id"] == c["id"]:
            r["status"] = status
            r["notes"] = (r.get("notes", "") + f" {today()}: {a.kind}" + (f" ({a.note})" if a.note else "")).strip()
    save_contacts(rows)
    log(c, "reply", "", a.kind + (f": {a.note}" if a.note else ""))
    print(f"{c['email']} -> {status}")
    if app_status:
        print(f"If this is about a tracked application, run: tracker.py status <id> {app_status}")
    return 0


def cmd_due(_a) -> int:
    cfg = settings()
    by_contact: dict[str, list[dict]] = {}
    for e in events():
        if e["event"] == "sent":
            by_contact.setdefault(e["contact_id"], []).append(e)
    status = {r["id"]: r["status"] for r in contacts()}
    shown = 0
    for cid, sent in by_contact.items():
        if status.get(cid) != "contacted":
            continue
        followups = sum(1 for e in sent if "followup" in e["message"])
        last = max(dt.date.fromisoformat(e["date"]) for e in sent)
        if followups < int(cfg["max_followups"]) and (dt.date.fromisoformat(today()) - last).days >= int(cfg["followup_days"]):
            print(f"FOLLOW UP  {cid}  last message {last}, follow-ups so far {followups}")
            shown += 1
    if not shown:
        print("No follow-ups due.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("import"); s.add_argument("file"); s.add_argument("--source", required=True, choices=["gosom", "kit", "manual"])
    s.add_argument("--basis", default="published-business-address", choices=BASES); s.set_defaults(fn=cmd_import)
    s = sub.add_parser("add"); s.add_argument("--org", required=True); s.add_argument("--email", required=True)
    s.add_argument("--basis", required=True, choices=BASES); s.add_argument("--name"); s.add_argument("--role"); s.set_defaults(fn=cmd_add)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    s = sub.add_parser("list"); s.add_argument("--status"); s.set_defaults(fn=cmd_list)
    s = sub.add_parser("new"); s.add_argument("contact"); s.add_argument("--type", required=True, choices=list(LIMITS))
    s.add_argument("--application"); s.set_defaults(fn=cmd_new)
    s = sub.add_parser("lint"); s.add_argument("message"); s.set_defaults(fn=cmd_lint)
    s = sub.add_parser("send"); s.add_argument("message"); s.set_defaults(fn=cmd_send)
    s = sub.add_parser("mark"); s.add_argument("message"); g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--drafted", action="store_true"); g.add_argument("--sent", action="store_true"); s.set_defaults(fn=cmd_mark)
    s = sub.add_parser("reply"); s.add_argument("contact"); s.add_argument("--kind", required=True, choices=list(REPLY_KINDS))
    s.add_argument("--note"); s.set_defaults(fn=cmd_reply)
    sub.add_parser("due").set_defaults(fn=cmd_due)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
