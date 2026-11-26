"""Tracker statuses: drafts are not applications until the candidate confirms submission."""
import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "scripts" / "tracker.py"

LEGACY = (
    "id,date_applied,company,role,role_family,cv_version,source,posting_date,status,status_date,next_followup,folder,my_notes\r\n"
    "A0001,2026-10-01,Acme,Data Analyst,data-analyst,data-analyst-v1,,,applied,2026-10-01,2026-10-08,,referral from Sam\r\n"
    "A0002,2026-10-03,Globex,BI Analyst,data-analyst,data-analyst-v1,,,callback,2026-10-10,,,\r\n"
)


@pytest.fixture
def tr(tmp_path, monkeypatch):
    path = tmp_path / "tracker.csv"

    def run(*args):
        # Inherit the parent environment: Windows Python 3.10 cannot start without SYSTEMROOT
        # ("_Py_HashRandomization_Init: failed to get random numbers"). Drop only our own settings.
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CV_", "NOMAGIC_"))}
        env.update({"CV_TRACKER": str(path), "CV_TODAY": "2026-11-19", "PYTHONUTF8": "1",
                    "NOMAGIC_WORKSPACE": str(tmp_path / "ws")})
        return subprocess.run([sys.executable, str(TRACKER), *args], env=env, capture_output=True, text=True)
    run.path = path
    return run


def rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def add(tr, *extra):
    return tr("add", "--company", "Initech", "--role", "Data Analyst", "--family", "data-analyst",
              "--cv-version", "data-analyst-v2", *extra)


def test_add_logs_a_draft_with_no_followup(tr):
    res = add(tr)
    assert res.returncode == 0 and "draft" in res.stdout
    (r,) = rows(tr.path)
    assert r["status"] == "draft" and r["date_applied"] == "" and r["next_followup"] == ""
    assert r["status_date"] == "2026-11-19"


def test_applied_needs_explicit_confirmation(tr):
    add(tr)
    res = tr("status", "A0001", "applied")
    assert res.returncode == 2 and "confirmed-submitted" in res.stderr
    assert rows(tr.path)[0]["status"] == "draft"
    res = tr("status", "A0001", "applied", "--confirmed-submitted", "--date", "2026-11-20")
    assert res.returncode == 0
    r = rows(tr.path)[0]
    assert (r["status"], r["date_applied"], r["next_followup"]) == ("applied", "2026-11-20", "2026-11-27")


def test_outcomes_require_a_submitted_application(tr):
    add(tr)
    for status in ("callback", "rejected", "ghosted"):
        assert tr("status", "A0001", status).returncode == 2
    assert tr("status", "A0001", "withdrawn").returncode == 0      # an abandoned draft can be withdrawn


def test_add_can_record_an_already_submitted_application(tr):
    add(tr, "--confirmed-submitted", "--date", "2026-11-18")
    r = rows(tr.path)[0]
    assert (r["status"], r["date_applied"], r["next_followup"]) == ("applied", "2026-11-18", "2026-11-25")


def test_drafts_are_excluded_from_stats_and_followups(tr):
    add(tr)
    add(tr, "--confirmed-submitted", "--date", "2026-11-01")
    stats = tr("stats").stdout
    assert "1 draft(s) not counted" in stats
    (row,) = [ln.split() for ln in stats.splitlines() if ln.startswith("data-analyst-v2")]
    assert row[1] == "1"                                                    # n counts only the submitted one
    due = tr("due").stdout
    assert "DRAFT      A0001" in due and "FOLLOW UP  A0002" in due and "FOLLOW UP  A0001" not in due


def test_legacy_csv_is_preserved(tr):
    tr.path.write_bytes(LEGACY.encode("utf-8"))
    assert tr("list").returncode == 0 and tr("due").returncode == 0 and tr("stats").returncode == 0
    assert tr.path.read_bytes() == LEGACY.encode("utf-8"), "read-only commands must not rewrite the file"
    add(tr)
    after = rows(tr.path)
    assert [r["id"] for r in after] == ["A0001", "A0002", "A0003"]
    assert after[0]["status"] == "applied" and after[0]["date_applied"] == "2026-10-01"   # old rows untouched
    assert after[0]["my_notes"] == "referral from Sam"                                    # extra column kept
    assert after[1]["status"] == "callback"
    assert after[2]["status"] == "draft"
    assert not tr.path.with_name("tracker.csv.tmp").exists()


HEADER = "id,date_applied,company,role,role_family,cv_version,source,posting_date,status,status_date,next_followup,folder\r\n"


def legacy_row(rid, company, status="applied", date="2026-10-01"):
    follow = "2026-10-08" if status == "applied" else ""
    return f"{rid},{date},{company},Data Analyst,data-analyst,data-analyst-v1,,,{status},{date},{follow},\r\n"


def test_ids_are_not_reused_after_a_middle_row_is_deleted(tr):
    # Legacy CSV (0.1.0 layout) where A0002 was deleted by hand: len(rows)+1 would give a second A0003.
    tr.path.write_text(HEADER + legacy_row("A0001", "Acme") + legacy_row("A0003", "Initech"), encoding="utf-8", newline="")
    add(tr)
    assert [r["id"] for r in rows(tr.path)] == ["A0001", "A0003", "A0004"]


def test_ids_ignore_hand_written_ids_and_grow_past_9999(tr):
    tr.path.write_text(HEADER + legacy_row("my-first-app", "Acme") + legacy_row("A9999", "Initech"),
                       encoding="utf-8", newline="")
    add(tr)
    assert rows(tr.path)[-1]["id"] == "A10000"


def test_existing_duplicate_ids_are_refused_not_guessed(tr):
    tr.path.write_text(HEADER + legacy_row("A0003", "Acme") + legacy_row("A0003", "Initech"), encoding="utf-8", newline="")
    before = tr.path.read_bytes()
    res = tr("status", "A0003", "callback")
    assert res.returncode == 2 and "appears 2 times" in res.stderr and "A0004" in res.stderr
    assert tr.path.read_bytes() == before
    res = add(tr)
    assert "appears more than once" in res.stderr and rows(tr.path)[-1]["id"] == "A0004"


def test_submitted_row_cannot_silently_return_to_draft(tr):
    tr.path.write_text(HEADER + legacy_row("A0001", "Acme"), encoding="utf-8", newline="")
    before = tr.path.read_bytes()
    res = tr("status", "A0001", "draft")
    assert res.returncode == 2 and "--not-submitted" in res.stderr
    assert tr.path.read_bytes() == before                     # date kept, still counted in stats
    assert "    1" in tr("stats").stdout.splitlines()[1]


def test_not_submitted_corrects_a_mistaken_applied(tr):
    add(tr)
    tr("status", "A0001", "applied", "--confirmed-submitted")
    res = tr("status", "A0001", "draft", "--not-submitted")
    assert res.returncode == 0
    r = rows(tr.path)[0]
    assert (r["status"], r["date_applied"], r["next_followup"]) == ("draft", "", "")
    assert "No submitted applications yet." in tr("stats").stdout


def test_outcomes_never_return_to_draft(tr):
    tr.path.write_text(HEADER + legacy_row("A0001", "Acme", status="callback"), encoding="utf-8", newline="")
    for extra in ((), ("--not-submitted",)):
        res = tr("status", "A0001", "draft", *extra)
        assert res.returncode == 2 and "cannot go back to draft" in res.stderr


def test_withdrawn_draft_can_be_reopened_but_withdrawn_submission_cannot(tr):
    add(tr)
    tr("status", "A0001", "withdrawn")
    assert tr("status", "A0001", "draft").returncode == 0       # never submitted: reopening is fine
    add(tr, "--confirmed-submitted")
    tr("status", "A0002", "withdrawn")
    assert tr("status", "A0002", "draft").returncode == 2       # was submitted: needs --not-submitted
